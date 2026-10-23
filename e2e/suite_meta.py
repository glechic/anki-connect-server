#!/usr/bin/env python3
"""E2E black-box suite — meta actions (MT-01..MT-14): apiReflect, reloadCollection, requestPermission, README parity, legacy envelope.

Every case's criteria are inlined as a "# Spec:" comment under its banner.

Usage (from repo root):
    python3 e2e/suite_meta.py [BASE_URL] [README.md]

API-only (C6): never imports anki_connect_server or anki; every assertion is
made against HTTP responses. The optional README argument (default: the repo README)
is project documentation used solely by MT-12/MT-14 doc-parity
parsing — it is not server source.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from anki_client import Client, check, die, record, summary

DEFAULT_README = str(Path(__file__).resolve().parent.parent / "README.md")

EXPECTED_RP = {"permission": "granted", "requireApikey": False, "version": 6}
EXPECTED_COUNT = 94  # 91 upstream + canAddNotesWithErrorDetail + syncMedia + syncStatus
REQUIRED_MEMBERS = [
    "answerCards",
    "apiReflect",
    "reloadCollection",
    "requestPermission",
    "insertReviews",
    "findAndReplaceInModels",
    "version",
    "multi",
]

# No-param README actions that MUST succeed on a fresh collection (via multi).
SPOT_SAFE = [
    "version",
    "deckNames",
    "deckNamesAndIds",
    "modelNames",
    "modelNamesAndIds",
    "getTags",
    "getMediaDirPath",
    "getNumCardsReviewedToday",
    "reloadCollection",
    "requestPermission",
]
# No-param README actions where an error envelope is still a valid response
# (no AnkiWeb credentials configured / effectively-required param).
SPOT_TOLERANT = [
    "sync",
    "syncStatus",
    "syncMedia",
    "apiReflect",
    "getMediaFilesNames",
    "getCollectionStatsHTML",
    "getNumCardsReviewedByDay",
]
# No-param but destructive — deliberately NOT executed in the spot-check.
SPOT_SKIPPED = ["removeEmptyNotes", "clearUnusedTags"]

c: Client  # set in main()


# ---------------------------------------------------------------- helpers


def ev(action: str, params: Any, body: Any, version: Any = 6, path: str = "/api") -> str:
    """One-line request/response evidence string (truncated)."""
    req = {"action": action, "version": version, "params": params, "path": path}
    try:
        req_s = json.dumps(req, sort_keys=True)
    except (TypeError, ValueError):
        req_s = repr(req)
    if isinstance(body, str):
        resp_s = body[:400]
    else:
        try:
            resp_s = json.dumps(body, sort_keys=True)[:400]
        except (TypeError, ValueError):
            resp_s = repr(body)[:400]
    return f"req={req_s} -> resp={resp_s}"


def req(action: str, params: Any = None, version: int = 6, path: str = "/api") -> tuple[int, Any]:
    """Client.request that never crashes on a non-JSON body."""
    try:
        return c.request(action, params, version, path)
    except (json.JSONDecodeError, ValueError) as e:
        return 0, f"<non-JSON response: {e}>"


def raw(payload: Any, path: str = "/api") -> tuple[int, Any]:
    """Client.raw_post that never crashes on a non-JSON body."""
    try:
        return c.raw_post(payload, path)
    except (json.JSONDecodeError, ValueError) as e:
        return 0, f"<non-JSON response: {e}>"


def is_err_envelope(status: int, body: Any) -> bool:
    """C3: client-caused errors must be HTTP 200 {result: null, error: str}."""
    return (
        status == 200
        and isinstance(body, dict)
        and isinstance(body.get("error"), str)
        and body.get("result") is None
    )


def unpack(entry: Any) -> tuple[Any, Any]:
    """Normalize a multi entry to (result, error).

    Upstream semantics (verified in AnkiConnect's util.py): a successful
    entry is the bare value when the entry's own version is <= 4 or absent
    (the common case), or {"result": .., "error": null} for version >= 5;
    a failed entry is always {"result": null, "error": ".."} regardless of
    version. Support every shape so the "action responded" judgement is
    identical either way.
    """
    if isinstance(entry, dict) and set(entry.keys()) == {"result", "error"}:
        return entry["result"], entry["error"]
    if isinstance(entry, dict) and "result" in entry and "error" in entry:
        return entry["result"], entry["error"]
    return entry, None


def resilient() -> None:
    """C5: silent resilience probe after an error case (records only failures)."""
    status, _ = c.get("/health")
    if status != 200:
        check("MT-14", False, f"/health returned {status} immediately after an error case")


def parse_readme(path: Path) -> tuple[list[str], str]:
    """Return (names under '### Supported Actions', 'Not supported' section text)."""
    text = path.read_text(encoding="utf-8")
    m_start = re.search(r"^### Supported Actions\s*$", text, re.MULTILINE)
    if not m_start:
        die(f"{path}: '### Supported Actions' section not found")
    rest = text[m_start.end() :]
    m_stop = re.search(r"^#### Not supported \(headless server\)\s*$", rest, re.MULTILINE)
    if not m_stop:
        die(f"{path}: '#### Not supported (headless server)' section not found")
    names = []
    for line in rest[: m_stop.start()].splitlines():
        m = re.match(r"^- `([A-Za-z0-9_]+)`", line.strip())
        if m:
            names.append(m.group(1))
    return names, rest[m_stop.start() :]


# ---------------------------------------------------------------- main


def main() -> int:
    if len(sys.argv) < 2:
        die("usage: suite_meta.py <base_url> [readme_path]")
    base = sys.argv[1]
    readme = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(DEFAULT_README)

    global c
    c = Client(base, timeout=90.0)
    if not c.wait_healthy():
        die(f"{base}/health never returned 200")
    record("ENV", f"server healthy at {base}")

    # ------------------------------------------------ MT-01 apiReflect happy
    # Spec: MT-01 — apiReflect happy {scopes:["actions"], actions:null} → {"scopes":["actions"],
    #       "actions":[...all registered...]}. Count the actions — expected 94 (91 upstream +
    #       canAddNotesWithErrorDetail + syncMedia + syncStatus). Record the count. Assert members:
    #       answerCards, apiReflect, reloadCollection, requestPermission, insertReviews,
    #       findAndReplaceInModels, version, multi. Assert NO gui* members and no getProfiles/loadProfile.
    params = {"scopes": ["actions"], "actions": None}
    status, body = req("apiReflect", params)
    result = body.get("result") if isinstance(body, dict) else None
    actions = result.get("actions") if isinstance(result, dict) else None
    check(
        "MT-01",
        status == 200
        and isinstance(result, dict)
        and result.get("scopes") == ["actions"]
        and isinstance(actions, list)
        and body.get("error") is None,
        ev("apiReflect", params, body),
    )
    if not isinstance(actions, list):
        actions = []
    record("MT-01", f"apiReflect reports {len(actions)} actions")
    check(
        "MT-01",
        len(actions) == EXPECTED_COUNT,
        f"expected {EXPECTED_COUNT} actions, got {len(actions)}: {sorted(actions)}",
    )
    missing = [m for m in REQUIRED_MEMBERS if m not in actions]
    check("MT-01", not missing, f"required members missing: {missing} (count={len(actions)})")
    gui = [a for a in actions if a.startswith("gui")]
    check("MT-01", not gui, f"gui* members present: {gui}")
    banned = [a for a in ("getProfiles", "loadProfile") if a in actions]
    check("MT-01", not banned, f"headless-excluded members present: {banned}")

    # ------------------------------------------------ MT-02 apiReflect filter
    # Spec: MT-02 — apiReflect filter {scopes:["actions"], actions:["deckNames","nope","answerCards"]} →
    #       actions == ["deckNames","answerCards"] (unknown filtered, order preserved).
    params = {"scopes": ["actions"], "actions": ["deckNames", "nope", "answerCards"]}
    status, body = req("apiReflect", params)
    result = body.get("result") if isinstance(body, dict) else None
    got = result.get("actions") if isinstance(result, dict) else None
    check(
        "MT-02",
        status == 200
        and got == ["deckNames", "answerCards"]
        and isinstance(result, dict)
        and result.get("scopes") == ["actions"]
        and body.get("error") is None,
        f"expected actions ['deckNames', 'answerCards'] (order preserved, unknown filtered); {ev('apiReflect', params, body)}",
    )

    # ------------------------------------------------ MT-03 empty actions list
    # Spec: MT-03 — apiReflect empty actions list actions: [] → actions == [], scopes still ["actions"].
    params = {"scopes": ["actions"], "actions": []}
    status, body = req("apiReflect", params)
    result = body.get("result") if isinstance(body, dict) else None
    check(
        "MT-03",
        status == 200
        and result == {"scopes": ["actions"], "actions": []}
        and body.get("error") is None,
        ev("apiReflect", params, body),
    )

    # ------------------------------------------------ MT-04 no scopes
    # Spec: MT-04 — apiReflect no scopes {scopes:[]} → {"scopes": []} and no "actions" key.
    params = {"scopes": []}
    status, body = req("apiReflect", params)
    result = body.get("result") if isinstance(body, dict) else None
    check(
        "MT-04",
        status == 200 and result == {"scopes": []} and body.get("error") is None,
        f"expected exactly {{'scopes': []}} with no 'actions' key; {ev('apiReflect', params, body)}",
    )

    # ------------------------------------------------ MT-05 unknown scope
    # Spec: MT-05 — apiReflect unknown scope {scopes:["decks"]} → {"scopes": []} (silently ignored —
    #       upstream supports decks/cards/notes scopes; this server only "actions". Record as
    #       OBS/divergence).
    params = {"scopes": ["decks"]}
    status, body = req("apiReflect", params)
    result = body.get("result") if isinstance(body, dict) else None
    check(
        "MT-05",
        status == 200 and result == {"scopes": []} and body.get("error") is None,
        f"unknown scope silently ignored; {ev('apiReflect', params, body)}",
    )
    record(
        "MT-05",
        "divergence: upstream apiReflect supports decks/cards/notes scopes; "
        "this server only supports 'actions' and answers {'scopes': []} for others",
    )

    # ------------------------------------------------ MT-06 non-string action entry
    # Spec: MT-06 — apiReflect non-string action entry (documented divergence) {scopes:["actions"],
    #       actions:[42]} → error envelope (pydantic list[str] rejects; upstream silently skips). Record.
    params = {"scopes": ["actions"], "actions": [42]}
    status, body = req("apiReflect", params)
    check(
        "MT-06",
        is_err_envelope(status, body),
        f"expected error envelope for non-string action entry; {ev('apiReflect', params, body)}",
    )
    record(
        "MT-06",
        f"documented divergence: non-string action entries rejected with {body.get('error')!r} "
        "(upstream silently skips them); spec expects error envelope",
    )
    resilient()

    # ------------------------------------------------ MT-07 invalid types
    # Spec: MT-07 — apiReflect invalid types scopes:"actions" (string not list) → error envelope;
    #       actions:"deckNames" → error envelope.
    params = {"scopes": "actions"}
    status, body = req("apiReflect", params)
    check(
        "MT-07a",
        is_err_envelope(status, body),
        f"scopes as string must be an error envelope; {ev('apiReflect', params, body)}",
    )
    params = {"scopes": ["actions"], "actions": "deckNames"}
    status, body = req("apiReflect", params)
    check(
        "MT-07b",
        is_err_envelope(status, body),
        f"actions as string must be an error envelope; {ev('apiReflect', params, body)}",
    )
    resilient()

    # ------------------------------------------------ MT-08 reloadCollection
    # Spec: MT-08 — reloadCollection → result null, error null. Afterwards deckNames and version still
    #       work (server healthy).
    params: Any = {}
    status, body = req("reloadCollection", params)
    check(
        "MT-08",
        status == 200
        and isinstance(body, dict)
        and body.get("result") is None
        and body.get("error") is None,
        f"expected {{'result': None, 'error': None}}; {ev('reloadCollection', params, body)}",
    )
    names = c.ok("deckNames")
    check("MT-08", isinstance(names, list), f"deckNames after reloadCollection returned {names!r}")
    version = c.ok("version")
    check("MT-08", version == 6, f"version after reloadCollection returned {version!r}")

    # ------------------------------------------------ MT-09 reloadCollection stray param
    # Spec: MT-09 — reloadCollection stray param {foo:1} → error envelope (extra=forbid).
    params = {"foo": 1}
    status, body = req("reloadCollection", params)
    check(
        "MT-09",
        is_err_envelope(status, body),
        f"stray param must be an error envelope (extra=forbid); {ev('reloadCollection', params, body)}",
    )
    resilient()

    # ------------------------------------------------ MT-10 requestPermission
    # Spec: MT-10 — requestPermission → EXACT {"permission":"granted","requireApikey":false,"version":6}.
    params = {}
    status, body = req("requestPermission", params)
    check(
        "MT-10",
        status == 200
        and isinstance(body, dict)
        and body.get("result") == EXPECTED_RP
        and body.get("error") is None,
        f"expected result exactly {EXPECTED_RP}; {ev('requestPermission', params, body)}",
    )

    # ------------------------------------------------ MT-11 requestPermission stray param
    # Spec: MT-11 — requestPermission stray param → error envelope.
    params = {"foo": 1}
    status, body = req("requestPermission", params)
    check(
        "MT-11",
        is_err_envelope(status, body),
        f"stray param must be an error envelope (extra=forbid); {ev('requestPermission', params, body)}",
    )
    resilient()

    # ------------------------------------------------ MT-12 README parity
    # Spec: MT-12 — README parity sweep every action listed in README's "Supported Actions" section must
    #       appear in apiReflect's action list; and every action in apiReflect's list that README
    #       documents must respond (spot-execute the no-param ones via multi).
    #       Also in this slice (doc check): README's "Not supported (headless server)" section must
    #       document getProfiles, loadProfile, and the gui* actions (README parsing, not runtime).
    if not readme.is_file():
        die(f"README not found: {readme}")
    readme_names, not_supported = parse_readme(readme)
    reflect_set = set(actions)
    not_in_reflect = [a for a in readme_names if a not in reflect_set]
    check(
        "MT-12",
        not not_in_reflect,
        f"README-documented actions missing from apiReflect: {not_in_reflect} "
        f"(README lists {len(readme_names)} actions)",
    )
    undocumented = sorted(reflect_set - set(readme_names))
    record(
        "MT-12",
        f"README documents {len(readme_names)} supported actions; apiReflect reports "
        f"{len(actions)}; present in apiReflect but not documented in README: {undocumented}",
    )
    check(
        "MT-12",
        "getProfiles" in not_supported and "loadProfile" in not_supported,
        "'Not supported (headless server)' section must mention getProfiles and loadProfile",
    )
    gui_doc = re.findall(r"`(gui[A-Za-z0-9_]*)`", not_supported)
    check("MT-12", bool(gui_doc), "gui* actions not mentioned in the 'Not supported' section")
    record(
        "MT-12",
        f"'Not supported (headless server)' documents getProfiles+loadProfile and "
        f"{len(gui_doc)} gui* actions: {gui_doc[:5]}...",
    )

    # spot-execute no-param README-documented actions via multi
    spot = SPOT_SAFE + SPOT_TOLERANT
    multi_params = {"actions": [{"action": a, "params": {}} for a in spot]}
    status, body = req("multi", multi_params)
    entries = body.get("result") if isinstance(body, dict) else None
    responded = (
        status == 200
        and isinstance(entries, list)
        and len(entries) == len(spot)
        and body.get("error") is None
    )
    check(
        "MT-12",
        responded,
        f"every spot-executed action must respond in order ({len(spot)} expected); "
        f"{ev('multi', multi_params, body)}",
    )
    if isinstance(entries, list):
        # P2-4 fixed contract (verified against upstream util.py):
        # - failure entries are ALWAYS {"result": null, "error": "..."}
        # - success entries follow the entry's own version: bare for
        #   version <= 4 / absent (upstream's default), envelope for >= 5.
        probe_params = {
            "actions": [
                {"action": "version"},  # bare success
                {"action": "definitelyNotAnAction", "params": {}},  # failure
                {"action": "version", "version": 6},  # envelope success
            ]
        }
        pstatus, pbody = req("multi", probe_params)
        probe_ok = (
            pstatus == 200
            and isinstance(pbody.get("result"), list)
            and pbody["result"][0] == 6
            and pbody["result"][1]
            == {
                "result": None,
                "error": "Unsupported action: definitelyNotAnAction",
            }
            and pbody["result"][2] == {"result": 6, "error": None}
        )
        check(
            "MULTI",
            probe_ok,
            f"multi per-entry shapes must match upstream; {ev('multi', probe_params, pbody)}",
        )
        check(
            "MT-12",
            len(spot) == len(entries),
            f"multi must return one entry per requested action: {len(entries)} for {len(spot)}",
        )
        for i, name in enumerate(spot):
            result, error = unpack(entries[i])
            if name in SPOT_SAFE:
                check(
                    "MT-12",
                    error is None,
                    f"no-param action {name} must succeed via multi; got entry {entries[i]!r}",
                )
            else:
                state = "ok" if error is None else f"error entry: {error!r}"
                record("MT-12", f"no-param action {name} via multi -> {state}")
    record("MT-12", f"destructive no-param actions skipped by design: {SPOT_SKIPPED}")
    resilient()

    # ------------------------------------------------ MT-13 legacy envelope + "/" path
    # Spec: MT-13 — envelope/legacy requestPermission with version=4 → bare object (no envelope); / path
    #       behaves like /api.
    status, body = req("requestPermission", {}, version=4)
    check(
        "MT-13",
        status == 200 and body == EXPECTED_RP,
        f"version 4 must return the bare object (no envelope); {ev('requestPermission', {}, body, version=4)}",
    )
    status, body = raw({"action": "requestPermission", "params": {}})
    check(
        "MT-13",
        status == 200 and body == EXPECTED_RP,
        f"missing version (defaults to 4) must return the bare object; "
        f"req={{'action': 'requestPermission', 'params': {{}}}} (no version key) -> resp={body!r}",
    )
    _, api_body = req("requestPermission", {}, version=6, path="/api")
    status, body = req("requestPermission", {}, version=6, path="/")
    check(
        "MT-13",
        status == 200 and body == api_body,
        f"'/' path must behave like '/api'; {ev('requestPermission', {}, body, path='/')} ; /api -> {api_body!r}",
    )
    status, body = req("requestPermission", {}, version=4, path="/")
    check(
        "MT-13",
        status == 200 and body == EXPECTED_RP,
        f"'/' with version 4 must return the bare object; {ev('requestPermission', {}, body, version=4, path='/')}",
    )
    resilient()

    # ------------------------------------------------ C3 unknown action (common criterion)
    status, body = req("definitelyNotAnAction")
    check(
        "C3",
        is_err_envelope(status, body),
        f"unknown action must be an HTTP 200 error envelope; {ev('definitelyNotAnAction', None, body)}",
    )
    resilient()

    # ------------------------------------------------ MT-14 resilience
    # Spec: MT-14 — resilience /health == 200 after all error cases.
    status, _ = c.get("/health")
    check("MT-14", status == 200, f"final /health status = {status}")
    v = c.ok("version")
    check("MT-14", v == 6, f"server still serves after all cases (version -> {v!r})")

    return summary()


if __name__ == "__main__":
    sys.exit(main())
