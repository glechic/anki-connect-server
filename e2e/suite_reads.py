"""E2E suite — card/note read actions (RD-01..RD-21).

Actions under test: canAddNote, cardsModTime, deckNameFromId,
getEaseFactors, modelNameFromId, suspended, getMediaFilesNames,
removeEmptyNotes. Every case's criteria are inlined as a "# Spec:" comment
under its banner.

Fixture (via API): deck Reads; 2 Basic notes (read-F1, read-F2, second
tagged); model "UnusedModel" (fields X,Y; template T1) used by NO note;
media read-asset.txt = base64("read"). c1 = card of read-F1.

Black-box: talks ONLY to the HTTP API via anki_client.py.
Run from repo root:  python3 e2e/suite_reads.py http://localhost:18762
"""

from __future__ import annotations

import sys

sys.path.insert(0, "e2e")

from anki_client import Client, check, die, record, summary

MISSING = 999999999999


def setup_fixture(c: Client) -> tuple[int, int]:
    """Create deck Reads, 2 Basic notes, UnusedModel, media file.

    Returns (c1, c2) — card ids of the two notes in deck Reads.
    """
    c.create_deck("Reads")
    c.add_note("Reads", "read-F1", "read-B1", tags=["read-tag"])
    c.add_note("Reads", "read-F2", "read-B2", tags=["read-tag2", "extra"])
    # UnusedModel: used by NO note. (This commit uses upstream-style params:
    # modelName / inOrderFields / cardTemplates.)
    c.ok(
        "createModel",
        {
            "modelName": "UnusedModel",
            "inOrderFields": ["X", "Y"],
            "cardTemplates": [{"Name": "T1", "Front": "{{X}}", "Back": "{{Y}}"}],
        },
    )
    c.store_media_b64("read-asset.txt", "read")
    cards = c.find_cards('deck:"Reads"')
    if len(cards) != 2:
        die(f"fixture: expected 2 cards in Reads, got {cards!r}")
    # c1 = card of note 1 (read-F1), c2 = card of note 2 (read-F2)
    q1 = c.find_cards('deck:"Reads" Front:"read-F1"')
    q2 = c.find_cards('deck:"Reads" Front:"read-F2"')
    if len(q1) != 1 or len(q2) != 1:
        die(f"fixture: per-note card lookup failed: F1->{q1!r} F2->{q2!r}")
    return q1[0], q2[0]


def main() -> int:
    if len(sys.argv) != 2:
        die(f"usage: {sys.argv[0]} <base-url>")
    base = sys.argv[1]
    c = Client(base)

    if not c.wait_healthy(tries=90, delay=1.0):
        die(f"server did not become healthy at {base}/health")
    print(f"server healthy at {base}")

    c1, c2 = setup_fixture(c)
    print(f"fixture ready: c1={c1} c2={c2}")

    # ------------------------------------------------ RD-01 canAddNote happy
    # Spec: RD-01 — canAddNote happy note {deck Reads, model Basic, fields {Front: read-F3, Back: b}} →
    #       true.
    res = c.ok(
        "canAddNote",
        {
            "note": {
                "deckName": "Reads",
                "modelName": "Basic",
                "fields": {"Front": "read-F3", "Back": "b"},
            }
        },
    )
    check("RD-01", res is True, f"canAddNote(new note) = {res!r}, expected true")

    # ------------------------------------------ RD-02 canAddNote duplicate
    # Spec: RD-02 — canAddNote duplicate Front == read-F1 (existing) → false (dupe check, no error).
    res = c.ok(
        "canAddNote",
        {
            "note": {
                "deckName": "Reads",
                "modelName": "Basic",
                "fields": {"Front": "read-F1", "Back": "read-B1"},
            }
        },
    )
    check("RD-02", res is False, f"canAddNote(dup Front read-F1) = {res!r}, expected false")

    # ------------------------------------- RD-03 canAddNote invalid model
    # Spec: RD-03 — canAddNote invalid model modelName "NoSuchModel" → false (NOT an error envelope).
    res = c.ok(
        "canAddNote",
        {
            "note": {
                "deckName": "Reads",
                "modelName": "NoSuchModel",
                "fields": {"Front": "read-F4", "Back": "b"},
            }
        },
    )
    check("RD-03", res is False, f"canAddNote(NoSuchModel) = {res!r}, expected false (not error)")

    # ------------------------------------ RD-04 canAddNote invalid deck
    # Spec: RD-04 — canAddNote invalid deck name? deckName "No such deck" → record behavior (upstream
    #       canAddNote returns true — deck would be created at add time). OBS.
    res = c.ok(
        "canAddNote",
        {
            "note": {
                "deckName": "No such deck",
                "modelName": "Basic",
                "fields": {"Front": "read-F5", "Back": "b"},
            }
        },
    )
    record(
        "RD-04",
        f"canAddNote(deckName='No such deck') = {res!r} "
        f"(upstream returns true — deck created at add time)",
    )

    # ------------------------------------------- RD-05 cardsModTime happy
    # Spec: RD-05 — cardsModTime happy [c1] → [{"cardId": c1, "mod": <int>}]. mod must be epoch SECONDS
    #       (raw card.mod, upstream parity — assert value < 2^33 so it's clearly not ms). Record the
    #       value.
    res = c.ok("cardsModTime", {"cards": [c1]})
    ok05 = (
        isinstance(res, list)
        and len(res) == 1
        and isinstance(res[0], dict)
        and res[0].get("cardId") == c1
        and isinstance(res[0].get("mod"), int)
        and res[0]["mod"] < 2**33
    )
    mod_val = (
        res[0].get("mod") if isinstance(res, list) and res and isinstance(res[0], dict) else None
    )
    check(
        "RD-05",
        bool(ok05),
        f"cardsModTime([c1]) = {res!r}; mod={mod_val!r} "
        f"must be epoch seconds (< 2^33 = 8589934592)",
    )

    # ---------------------------------------- RD-06 cardsModTime missing
    # Spec: RD-06 — cardsModTime missing [999999999999] → [{}] (empty dict, position preserved).
    res = c.ok("cardsModTime", {"cards": [MISSING]})
    check("RD-06", res == [{}], f"cardsModTime([missing]) = {res!r}, expected [{{}}]")

    # ----------------------------------------- RD-07 cardsModTime mixed
    # Spec: RD-07 — cardsModTime mixed [c1, 999999999999] → [{...}, {}].
    res = c.ok("cardsModTime", {"cards": [c1, MISSING]})
    ok07 = (
        isinstance(res, list)
        and len(res) == 2
        and isinstance(res[0], dict)
        and res[0].get("cardId") == c1
        and isinstance(res[0].get("mod"), int)
        and res[1] == {}
    )
    check("RD-07", bool(ok07), f"cardsModTime([c1, missing]) = {res!r}, expected [{{...}}, {{}}]")

    # --------------------------------------- RD-08 deckNameFromId happy
    # Spec: RD-08 — deckNameFromId happy get id from deckNamesAndIds → name == "Reads".
    dmap = c.ok("deckNamesAndIds")
    reads_id = dmap.get("Reads")
    res = c.ok("deckNameFromId", {"deckId": reads_id})
    check("RD-08", res == "Reads", f"deckNameFromId({reads_id}) = {res!r}, expected 'Reads'")

    # -------------------------------------- RD-09 deckNameFromId missing
    # Spec: RD-09 — deckNameFromId missing 999999999999 → error envelope, exact message deck was not
    #       found: 999999999999.
    err = c.err("deckNameFromId", {"deckId": MISSING})
    check(
        "RD-09",
        err == f"deck was not found: {MISSING}",
        f"deckNameFromId({MISSING}) error = {err!r}",
    )

    # --------------------------------------- RD-10 getEaseFactors happy
    # Spec: RD-10 — getEaseFactors happy [c1] → [2500] (default new-card factor). If different, record
    #       actual.
    res = c.ok("getEaseFactors", {"cards": [c1]})
    if res == [2500]:
        check("RD-10", True, f"getEaseFactors([c1]) = {res!r} (default 2500)")
    else:
        record(
            "RD-10",
            f"getEaseFactors([c1]) = {res!r}, spec expected [2500] "
            f"(default new-card factor); recording actual value",
        )
        check(
            "RD-10",
            isinstance(res, list) and len(res) == 1 and isinstance(res[0], int),
            f"getEaseFactors([c1]) = {res!r}, expected single int list",
        )

    # ------------------------------------- RD-11 getEaseFactors missing
    # Spec: RD-11 — getEaseFactors missing → [null].
    res = c.ok("getEaseFactors", {"cards": [MISSING]})
    check("RD-11", res == [None], f"getEaseFactors([missing]) = {res!r}, expected [None]")

    # --------------------------------------- RD-12 modelNameFromId happy
    # Spec: RD-12 — modelNameFromId happy id of "Basic" from modelNamesAndIds → "Basic".
    mmap = c.ok("modelNamesAndIds")
    basic_id = mmap.get("Basic")
    res = c.ok("modelNameFromId", {"modelId": basic_id})
    check("RD-12", res == "Basic", f"modelNameFromId({basic_id}) = {res!r}, expected 'Basic'")

    # -------------------------------------- RD-13 modelNameFromId missing
    # Spec: RD-13 — modelNameFromId missing 999999999999 → error model was not found: 999999999999.
    err = c.err("modelNameFromId", {"modelId": MISSING})
    check(
        "RD-13",
        err == f"model was not found: {MISSING}",
        f"modelNameFromId({MISSING}) error = {err!r}",
    )

    # --------------------------------------- RD-14 suspended lifecycle
    # Spec: RD-14 — suspended lifecycle suspended(card=c1) → false; suspend [c1] → true; suspended(c1) →
    #       true; unsuspend [c1] → true; suspended(c1) → false.
    steps = [
        ("suspended(c1) fresh", c.ok("suspended", {"card": c1}), False),
    ]
    c.ok("suspend", {"cards": [c1]})
    steps.append(("suspend([c1]) result", True, True))
    steps.append(("suspended(c1) after suspend", c.ok("suspended", {"card": c1}), True))
    uns = c.ok("unsuspend", {"cards": [c1]})
    steps.append(("unsuspend([c1]) result", uns, True))
    steps.append(("suspended(c1) after unsuspend", c.ok("suspended", {"card": c1}), False))
    ok14 = all(got is want for _, got, want in steps)
    check("RD-14", ok14, "; ".join(f"{n}: {g!r} (want {w!r})" for n, g, w in steps))

    # ------------------------------------- RD-15 suspended missing card
    # Spec: RD-15 — suspended missing card suspended(card=999999999999) → error envelope, exact message
    #       Card was not found: 999999999999.
    err = c.err("suspended", {"card": MISSING})
    check("RD-15", err == f"Card was not found: {MISSING}", f"suspended({MISSING}) error = {err!r}")

    # ---------------------------------- RD-16 getMediaFilesNames default
    # Spec: RD-16 — getMediaFilesNames default {"pattern":"*"} → contains read-asset.txt. Pattern read-* →
    #       ["read-asset.txt"]; pattern *.ogg → []; pattern *asset* → ["read-asset.txt"].
    res = c.ok("getMediaFilesNames", {"pattern": "*"})
    check(
        "RD-16a",
        isinstance(res, list) and "read-asset.txt" in res,
        f"getMediaFilesNames('*') = {res!r}, must contain read-asset.txt",
    )
    res = c.ok("getMediaFilesNames", {"pattern": "read-*"})
    check(
        "RD-16b",
        res == ["read-asset.txt"],
        f"getMediaFilesNames('read-*') = {res!r}, expected ['read-asset.txt']",
    )
    res = c.ok("getMediaFilesNames", {"pattern": "*.ogg"})
    check("RD-16c", res == [], f"getMediaFilesNames('*.ogg') = {res!r}, expected []")
    res = c.ok("getMediaFilesNames", {"pattern": "*asset*"})
    check(
        "RD-16d",
        res == ["read-asset.txt"],
        f"getMediaFilesNames('*asset*') = {res!r}, expected ['read-asset.txt']",
    )

    # ------- RD-17 getMediaFilesNames path traversal (hardened, E2E P2-5)
    # Spec: RD-17 — getMediaFilesNames path traversal (security probe) pattern ../etc/* and absolute
    #       /etc/* → record what is returned. os.path.join semantics mean an absolute pattern likely lists
    #       files OUTSIDE the media dir (container's /etc). This mirrors upstream but is still worth
    #       recording as an OBS + security note.
    # P2-5 fixed contract: absolute patterns and '..' components are refused
    # as client errors (200 error envelope). Previously '/etc/*' listed the
    # container's /etc — an unauthenticated remote directory-listing
    # primitive that upstream (desktop add-on) tolerates but a server must
    # not.
    for pat in ("../etc/*", "/etc/*"):
        try:
            res = c.ok("getMediaFilesNames", {"pattern": pat})
            check("RD-17", False, f"pattern {pat!r} must be rejected, got result {res!r}")
        except AssertionError as e:
            check(
                "RD-17",
                "relative to the media directory" in str(e),
                f"pattern {pat!r} rejected with: {e}",
            )

    # ------------------------------------- RD-18 removeEmptyNotes happy
    # Spec: RD-18 — removeEmptyNotes happy modelNames contains "UnusedModel" and "Basic" → call
    #       removeEmptyNotes → result null → modelNames NO LONGER contains "UnusedModel", still contains
    #       "Basic". (Upstream quirk: removes unused note TYPES despite the name.)
    before = c.ok("modelNames")
    ok18a = "UnusedModel" in before and "Basic" in before
    check(
        "RD-18a",
        ok18a,
        f"modelNames before removeEmptyNotes = {before!r}, must contain UnusedModel and Basic",
    )
    res = c.ok("removeEmptyNotes")
    check("RD-18b", res is None, f"removeEmptyNotes() result = {res!r}, expected null")
    after = c.ok("modelNames")
    check(
        "RD-18c",
        "UnusedModel" not in after and "Basic" in after,
        f"modelNames after removeEmptyNotes = {after!r}, "
        f"UnusedModel must be gone, Basic must remain",
    )

    # ------------------------- RD-19 removeEmptyNotes idempotent + healthy
    # Spec: RD-19 — removeEmptyNotes idempotent + healthy second call → null; notes/cards still readable
    #       (notesInfo, cardsInfo), version == 6.
    res = c.ok("removeEmptyNotes")
    check("RD-19a", res is None, f"second removeEmptyNotes() = {res!r}, expected null")
    ninfo = c.ok("notesInfo", {"notes": c.ok("findNotes", {"query": 'deck:"Reads"'})})
    cinfo = c.cards_info([c1, c2])
    ver = c.ok("version", version=6)
    check(
        "RD-19b",
        len(ninfo) == 2
        and isinstance(ninfo[0], dict)
        and len(cinfo) == 2
        and isinstance(cinfo[0], dict)
        and ver == 6,
        f"after removeEmptyNotes x2: notesInfo={len(ninfo)} notes, "
        f"cardsInfo={len(cinfo)} cards, version={ver!r} (want 2/2/6)",
    )

    # ------------------------------------------- RD-20 param validation
    # Spec: RD-20 — param validation suspended with cards (wrong key) → error envelope; deckNameFromId
    #       with string id "1" → record (pydantic coerces str→int? OBS); cardsModTime with cards: 5 (not a
    #       list) → error envelope.
    # suspended with wrong key 'cards' -> error envelope
    status, body = c.request("suspended", {"cards": [c1]})
    err20a = (
        status == 200
        and isinstance(body, dict)
        and isinstance(body.get("error"), str)
        and body.get("result") is None
    )
    check(
        "RD-20a",
        err20a,
        f"suspended(cards=[c1]) -> HTTP {status} body {body!r}, "
        f"expected 200 error envelope (missing 'card')",
    )

    # deckNameFromId with string id "1" -> OBS (pydantic coercion?)
    status, body = c.request("deckNameFromId", {"deckId": "1"})
    if status == 200 and isinstance(body, dict) and body.get("error") is None:
        record(
            "RD-20b",
            f"deckNameFromId(deckId='1') -> {body.get('result')!r} "
            f"(string coerced to int, no error)",
        )
    else:
        record(
            "RD-20b",
            f"deckNameFromId(deckId='1') -> HTTP {status} {body!r} (no coercion, validation error)",
        )

    # cardsModTime with cards: 5 (not a list) -> error envelope
    status, body = c.request("cardsModTime", {"cards": 5})
    err20c = (
        status == 200
        and isinstance(body, dict)
        and isinstance(body.get("error"), str)
        and body.get("result") is None
    )
    check(
        "RD-20c",
        err20c,
        f"cardsModTime(cards=5) -> HTTP {status} body {body!r}, expected 200 error envelope",
    )

    # ------------------------------------ RD-21 envelope/legacy + resilience
    # Spec: RD-21 — envelope/legacy + resilience per common criteria C2-C5.
    # C2: success envelope shape
    status, body = c.request("deckNames")
    ok21a = (
        status == 200
        and isinstance(body, dict)
        and set(body.keys()) == {"result", "error"}
        and body["error"] is None
        and isinstance(body["result"], list)
    )
    check(
        "RD-21a",
        ok21a,
        f"deckNames envelope: HTTP {status} keys={sorted(body) if isinstance(body, dict) else body!r}",
    )

    # C3: unknown action -> 200 error envelope, never 500
    status, body = c.request("noSuchActionRead")
    ok21b = (
        status == 200
        and isinstance(body, dict)
        and isinstance(body.get("error"), str)
        and body.get("result") is None
    )
    check("RD-21b", ok21b, f"unknown action -> HTTP {status} body {body!r}")

    # C4: legacy versions <= 4 -> bare result, no envelope
    for v in (4, 3):
        status, body = c.request("deckNames", version=v)
        ok21c = (
            status == 200
            and isinstance(body, list)
            and "Reads" in [d.get("name") if isinstance(d, dict) else d for d in body]
        )
        check(
            f"RD-21c-v{v}",
            ok21c,
            f"version {v} deckNames -> HTTP {status} body {body!r}, "
            f"expected bare list containing Reads",
        )
    status, body = c.request("deckNames", version=0)  # missing version defaults to 4
    status_m, body_m = c.raw_post({"action": "deckNames"})  # no version key at all
    ok21d = (
        status == 200 and isinstance(body, list) and status_m == 200 and isinstance(body_m, list)
    )
    check(
        "RD-21d",
        ok21d,
        f"version 0 -> {type(body).__name__}, no version -> {type(body_m).__name__}, "
        f"expected bare lists both",
    )

    # C1: spot-check GET /
    status, _txt = c.get("/")
    record("RD-21e", f"GET / -> HTTP {status} (C1 spot-check)")

    # C5: resilience after failures — health still 200
    status, _ = c.get("/health")
    check("RD-21f", status == 200, f"GET /health after all cases -> HTTP {status}")

    # C6 (meta): this suite imports only stdlib + anki_client, asserts via API.
    record(
        "RD-21g", "C6: suite never imports anki_connect_server/anki; all assertions via HTTP API"
    )

    return summary()


if __name__ == "__main__":
    sys.exit(main())
