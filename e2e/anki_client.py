"""Black-box E2E client for anki-connect-server.

Talks ONLY to the HTTP API (POST /api) — never imports the server library or
touches the collection DB directly. Uses the Python stdlib exclusively so it
can run on any host without installs.

Usage:
    from anki_client import Client, check, record, summary
    c = Client("http://localhost:18761")
    r = c.ok("version")                    # asserts error is None, returns result
    e = c.err("nope")                       # asserts error is a string, returns it
    obs = c.request("deckNames")           # raw envelope, no assertion
    check("SC-01", r == [True], f"got {r}")
    record("SC-03", f"ease=5 rejected with: {e}")
    exit(summary())
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

# ---------------------------------------------------------------- test ledger

_RESULTS: list[tuple[str, str, str]] = []  # (status, case_id, detail)


def check(case_id: str, cond: bool, detail: str = "") -> bool:
    status = "PASS" if cond else "FAIL"
    _RESULTS.append((status, case_id, detail))
    print(f"[{status}] {case_id} {detail}")
    return cond


def record(case_id: str, detail: str) -> None:
    """Record an exploratory observation (no pass/fail judgement)."""
    _RESULTS.append(("OBS", case_id, detail))
    print(f"[OBS ] {case_id} {detail}")


def summary() -> int:
    """Print totals; return process exit code (non-zero if any FAIL)."""
    n_pass = sum(1 for s, _, _ in _RESULTS if s == "PASS")
    n_fail = sum(1 for s, _, _ in _RESULTS if s == "FAIL")
    n_obs = sum(1 for s, _, _ in _RESULTS if s == "OBS")
    print(f"\nTOTAL: {n_pass} passed, {n_fail} failed, {n_obs} observations")
    return 1 if n_fail else 0


# ---------------------------------------------------------------- HTTP client


class Client:
    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -- low-level

    def request(
        self,
        action: str,
        params: dict[str, Any] | None = None,
        version: int = 6,
        path: str = "/api",
    ) -> tuple[int, Any]:
        """POST an AnkiConnect-style request; return (http_status, parsed_body)."""
        body = json.dumps({"action": action, "version": version, "params": params or {}}).encode()
        req = urllib.request.Request(
            self.base_url + path, data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            try:
                return e.code, json.loads(raw)
            except json.JSONDecodeError:
                return e.code, raw
        except urllib.error.URLError as e:
            return 0, f"connection error: {e}"

    def raw_post(self, payload: Any, path: str = "/api") -> tuple[int, Any]:
        """POST an arbitrary JSON payload (for malformed-request tests)."""
        req = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            try:
                return e.code, json.loads(raw)
            except json.JSONDecodeError:
                return e.code, raw
        except urllib.error.URLError as e:
            return 0, f"connection error: {e}"

    def get(self, path: str = "/health") -> tuple[int, str]:
        req = urllib.request.Request(self.base_url + path)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, resp.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(errors="replace")
        except urllib.error.URLError as e:
            return 0, f"connection error: {e}"

    # -- assertions

    def ok(self, action: str, params: dict[str, Any] | None = None, version: int = 6) -> Any:
        """Assert error is None; return the result."""
        _, body = self.request(action, params, version)
        if body.get("error") is not None:
            raise AssertionError(f"{action}: expected success, got error: {body.get('error')!r}")
        return body.get("result")

    def err(self, action: str, params: dict[str, Any] | None = None, version: int = 6) -> str:
        """Assert an error envelope (HTTP 200, error str, result null); return the error."""
        status, body = self.request(action, params, version)
        if status != 200:
            raise AssertionError(
                f"{action}: expected HTTP 200 error envelope, got {status}: {body}"
            )
        if not isinstance(body, dict) or not isinstance(body.get("error"), str):
            raise AssertionError(f"{action}: expected error string, got: {body}")
        if body.get("result") is not None:
            raise AssertionError(f"{action}: error envelope must have result=null, got: {body}")
        return body["error"]

    # -- anki-connect conveniences (thin wrappers, still API-only)

    def wait_healthy(self, tries: int = 60, delay: float = 1.0) -> bool:
        for _ in range(tries):
            status, _ = self.get("/health")
            if status == 200:
                return True
            time.sleep(delay)
        return False

    def add_note(
        self, deck: str, front: str, back: str, tags: list[str] | None = None, model: str = "Basic"
    ) -> int:
        note: dict[str, Any] = {
            "deckName": deck,
            "modelName": model,
            "fields": {"Front": front, "Back": back},
        }
        if tags:
            note["tags"] = tags
        nid = self.ok("addNote", {"note": note})
        assert isinstance(nid, int), f"addNote returned {nid!r}"
        return nid

    def add_note_model(
        self, deck: str, front: str, back: str, tags: list[str] | None = None, model: str = "Basic"
    ) -> int:
        """Add a note and return its first card id."""
        self.add_note(deck, front, back, tags, model)
        cids = self.ok("findCards", {"query": f'deck:"{deck}" Front:"{front}"'})
        assert cids, "note added but no card found"
        return cids[0]

    def find_cards(self, query: str) -> list[int]:
        return self.ok("findCards", {"query": query})

    def cards_info(self, ids: list[int]) -> list[dict[str, Any]]:
        return self.ok("cardsInfo", {"cards": ids})

    def create_deck(self, name: str) -> int:
        return self.ok("createDeck", {"deck": name})

    def store_media_b64(self, filename: str, text: str) -> None:
        import base64

        self.ok(
            "storeMediaFile",
            {"filename": filename, "data": base64.b64encode(text.encode()).decode()},
        )


def die(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(2)
