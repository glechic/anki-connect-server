#!/usr/bin/env python3
"""E2E black-box suite — card scheduling actions (SC-01..SC-22).

Actions under test: answerCards, forgetCards, relearnCards, setEaseFactors,
setSpecificValueOfCard. Every case's criteria are inlined as a "# Spec:"
comment under its banner.

Fixture (built via the API): deck Sched; 6 Basic notes n1..n6
(Front "sched-F<i>"); findCards deck:Sched → card ids c1..c6. New Basic
cards in the default deck config have 2 learning steps (1m, 10m).

API-only: every setup step and assertion goes through HTTP (anki_client.Client);
the server package and the collection DB are never imported or read.

Run from the repo root:
    python3 e2e/suite_scheduling.py http://localhost:18761
"""

from __future__ import annotations

import sys

from anki_client import Client, check, die, record, summary

MISSING = 999_999_999_999  # card id that cannot exist


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:18761"
    c = Client(base)
    if not c.wait_healthy():
        die("server never became healthy")

    # ----------------------------------------------------------- helpers

    def call(action: str, params: dict, version: int = 6, path: str = "/api"):
        """Raw request + a compact request/response evidence string."""
        st, body = c.request(action, params, version, path)
        return st, body, f"[{st}] {action}({params!r}) v{version} on {path} -> {body!r}"

    def find(query: str) -> list:
        return c.ok("findCards", {"query": query})

    def state(cid: int) -> str:
        """Card state via Anki search (cardsInfo has no queue/type at this commit).

        is:new    -> type == 0 (new)
        is:learn  -> queue in (1, 3)   (learning or relearning queue)
        is:review -> type in (2, 3)   (graduated card: review or relearning)
        so: new / learn(type=1) / review(type=2 or 3, queue not lrn) /
        relearn(type=3 with lrn queue).
        """
        is_new = bool(find(f"cid:{cid} is:new"))
        is_learn = bool(find(f"cid:{cid} is:learn"))
        is_review = bool(find(f"cid:{cid} is:review"))
        if is_new:
            return "new"
        if is_learn and is_review:
            return "relearn"
        if is_learn:
            return "learn"
        if is_review:
            return "review"
        return "other"

    def ivl_factor(cid: int) -> tuple[int, int]:
        """(interval, ease-factor) via cardsInfo ('interval' and 'ease' keys)."""
        infos = c.ok("cardsInfo", {"cards": [cid]})
        if not infos:
            return -1, -1
        return int(infos[0]["interval"]), int(infos[0]["ease"])

    def healthy() -> bool:
        st, _ = c.get("/health")
        return st == 200

    def env(body: object, result: object) -> bool:
        """v6 envelope with an exact result and error null."""
        return isinstance(body, dict) and body.get("result") == result and body.get("error") is None

    def err_env(body: object, contains: str) -> bool:
        """v6 error envelope: HTTP 200 handled by caller, result null, message."""
        return (
            isinstance(body, dict)
            and body.get("result") is None
            and isinstance(body.get("error"), str)
            and contains in body["error"]
        )

    # ----------------------------------------------------- C1/C2 baseline

    st, body = c.request("version")
    check("C1/C2", st == 200 and env(body, 6), f"[{st}] POST /api version -> {body!r}")

    # ------------------------------------------------------------- fixture

    # Expected v3-scheduler outcomes after answering a NEW card (used by SC-01):
    #   ease 1 (Again) -> queue=1 (learning), type=1, left stays, card repeats step 1
    #   ease 2 (Hard)  -> queue=1, type=1 (still learning)
    #   ease 3 (Good)  -> queue=1, type=1 (first Good -> step 2 of 2 not yet passed)
    #   ease 4 (Easy)  -> queue=2 (review), type=2, ivl=4d (default easy graduate),
    #                     factor raised
    # Verify with cardsInfo; if actual differs, record actual values as OBS and
    # FAIL only if the card did not leave the new state (queue=0/type=0).
    c.ok("createDeck", {"deck": "Sched"})
    for i in range(1, 7):
        c.add_note("Sched", f"sched-F{i}", f"sched-B{i}")
    cids = sorted(c.ok("findCards", {"query": "deck:Sched"}))
    check("FIXTURE", len(cids) == 6, f"findCards deck:Sched -> {cids!r}")
    front2cid: dict[str, int] = {}
    for info in c.ok("cardsInfo", {"cards": cids}):
        front2cid[info["fields"]["Front"]["value"]] = int(info["cardId"])
    check(
        "FIXTURE",
        [front2cid.get(f"sched-F{i}") for i in range(1, 7)] == cids,
        f"cardsInfo Front->cid map: {front2cid!r}",
    )
    c1, c2, c3, c4, c5, c6 = cids
    check(
        "FIXTURE",
        all(state(cid) == "new" for cid in cids),
        f"all 6 cards start new: {[state(cid) for cid in cids]}",
    )

    # ============================================================== SC-01
    # Spec: SC-01 — happy answerCards [{cardId:c1, ease:1}, {cardId:c2, ease:2}, {cardId:c3, ease:3},
    #       {cardId:c4, ease:4}] → result == [true,true,true,true], error == null. Verify per-card state
    #       via cardsInfo (table above; at minimum: reps≥1 and not new).
    answers = [
        {"cardId": c1, "ease": 1},
        {"cardId": c2, "ease": 2},
        {"cardId": c3, "ease": 3},
        {"cardId": c4, "ease": 4},
    ]
    st, body, ev = call("answerCards", {"answers": answers})
    check("SC-01", st == 200 and env(body, [True, True, True, True]), ev)

    expected = {c1: "learn", c2: "learn", c3: "learn", c4: "review"}
    for cid, exp in expected.items():
        s = state(cid)
        reps = bool(find(f"cid:{cid} prop:reps>=1"))
        check("SC-01", s == exp and reps, f"card {cid}: state={s} (want {exp}), reps>=1: {reps}")
    # P3-1 fixed contract: cardsInfo now exposes the full scheduling shape,
    # so assert it directly instead of inferring everything from search.
    info = {e["cardId"]: e for e in c.cards_info([c1, c2, c3, c4])}
    for cid, ease in ((c1, 1), (c2, 2), (c3, 3), (c4, 4)):
        e = info.get(cid, {})
        check(
            "SC-01",
            isinstance(e.get("factor"), int) and e.get("factor") == e.get("ease"),
            f"card {cid}: factor==ease alias broken; entry keys={sorted(e)}",
        )
        check(
            "SC-01",
            e.get("reps", 0) >= 1 and (e.get("type"), e.get("queue")) != (0, 0),
            f"card {cid} (ease={ease}) left new state: type={e.get('type')} queue={e.get('queue')} reps={e.get('reps')}",
        )
        record(
            "SC-01",
            f"card {cid} cardsInfo: type={e.get('type')} queue={e.get('queue')} "
            f"due={e.get('due')} reps={e.get('reps')} lapses={e.get('lapses')} "
            f"left={e.get('left')} mod={e.get('mod')} factor={e.get('factor')}",
        )
    e4 = info.get(c4, {})
    check(
        "SC-01",
        e4.get("type") == 2 and e4.get("queue") == 2 and e4.get("interval", 0) >= 3,
        f"c4 (Easy) must graduate to review: type={e4.get('type')} queue={e4.get('queue')} ivl={e4.get('interval')}",
    )
    # Spec table detail: record actual scheduling values.
    for cid, ease in ((c1, 1), (c2, 2), (c3, 3), (c4, 4)):
        iv, fac = ivl_factor(cid)
        record(
            "SC-01", f"card {cid} after ease={ease}: state={state(cid)} interval={iv} factor={fac}"
        )
    iv4, fac4 = ivl_factor(c4)
    record(
        "SC-01",
        f"c4 (Easy) ivl={iv4} (spec table: 4d — v3 fuzz may give 3..5), factor={fac4} "
        f"(spec: raised; 0 before answering)",
    )

    # ============================================================== SC-02
    # Spec: SC-02 — missing card [{cardId:999999999999, ease:3}] → [false], error null. NOT an error
    #       envelope (per-card false; upstream parity).
    st, body, ev = call("answerCards", {"answers": [{"cardId": MISSING, "ease": 3}]})
    check("SC-02", st == 200 and env(body, [False]), f"per-card false, NOT an error envelope: {ev}")

    # ============================================================== SC-03
    # Spec: SC-03 — invalid ease values ease=5, ease=0, ease=-1, ease=2.5, ease="three" → each: HTTP 200,
    #       result: null, error mentions validation (Literal[1, 2, 3, 4] / "Input should be"). Nothing
    #       applied.
    for bad in (5, 0, -1, 2.5, "three"):
        st, body, ev = call("answerCards", {"answers": [{"cardId": c5, "ease": bad}]})
        ok = (
            st == 200
            and isinstance(body, dict)
            and err_env(body, "Input should be")  # pydantic Literal[1, 2, 3, 4]
            and (body["error"].count("1") > 0 or "Literal" in body["error"])
        )
        check("SC-03", ok, f"ease={bad!r} rejected: {ev}")
    s5, reps5 = state(c5), bool(find(f"cid:{c5} prop:reps>=1"))
    check("SC-03", s5 == "new" and not reps5, f"nothing applied: c5 state={s5}, reps>=1: {reps5}")
    check("SC-03/C5", healthy(), "health 200 after validation failures")

    # ============================================================== SC-04
    # Spec: SC-04 — all-or-nothing divergence (documented) [{cardId:c5, ease:3}, {cardId:999999999999,
    #       ease:5}] — invalid entry makes the WHOLE request fail validation; verify error present AND c5
    #       was NOT answered (reps unchanged). This intentionally diverges from upstream (upstream applies
    #       earlier answers then errors) — record as OBS confirming the divergence.
    st, body, ev = call(
        "answerCards",
        {"answers": [{"cardId": c5, "ease": 3}, {"cardId": MISSING, "ease": 5}]},
    )
    check("SC-04", st == 200 and err_env(body, "Input should be"), f"whole request rejected: {ev}")
    s5, reps5 = state(c5), bool(find(f"cid:{c5} prop:reps>=1"))
    check("SC-04", s5 == "new" and not reps5, f"c5 NOT answered: state={s5}, reps>=1: {reps5}")
    record(
        "SC-04",
        "divergence from upstream confirmed: the invalid entry (ease=5) rejects the entire "
        "request before any card is answered; upstream answers earlier entries then errors",
    )
    check("SC-04/C5", healthy(), "health 200 after failed request")

    # ============================================================== SC-05
    # Spec: SC-05 — empty answers {"answers": []} → result == [].
    st, body, ev = call("answerCards", {"answers": []})
    check("SC-05", st == 200 and env(body, []), ev)

    # ============================================================== SC-06
    # Spec: SC-06 — missing/extra params no answers key → [] (default) or validation error — record which;
    #       answers: [{cardId: c1, ease: 3, bogus: 1}] → error envelope (extra=forbid); answers: [{ease:
    #       3}] → error envelope.
    st, body, ev = call("answerCards", {})
    if st == 200 and env(body, []):
        record("SC-06", f"missing 'answers' key -> default [] (no validation error): {ev}")
    elif st == 200 and err_env(body, ""):
        record("SC-06", f"missing 'answers' key -> validation error envelope: {ev}")
    else:
        check("SC-06", False, f"missing 'answers' key: unexpected response: {ev}")

    st, body, ev = call("answerCards", {"answers": [{"cardId": c1, "ease": 3, "bogus": 1}]})
    ok = st == 200 and err_env(body, "") and ("Extra" in body["error"] or "extra" in body["error"])
    check("SC-06", ok, f"extra key 'bogus' -> error envelope: {ev}")
    check("SC-06", state(c1) == "learn", f"c1 unchanged after refused answer: state={state(c1)}")

    st, body, ev = call("answerCards", {"answers": [{"ease": 3}]})
    ok = (
        st == 200
        and err_env(body, "cardId")
        and ("Field required" in body["error"] or "required" in body["error"])
    )
    check("SC-06", ok, f"missing cardId -> error envelope: {ev}")
    check("SC-06/C5", healthy(), "health 200 after validation failures")

    # ============================================================== SC-07
    # Spec: SC-07 — forgetCards happy forget c1 (currently learning after SC-01) → result null; cardsInfo:
    #       queue=0, type=0, ivl=0, due=0, factor=0 (hard reset to new, raw-SQL parity). Verify
    #       getEaseFactors [c1] == [0].
    s_before = state(c1)
    st, body, ev = call("forgetCards", {"cards": [c1]})
    check("SC-07", st == 200 and env(body, None), f"forget c1 (was {s_before}): {ev}")
    s1 = state(c1)
    iv1, fac1 = ivl_factor(c1)
    check(
        "SC-07",
        s1 == "new" and iv1 == 0 and fac1 == 0,
        f"c1 after forget: state={s1} (queue=0/type=0), interval={iv1}, factor={fac1} (spec: 0/0/0/0)",
    )
    st, body, ev = call("getEaseFactors", {"cards": [c1]})
    record(
        "SC-07",
        f"spec asks to verify factor via getEaseFactors; not implemented at this commit "
        f"(later commit) -> {ev}; factor==0 confirmed via cardsInfo.ease instead",
    )

    # ============================================================== SC-08
    # Spec: SC-08 — forgetCards missing id [999999999999] → result null (silent no-op), no error.
    st, body, ev = call("forgetCards", {"cards": [MISSING]})
    check("SC-08", st == 200 and env(body, None), f"missing id: silent no-op (result null): {ev}")

    # ============================================================== SC-09
    # Spec: SC-09 — relearnCards happy c4 (review after SC-01) → relearnCards [c4] → null; cardsInfo:
    #       type=3 (relearning), queue=1 (lrn). Record whether getDeckStats now shows learn_count≥1 for
    #       Sched (OBS).
    s_before = state(c4)
    st, body, ev = call("relearnCards", {"cards": [c4]})
    check("SC-09", st == 200 and env(body, None), f"relearn c4 (was {s_before}): {ev}")
    s4 = state(c4)
    check(
        "SC-09",
        s4 == "relearn",
        f"c4 state={s4} (is:learn + is:review => type=3 relearning in lrn queue; "
        f"queue 1 vs 3 not distinguishable via search)",
    )
    st, body, ev = call("getDeckStats", {"decks": ["Sched"]})
    record(
        "SC-09",
        f"spec asks to record getDeckStats learn_count; not implemented at this commit -> {ev}",
    )

    # ============================================================== SC-10
    # Spec: SC-10 — relearnCards missing id → null, silent no-op.
    st, body, ev = call("relearnCards", {"cards": [MISSING]})
    check("SC-10", st == 200 and env(body, None), f"missing id: silent no-op (result null): {ev}")

    # ============================================================== SC-11
    # Spec: SC-11 — setEaseFactors happy [c2], factors [2000] → [true]; getEaseFactors [c2] == [2000].
    st, body, ev = call("setEaseFactors", {"cards": [c2], "easeFactors": [2000]})
    check("SC-11", st == 200 and env(body, [True]), ev)
    _, fac = ivl_factor(c2)
    check(
        "SC-11",
        fac == 2000,
        f"c2 factor={fac} (spec: 2000; verified via cardsInfo.ease — getEaseFactors not available)",
    )

    # ============================================================== SC-12
    # Spec: SC-12 — setEaseFactors length mismatch cards [c2], factors [1,2] → error envelope containing
    #       "cards and easeFactors must be the same length"; factor unchanged (getEaseFactors still 2000).
    st, body, ev = call("setEaseFactors", {"cards": [c2], "easeFactors": [1, 2]})
    ok = st == 200 and err_env(body, "cards and easeFactors must be the same length")
    check("SC-12", ok, f"length mismatch -> error envelope: {ev}")
    _, fac = ivl_factor(c2)
    check("SC-12", fac == 2000, f"c2 factor unchanged: {fac}")
    check("SC-12/C5", healthy(), "health 200 after failed request")

    # ============================================================== SC-13
    # Spec: SC-13 — setEaseFactors missing card [c2, 999999999999], factors [2100, 2200] → [true, false];
    #       c2 == 2100 after.
    st, body, ev = call("setEaseFactors", {"cards": [c2, MISSING], "easeFactors": [2100, 2200]})
    check("SC-13", st == 200 and env(body, [True, False]), ev)
    _, fac = ivl_factor(c2)
    check("SC-13", fac == 2100, f"c2 factor={fac} (spec: 2100)")

    # ============================================================== SC-14
    # Spec: SC-14 — setSpecificValueOfCard happy card=c5, keys=["flags"], newValues=[3],
    #       warning_check=false → result == [true]; cardsInfo flags == 3.
    before = find(f"cid:{c5} flag:3")
    st, body, ev = call(
        "setSpecificValueOfCard",
        {"card": c5, "keys": ["flags"], "newValues": [3], "warning_check": False},
    )
    check("SC-14", st == 200 and env(body, [True]), f"flags=3 (flag:3 before: {before!r}): {ev}")
    after = find(f"cid:{c5} flag:3")
    check(
        "SC-14",
        not before and after == [c5],
        f"flag:3 search before={before!r} after={after!r} (cardsInfo has no flags field at this commit)",
    )

    # ============================================================== SC-15
    # Spec: SC-15 — blocked key refused keys=["queue"], newValues=[1], warning_check=false → result ==
    #       false (bare boolean, upstream shape), state unchanged.
    s_before = state(c6)
    st, body, ev = call(
        "setSpecificValueOfCard",
        {"card": c6, "keys": ["queue"], "newValues": [1], "warning_check": False},
    )
    check(
        "SC-15",
        st == 200 and env(body, False),
        f"blocked key without warning_check -> bare false: {ev}",
    )
    s_after = state(c6)
    check(
        "SC-15",
        s_before == "new" and s_after == "new",
        f"c6 state unchanged ({s_before} -> {s_after}); queue=1 would have shown is:learn",
    )

    # ============================================================== SC-16
    # Spec: SC-16 — blocked key with warning_check=true keys=["reps"], newValues=[42], warning_check=true
    #       → [true]; cardsInfo reps == 42.
    st, body, ev = call(
        "setSpecificValueOfCard",
        {"card": c6, "keys": ["reps"], "newValues": [42], "warning_check": True},
    )
    check(
        "SC-16",
        st == 200 and env(body, [True]),
        f"blocked key with warning_check=true -> [true]: {ev}",
    )
    lo = find(f"cid:{c6} prop:reps>=42")
    hi = find(f"cid:{c6} prop:reps>=43")
    check(
        "SC-16",
        lo == [c6] and hi == [],
        f"reps==42 via search (>=42: {lo!r}, >=43: {hi!r}) — cardsInfo has no reps field at this commit",
    )

    # ============================================================== SC-17
    # Spec: SC-17 — keys/newValues mismatch keys=["flags","reps"], newValues=[1] → result == false;
    #       nothing changed.
    st, body, ev = call(
        "setSpecificValueOfCard",
        {"card": c5, "keys": ["flags", "reps"], "newValues": [1], "warning_check": False},
    )
    check("SC-17", st == 200 and env(body, False), f"mismatched lengths -> bare false: {ev}")
    flag_after = find(f"cid:{c5} flag:3")
    reps_after = bool(find(f"cid:{c5} prop:reps>=1"))
    check(
        "SC-17",
        flag_after == [c5] and not reps_after,
        f"nothing changed: c5 flag:3={flag_after!r}, reps>=1: {reps_after}",
    )
    st, body, ev = call(
        "setSpecificValueOfCard",
        {"card": c5, "keys": ["flags"], "newValues": [1, 2], "warning_check": False},
    )
    record(
        "SC-17",
        f"pure length-mismatch path (unblocked key flags, 1 key vs 2 values): {ev} (expected bare false)",
    )

    # ============================================================== SC-18
    # Spec: SC-18 — missing card card=999999999999, keys=["flags"], newValues=[1] → result == [[false,
    #       "<some error string>"]] — NESTED list shape (upstream parity); error message mentions not
    #       found.
    st, body, ev = call(
        "setSpecificValueOfCard",
        {"card": MISSING, "keys": ["flags"], "newValues": [1], "warning_check": False},
    )
    res = body.get("result") if isinstance(body, dict) else None
    shape_ok = (
        st == 200
        and isinstance(body, dict)
        and body.get("error") is None
        and isinstance(res, list)
        and len(res) == 1
        and isinstance(res[0], list)
        and len(res[0]) == 2
        and res[0][0] is False
        and isinstance(res[0][1], str)
    )
    msg_ok = shape_ok and ("not found" in res[0][1].lower() or "no such card" in res[0][1].lower())
    check(
        "SC-18",
        shape_ok and msg_ok,
        f"missing card -> nested [[False, msg]] mentioning the missing card: {ev}",
    )
    if shape_ok:
        record(
            "SC-18",
            f"exact message: {res[0][1]!r} — anki's own NotFoundError text (fluent template "
            f"'errors_inconsistent_db_state' + 'No such card: <id>'); upstream AnkiConnect "
            f"str(e) wrapping returns the same string",
        )

    # ============================================================== SC-19
    # Spec: SC-19 — invalid value type (exploratory) keys=["flags"], newValues=["not-an-int"] → record
    #       status + body (shape [[false, msg]] expected; 500 = ISSUE).
    st, body, ev = call(
        "setSpecificValueOfCard",
        {"card": c6, "keys": ["flags"], "newValues": ["not-an-int"], "warning_check": False},
    )
    check("SC-19", st == 200, f"must NOT be a HTTP 500: {ev}")
    record("SC-19", f"invalid value type for flags -> {ev} (expected shape [[False, msg]])")

    # ============================================================== SC-20
    # Spec: SC-20 — wire name param must be warning_check (snake case, upstream). Sending warningCheck →
    #       error envelope (extra=forbid). Record.
    st, body, ev = call(
        "setSpecificValueOfCard",
        {"card": c1, "keys": ["flags"], "newValues": [0], "warningCheck": True},
    )
    ok = (
        st == 200
        and err_env(body, "")
        and (
            "warningCheck" in body["error"] or "Extra" in body["error"] or "extra" in body["error"]
        )
    )
    check("SC-20", ok, f"camelCase 'warningCheck' must be refused (extra=forbid): {ev}")
    record(
        "SC-20", "snake_case warning_check is the accepted wire name (SC-14/SC-16 show it accepted)"
    )
    check("SC-20/C5", healthy(), "health 200 after validation failure")

    # ============================================================== SC-21
    # Spec: SC-21 — envelope/legacy answerCards with version=4 → bare [true,...] (no envelope); unknown
    #       action answerCardsss → error envelope "Unsupported action: answerCardsss"; same request on /
    #       path → identical behavior.
    st, body, ev = call("answerCards", {"answers": [{"cardId": c1, "ease": 3}]}, version=4)
    check("SC-21", st == 200 and body == [True], f"version=4 -> bare [true], no envelope: {ev}")

    st, body, ev = call("answerCardsss", {})
    ok = st == 200 and err_env(body, "Unsupported action: answerCardsss")
    check("SC-21", ok, f"unknown action -> error envelope: {ev}")

    st2, body2, ev2 = call("answerCardsss", {}, path="/")
    check(
        "SC-21",
        (st2, body2) == (st, body),
        f"same unknown-action request on / -> identical behavior: {ev2} vs {ev}",
    )

    st, body = c.raw_post({"action": "deckNames", "params": {}})
    check(
        "SC-21",
        st == 200 and isinstance(body, list) and "Sched" in body,
        f"missing version defaults to 4 -> bare result, no envelope: [{st}] {body!r}",
    )

    # ============================================================== SC-22
    # Spec: SC-22 — resilience GET /health == 200 after all failures; version action == 6; deckNames still
    #       lists Sched.
    st, text = c.get("/health")
    check("SC-22", st == 200, f"GET /health -> {st} {text!r}")
    st, body, ev = call("version", {})
    check("SC-22", st == 200 and env(body, 6), ev)
    decks = c.ok("deckNames")
    check("SC-22", "Sched" in decks, f"deckNames still lists Sched: {decks!r}")

    print()
    return summary()


if __name__ == "__main__":
    sys.exit(main())
