#!/usr/bin/env python3
"""E2E suite: AnkiWeb-sync feature vs a real local anki.syncserver (SY-01..SY-12).

Topology (podman; build ONE image acs-e2e:sync from the revision under test
and use it for all four containers):

    podman build -t acs-e2e:sync <checkout-of-revision>
    podman network create acs-e2enet

    # sync server (creds e2e/e2e, port 8270 inside the network)
    podman run -d --name acs-e2e-syncsrv --network acs-e2enet \
      -e SYNC_USER1=e2e:e2e -e SYNC_BASE=/syncdata -e SYNC_HOST=0.0.0.0 \
      -e SYNC_PORT=8270 acs-e2e:sync uv run python -m anki.syncserver

    # API server A — the "producer" (port 18790)
    podman run -d --name acs-e2e-synca --network acs-e2enet -p 18790:8765 \
      -e ANKICONNECT_COLLECTION_PATH=/data/collection.anki2 \
      -e ANKICONNECT_ANKIWEB_USER=e2e -e ANKICONNECT_ANKIWEB_PASS=e2e \
      -e ANKICONNECT_ANKIWEB_URL=http://acs-e2e-syncsrv:8270/ acs-e2e:sync

    # API server B — the "consumer" (port 18791): same creds, fresh collection
    # (same env as A but -p 18791:8765 --name acs-e2e-syncb)

    # API server C — no credentials at all (port 18792):
    # (-p 18792:8765 --name acs-e2e-syncnone, only COLLECTION_PATH env)

If container-name DNS fails on the podman network, resolve the sync server IP
with `podman inspect acs-e2e-syncsrv` and substitute it in
ANKICONNECT_ANKIWEB_URL. Reset the sync server between runs (stale account
state causes confusing failures):

    podman rm -f acs-e2e-syncsrv acs-e2e-synca acs-e2e-syncb acs-e2e-syncnone
    podman network rm acs-e2enet   # then recreate everything

`sync`/`syncStatus`/`syncMedia` accept per-request username/password/endpoint
params — the suite uses these to vary credentials without new containers.

Black-box, API-only: every assertion goes through POST /api via
e2e/anki_client.py; the suite never imports anki / anki_connect_server and
never touches a collection file. Cases SY-01..SY-12 run in ID order and every
case's criteria are inlined as a "# Spec:" comment under its banner (the
order matters: it shapes the sync server's account state).

Run:  python3 e2e/suite_sync.py [A_BASE B_BASE C_BASE]
"""

from __future__ import annotations

import json
import sys
import threading
from typing import Any

from anki_client import Client, check, record, summary

A_BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:18790"
B_BASE = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:18791"
C_BASE = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:18792"

A = Client(A_BASE, timeout=180.0)
B = Client(B_BASE, timeout=180.0)
C = Client(C_BASE, timeout=180.0)

LOCK_ERR = "A synchronization is already in progress"
# P1-1 fix contract: with local data and an EMPTY remote, anki requires
# FULL_UPLOAD and the server seeds the account (outcome "uploaded").
# Media does not ride along on full-sync paths (anki starts the background
# media sync only when the requirement is NOT FullSyncRequired); it flows on
# the next sync or an explicit syncMedia.


def fmt(obj: Any, limit: int = 300) -> str:
    """Compact JSON evidence."""
    s = json.dumps(obj) if isinstance(obj, (dict, list, int, str, type(None))) else repr(obj)
    return s if len(s) <= limit else s[:limit] + f"...({len(s)}B)"


def show(action: str, params: Any, status: int, body: Any) -> str:
    return f"POST /api {action} params={json.dumps(params)} -> HTTP {status} {fmt(body)}"


def call(client: Client, action: str, params: dict[str, Any] | None = None) -> tuple[int, Any, Any]:
    """POST /api; return (http_status, error, result)."""
    status, body = client.request(action, params)
    if isinstance(body, dict):
        return status, body.get("error"), body.get("result")
    return status, f"non-JSON body: {body!r}", None


# ---------------------------------------------------------------- SY-00 preflight


def sy00_preflight() -> None:
    for name, cl in (("A", A), ("B", B), ("C", C)):
        record("SY-00", f"{name} {cl.base_url} /health: {cl.get('/health')[0]}")
    # C1 spot-check: actions also respond on POST /
    st, body = A.raw_post({"action": "version", "version": 6, "params": {}}, path="/")
    ok = (
        st == 200
        and isinstance(body, dict)
        and body.get("result") == 6
        and body.get("error") is None
    )
    check("SY-00", ok, f"C1 spot: POST / version -> HTTP {st} {fmt(body)}")


# ---------------------------------------------------------------- SY-01 syncStatus
# Spec: SY-01 — syncStatus happy on A: {} → result {"server":..., "status":..., "required":...}. Record
#       the shape; expect required to indicate pending changes or client/server state. NOT an error.


def sy01_sync_status_happy() -> None:
    status, err, res = call(A, "syncStatus")
    if err is not None:
        check(
            "SY-01",
            False,
            f"syncStatus errored: {show('syncStatus', {}, status, res if res else err)}",
        )
        return
    record("SY-01", f"syncStatus result shape: {fmt(res, 800)}")
    ok = status == 200 and isinstance(res, dict) and isinstance(res.get("required"), int)
    check(
        "SY-01",
        ok,
        f"syncStatus not an error; result keys={sorted(res) if isinstance(res, dict) else None}, required={res.get('required') if isinstance(res, dict) else None}",
    )
    # P3-9 fixed contract: anki 26.8 carries only the sync requirement, so
    # the always-empty server/status strings are omitted (keys == ['required']).
    if isinstance(res, dict):
        check(
            "SY-01",
            set(res) == {"required"},
            f"syncStatus keys must be exactly ['required'] on anki 26.8; got {sorted(res)}",
        )


# ---------------------------------------------------------------- SY-02 first sync (empty <-> empty)
# Spec: SY-02 — first sync (empty ↔ empty) on A (fresh, no local data): sync {} →
#       {"status":"completed","collection":{"outcome":<no_changes|merged>,"local_data_replaced":false},"media":{...}}.
#       Record the outcome. If it fails (e.g. the full-upload policy: "only a full upload is possible;
#       full uploads are disabled by policy") → record exact error + HTTP status — that is a legitimate
#       finding about fresh-deployment UX (ISSUE candidate: a brand-new client against a brand-new server
#       account can never push).


def sy02_first_sync() -> None:
    status, err, res = call(A, "sync")
    if err is None and isinstance(res, dict):
        coll = res.get("collection") or {}
        record(
            "SY-02",
            f"first sync (fresh-empty client vs fresh-empty server account): {fmt(res, 800)}",
        )
        ok = (
            status == 200
            and res.get("status") == "completed"
            and coll.get("outcome") in ("no_changes", "merged")
            and coll.get("local_data_replaced") is False
        )
        check(
            "SY-02",
            ok,
            f"first sync completed with outcome={coll.get('outcome')!r}, local_data_replaced={coll.get('local_data_replaced')}",
        )
    else:
        record("SY-02", f"first sync failed: HTTP {status}, error={err!r}")
        check(
            "SY-02",
            False,
            f"first sync (empty client vs empty server) failed: HTTP {status}, error={err!r}",
        )


# ---------------------------------------------------------------- SY-03 sync after local changes
# Spec: SY-03 — sync after changes (P1-1 fixed contract) A: createDeck "SyncDeck", add note (Front
#       sync-F1, tag synctag), storeMediaFile {filename "sync-asset.txt", data base64("sync")}. Then sync
#       {} → completed, outcome == "uploaded" (local data + empty remote → anki requires FULL_UPLOAD → the
#       server seeds the account; uploading is safe because FULL_UPLOAD implies remote.empty). Then sync
#       {} AGAIN → outcome == "no_changes" (this second sync also pushes A's media in the background).


def sy03_sync_after_changes() -> None:
    A.create_deck("SyncDeck")
    A.add_note("SyncDeck", "sync-F1", "sync-F1-back", tags=["synctag"])
    A.store_media_b64("sync-asset.txt", "sync")
    record(
        "SY-03",
        "fixtures on A: deck SyncDeck, note Front=sync-F1 (tag synctag), media sync-asset.txt",
    )

    status, err, res = call(A, "sync")
    if err is None and isinstance(res, dict):
        coll = res.get("collection") or {}
        # P1-1 fix contract: with local data + an EMPTY remote, anki requires
        # FULL_UPLOAD and the server now seeds the account (outcome=uploaded;
        # uploading is safe because FULL_UPLOAD implies remote.empty).
        check(
            "SY-03",
            status == 200 and coll.get("outcome") == "uploaded",
            f"seeding sync (local data, empty remote) -> {show('sync', {}, status, res)} (expected outcome=uploaded)",
        )
        first_ok = True
    else:
        check("SY-03", False, f"seeding sync failed: HTTP {status}, error={err!r}")
        first_ok = False

    status2, err2, res2 = call(A, "sync")
    if first_ok and err2 is None and isinstance(res2, dict):
        coll2 = res2.get("collection") or {}
        check(
            "SY-03",
            coll2.get("outcome") == "no_changes",
            f"idempotent second sync -> outcome={coll2.get('outcome')!r} (expected no_changes)",
        )
    elif not first_ok:
        record("SY-03", f"second sync after the failed first: HTTP {status2}, error={err2!r}")
    else:
        check("SY-03", False, f"second sync failed: HTTP {status2}, error={err2!r}")


# ---------------------------------------------------------------- SY-04 round-trip (core)
# Spec: SY-04 — round-trip (the core assertion) B (fresh): sync {} → completed, collection.outcome ==
#       "downloaded", local_data_replaced == true. Then on B: deckNames contains "SyncDeck"; findNotes
#       {query:'Front:"sync-F1"'} → 1 note; notesInfo fields Front == "sync-F1", tags contain "synctag".
#       Media does NOT ride along on full-sync paths (anki only starts the background media sync when the
#       requirement is not FullSyncRequired), so pull it with an explicit syncMedia {} — then
#       getMediaFilesNames "*" contains "sync-asset.txt".


def sy04_roundtrip() -> None:
    status, err, res = call(B, "sync")
    if err is None and isinstance(res, dict):
        coll = res.get("collection") or {}
        check(
            "SY-04",
            status == 200
            and res.get("status") == "completed"
            and coll.get("outcome") == "downloaded"
            and coll.get("local_data_replaced") is True,
            f"B (fresh) sync -> {show('sync', {}, status, res)} (expected outcome=downloaded, local_data_replaced=true)",
        )
    else:
        check("SY-04", False, f"B (fresh) sync failed: HTTP {status}, error={err!r}")

    try:
        decks = B.ok("deckNames")
    except AssertionError as e:
        check("SY-04", False, f"B deckNames after sync failed: {e}")
        decks = []
    check("SY-04", "SyncDeck" in decks, f"B deckNames after sync: {decks}")

    try:
        nids = B.ok("findNotes", {"query": 'Front:"sync-F1"'})
    except AssertionError as e:
        check("SY-04", False, f"B findNotes failed: {e}")
        nids = []
    check("SY-04", len(nids) == 1, f"B findNotes Front:synctag -> {nids} (expected exactly 1 note)")

    if nids:
        try:
            info = B.ok("notesInfo", {"notes": nids})
        except AssertionError as e:
            check("SY-04", False, f"B notesInfo failed: {e}")
            info = []
        if info:
            ni = info[0]
            front = (ni.get("fields", {}).get("Front") or {}).get("value")
            check(
                "SY-04",
                front == "sync-F1" and "synctag" in ni.get("tags", []),
                f"B notesInfo: Front={front!r}, tags={ni.get('tags')}",
            )
    # Media does NOT ride along on full-sync paths (anki's sync_collection
    # only starts the background media sync when the requirement is not
    # FullSyncRequired), so pull it with an explicit syncMedia — the same
    # flow desktop Anki's media_syncer performs after a full sync.
    sm_st, sm_err, sm_res = call(B, "syncMedia")
    record(
        "SY-04",
        f"B syncMedia after full download: HTTP {sm_st} "
        f"{fmt(sm_res if sm_err is None else {'error': sm_err}, 300)}",
    )
    try:
        names = B.ok("getMediaFilesNames", {"pattern": "*"})
    except AssertionError as e:
        check("SY-04", False, f"B getMediaFilesNames failed: {e}")
        names = []
    check("SY-04", "sync-asset.txt" in names, f"B media files after sync + syncMedia: {names}")


# ---------------------------------------------------------------- SY-05 two-way sync
# Spec: SY-05 — B is not a black hole B: add note sync-F2 in SyncDeck → sync → completed (outcome merged
#       or, per anki's post-sync reporting, no_changes — a completed normal sync always reports
#       no_changes, see rslib normal.rs; the data assertions below are the real proof); A: sync → same; A
#       findNotes Front:"sync-F2" → found. (Two-way sync.)


def sy05_two_way() -> None:
    try:
        nid = B.add_note("SyncDeck", "sync-F2", "sync-F2-back")
        record(
            "SY-05", f"B added note sync-F2 (id {nid}) to deck SyncDeck (deck auto-created on B)"
        )
    except AssertionError as e:
        check("SY-05", False, f"B addNote sync-F2 failed: {e}")
        return
    s1, e1, r1 = call(B, "sync")
    # anki semantics (rslib normal.rs): a *completed* normal sync always
    # reports required=NO_CHANGES (the post-sync state) — "merged" is
    # unreachable via sync. The data-flow checks below carry the proof.
    ok1 = (
        e1 is None
        and isinstance(r1, dict)
        and (r1.get("collection") or {}).get("outcome") in ("merged", "no_changes")
    )
    check(
        "SY-05",
        ok1,
        f"B sync after adding sync-F2: {show('sync', {}, s1, r1 if e1 is None else {'error': e1})} (expected merged|no_changes; data checks follow)",
    )

    s2, e2, r2 = call(A, "sync")
    ok2 = (
        e2 is None
        and isinstance(r2, dict)
        and (r2.get("collection") or {}).get("outcome") in ("merged", "no_changes")
    )
    check(
        "SY-05",
        ok2,
        f"A sync after B's: {show('sync', {}, s2, r2 if e2 is None else {'error': e2})} (expected merged|no_changes; data checks follow)",
    )

    try:
        nids = A.ok("findNotes", {"query": 'Front:"sync-F2"'})
    except AssertionError as e:
        check("SY-05", False, f"A findNotes failed: {e}")
        nids = []
    check("SY-05", len(nids) == 1, f"A findNotes Front:sync-F2 -> {nids} (B is not a black hole)")


# ---------------------------------------------------------------- SY-06 syncMedia
# Spec: SY-06 — syncMedia B: store "sync2.txt" → syncMedia {} → {outcome:"completed", checked:..., ...}
#       (record); A: syncMedia {} → A's getMediaFilesNames contains "sync2.txt".


def sy06_sync_media() -> None:
    try:
        B.store_media_b64("sync2.txt", "sync2-content")
        record("SY-06", "B stored media file sync2.txt")
    except AssertionError as e:
        check("SY-06", False, f"B storeMediaFile failed: {e}")
        return
    s1, e1, r1 = call(B, "syncMedia")
    record("SY-06", f"B syncMedia: HTTP {s1} {fmt(r1 if e1 is None else {'error': e1}, 400)}")
    check(
        "SY-06",
        e1 is None and isinstance(r1, dict) and r1.get("outcome") == "completed",
        f"B syncMedia -> outcome={r1.get('outcome') if isinstance(r1, dict) else None!r} (expected completed)",
    )

    s2, e2, r2 = call(A, "syncMedia")
    record("SY-06", f"A syncMedia: HTTP {s2} {fmt(r2 if e2 is None else {'error': e2}, 400)}")
    try:
        names = A.ok("getMediaFilesNames", {"pattern": "*"})
    except AssertionError as e:
        check("SY-06", False, f"A getMediaFilesNames failed: {e}")
        names = []
    check("SY-06", "sync2.txt" in names, f"A media files after syncMedia: {names}")

    # Exploratory: confirm A's media is fully on the server by now (pushed
    # during the post-seeding syncs) and that B's second syncMedia is a
    # stable no-op-style completion (bidirectional media still consistent).
    s3, e3, r3 = call(B, "syncMedia")
    try:
        names_b = B.ok("getMediaFilesNames", {"pattern": "*"})
    except AssertionError:
        names_b = []
    record(
        "SY-06",
        f"B second syncMedia: HTTP {s3} {fmt(r3 if e3 is None else {'error': e3}, 200)}; B media files: {names_b}",
    )


# ---------------------------------------------------------------- SY-07 wrong credentials
# Spec: SY-07 — wrong credentials A: sync {username:"e2e", password:"WRONG"} → error. Record HTTP status +
#       message. Per current design SyncError is a RuntimeError → likely HTTP 500
#       {"result":null,"error":"..."}; upstream AnkiConnect reports sync failures as 200 error envelopes.
#       Record and FLAG as divergence ISSUE.


def sy07_wrong_credentials() -> None:
    params = {"username": "e2e", "password": "WRONG"}
    status, err, res = call(A, "sync", params)
    # P2-3 fixed contract: client-caused sync failures are HTTP 200 error
    # envelopes like upstream (previously SyncError -> HTTP 500).
    check(
        "SY-07",
        err is not None and status == 200,
        f"wrong-password sync -> {show('sync', params, status, res if res is not None else {'error': err})} (expected HTTP 200 error envelope)",
    )
    if err is not None:
        record(
            "SY-07",
            f"wrong credentials: HTTP {status}, error={err!r}"
            + (
                ""
                if status == 200
                else " — REGRESSION: expected HTTP 200 error envelope (E2E P2-3)"
            ),
        )


# ---------------------------------------------------------------- SY-08 unreachable endpoint
# Spec: SY-08 — unreachable endpoint A: sync {endpoint:"http://acs-e2e-syncsrv:9999/"} → error; record
#       status + message (likely 500 — flag like SY-07). Server must stay healthy after (SY-11).


def sy08_unreachable_endpoint() -> None:
    params = {"endpoint": "http://acs-e2e-syncsrv:9999/"}
    status, err, res = call(A, "sync", params)
    check(
        "SY-08",
        err is not None and status == 200,
        f"unreachable-endpoint sync -> {show('sync', params, status, res if res is not None else {'error': err})} (expected HTTP 200 error envelope)",
    )
    # P2-3 sub-issue: the endpoint must appear in the message (anki's own
    # network error drops the URL: "error sending request for url ()").
    check(
        "SY-08",
        err is not None and "acs-e2e-syncsrv:9999" in str(err),
        f"error message must name the failing endpoint, got: {err!r}",
    )
    if err is not None:
        record("SY-08", f"unreachable endpoint: HTTP {status}, error={err!r}")


# ---------------------------------------------------------------- SY-09 no credentials configured
# Spec: SY-09 — no credentials configured on C: syncStatus {} → HTTP 200 error envelope containing
#       ANKICONNECT_ANKIWEB_USER and ANKICONNECT_ANKIWEB_PASS required for sync status. Same for sync
#       (message ends required for sync) and syncMedia (required for media sync). These are clean client
#       errors (ValueError) — assert 200 + envelope.


def sy09_no_credentials() -> None:
    for action, tail in (
        ("syncStatus", "required for sync status"),
        ("sync", "required for sync"),
        ("syncMedia", "required for media sync"),
    ):
        try:
            err = C.err(action)  # asserts HTTP 200 + {"result": null, "error": str}
        except AssertionError as e:
            check("SY-09", False, f"{action} on C: expected HTTP 200 error envelope, got: {e}")
            continue
        ok = (
            err.startswith("ANKICONNECT_ANKIWEB_USER and ANKICONNECT_ANKIWEB_PASS required for")
            and tail in err
        )
        check("SY-09", ok, f"{action} on C: HTTP 200 error envelope: {err!r}")


# ---------------------------------------------------------------- SY-10 concurrent sync lock
# Spec: SY-10 — concurrent sync lock on A fire two sync requests concurrently (two threads) → exactly one
#       succeeds; the other errors A synchronization is already in progress. Record status code (500
#       expected — flag).


def _concurrent_pair() -> list[tuple[int, Any]]:
    out: list[tuple[int, Any]] = []
    barrier = threading.Barrier(2)

    def worker() -> None:
        barrier.wait()
        status, body = A.request("sync")
        out.append((status, body))

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return out


def sy10_concurrent_lock() -> None:
    for attempt in range(1, 6):
        pair = _concurrent_pair()
        errs = [b.get("error") if isinstance(b, dict) else str(b) for _, b in pair]
        lock_hits = [i for i, e in enumerate(errs) if e and LOCK_ERR in e]
        record(
            "SY-10",
            f"attempt {attempt}: "
            + "; ".join(f"[{i}] HTTP {st} {fmt(b, 260)}" for i, (st, b) in enumerate(pair)),
        )
        if len(lock_hits) == 1:
            loser_i = lock_hits[0]
            winner_i = 1 - loser_i
            loser_status = pair[loser_i][0]
            winner_status, winner_body = pair[winner_i]
            check(
                "SY-10",
                True,
                f"exactly one request got the lock error (loser: HTTP {loser_status} {errs[loser_i]!r}); winner: HTTP {winner_status} {fmt(winner_body, 160)}",
            )
            # P2-3 fixed contract: the lock error is a client-caused failure
            # and must reach clients in the HTTP 200 error envelope (not 500).
            check(
                "SY-10",
                loser_status == 200,
                f"lock-error loser must be HTTP 200 (error envelope), got {loser_status}",
            )
            record(
                "SY-10",
                f"lock-error loser HTTP status: {loser_status}"
                + (
                    f" — DIVERGENCE FLAG: upstream reports this as a 200 error envelope, here HTTP {loser_status}"
                    if loser_status != 200
                    else " (200 error envelope, matches upstream)"
                ),
            )
            return
    check(
        "SY-10",
        False,
        "5 attempts, never observed exactly one lock error; see recorded pairs (server may serialize the requests)",
    )


# ---------------------------------------------------------------- SY-11 resilience
# Spec: SY-11 — resilience after SY-07/08/10 failures, on A and B: /health == 200, CRUD works (version,
#       addNote, findNotes). A failed sync must not wedge the collection (the wrapper reopens it).


def sy11_resilience() -> None:
    for name, cl in (("A", A), ("B", B)):
        status, _txt = cl.get("/health")
        check("SY-11", status == 200, f"{name} /health after failed syncs: {status}")
        try:
            v = cl.ok("version")
        except AssertionError as e:
            check("SY-11", False, f"{name} version failed: {e}")
            continue
        check("SY-11", v == 6, f"{name} version after failed syncs: {v}")
        try:
            front = f"resilient-{name.lower()}"
            nid = cl.add_note("ResilienceDeck", front, "back")
            nids = cl.ok("findNotes", {"query": f'Front:"{front}"'})
            check(
                "SY-11",
                isinstance(nid, int) and len(nids) == 1,
                f"{name} CRUD after failed syncs: addNote -> {nid}, findNotes -> {nids} (collection not wedged)",
            )
        except AssertionError as e:
            check("SY-11", False, f"{name} CRUD after failed syncs failed: {e}")


# ---------------------------------------------------------------- SY-12 collection_generation
# Spec: SY-12 — collection_generation (exploratory) after SY-03's sync, A's collection was reopened
#       internally — verify A still serves reads/writes normally (already covered by SY-11 but do an
#       explicit addNote on A post-sync and confirm it syncs in a later sync).


def sy12_collection_generation() -> None:
    try:
        nid = A.add_note("SyncDeck", "sync-F3", "sync-F3-back")
        check(
            "SY-12",
            isinstance(nid, int),
            f"A addNote post-sync works (collection reopened by the sync wrapper): id={nid}",
        )
    except AssertionError as e:
        check("SY-12", False, f"A addNote post-sync failed: {e}")
        return
    status, err, res = call(A, "sync")
    if err is None and isinstance(res, dict):
        coll = res.get("collection") or {}
        check(
            "SY-12",
            coll.get("outcome") in ("merged", "no_changes"),
            f"post-addNote sync -> {show('sync', {}, status, res)}",
        )
    else:
        record("SY-12", f"post-addNote sync attempt: HTTP {status}, error={err!r}")
        check("SY-12", False, f"post-addNote sync failed: HTTP {status}, error={err!r}")
    try:
        nids = A.ok("findNotes", {"query": 'Front:"sync-F3"'})
        check(
            "SY-12",
            len(nids) == 1,
            f"A findNotes after post-sync addNote: {nids} (A still serves reads/writes)",
        )
    except AssertionError as e:
        check("SY-12", False, f"A findNotes after post-sync addNote failed: {e}")


# ---------------------------------------------------------------- SY-99 final sweep


def sy99_final_health() -> None:
    for name, cl in (("A", A), ("B", B), ("C", C)):
        status, _txt = cl.get("/health")
        record("SY-99", f"{name} final /health: {status}")


# ---------------------------------------------------------------- runner


def main() -> int:
    for name, cl in (("A", A), ("B", B), ("C", C)):
        if not cl.wait_healthy():
            print(f"FATAL: {name} at {cl.base_url} is not healthy; aborting")
            return 2
    cases = [
        sy00_preflight,
        sy01_sync_status_happy,
        sy02_first_sync,
        sy03_sync_after_changes,
        sy04_roundtrip,
        sy05_two_way,
        sy06_sync_media,
        sy07_wrong_credentials,
        sy08_unreachable_endpoint,
        sy09_no_credentials,
        sy10_concurrent_lock,
        sy11_resilience,
        sy12_collection_generation,
        sy99_final_health,
    ]
    for fn in cases:
        case_id = f"SY-{fn.__name__[2:4]}"
        print(f"\n--- {case_id} {fn.__name__} ---")
        try:
            fn()
        except Exception as e:  # the suite must survive anything
            check(case_id, False, f"case crashed with {type(e).__name__}: {e}")
    return summary()


if __name__ == "__main__":
    sys.exit(main())
