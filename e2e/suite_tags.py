#!/usr/bin/env python3
"""E2E black-box suite — tag actions (TG-01..TG-16).

Actions under test: replaceTags, replaceTagsInAllNotes, clearUnusedTags,
getNoteTags, updateNoteTags. Wire names for replace/update are snake_case
per upstream: tag_to_replace, replace_with_tag. updateNoteTags accepts
tags as list OR string. Every case's criteria are inlined as a "# Spec:"
comment under its banner.

Fixture (via API): deck Tags; notes: n1 "tags-F1" tags [alpha, keep];
n2 "tags-F2" tags [beta]; n3 "tags-F3" no tags; n4 "tags-F4"
tags [alpha, delta].

Run:  python3 e2e/suite_tags.py http://localhost:18763
"""

from __future__ import annotations

import sys
from typing import Any

from anki_client import Client, check, die, record, summary

MISSING = 999999999999

C = Client("http://localhost:18763")  # replaced in main()


def call(action: str, params: dict[str, Any] | None = None, version: int = 6) -> tuple[int, Any]:
    status, body = C.request(action, params, version)
    return status, body


def null_env(case: str, action: str, params: dict[str, Any] | None = None) -> bool:
    """Assert a success envelope with result null: {"result": null, "error": null}."""
    status, body = call(action, params)
    req = {"action": action, "params": params or {}}
    ok = status == 200 and body == {"result": None, "error": None}
    return check(case, ok, f"req={req!r} status={status} resp={body!r}")


def err_env(case: str, action: str, params: dict[str, Any] | None = None) -> str | None:
    """Assert the C3 error envelope: HTTP 200, {result: null, error: str}. Return the message."""
    status, body = call(action, params)
    req = {"action": action, "params": params or {}}
    ok = (
        status == 200
        and isinstance(body, dict)
        and isinstance(body.get("error"), str)
        and body.get("result") is None
    )
    if check(case, ok, f"req={req!r} status={status} resp={body!r}"):
        return body["error"]
    return None


def note_tags(case: str, nid: int) -> list[str] | None:
    """getNoteTags with envelope capture; returns None on envelope failure."""
    status, body = call("getNoteTags", {"note": nid})
    ok = (
        status == 200
        and isinstance(body, dict)
        and body.get("error") is None
        and isinstance(body.get("result"), list)
    )
    if not check(case, ok, f"req=getNoteTags note={nid} status={status} resp={body!r}"):
        return None
    return body["result"]


def healthy(case: str) -> None:
    status, text = C.get("/health")
    check(case, status == 200, f"GET /health status={status} body={text!r}")


def main() -> int:
    global C
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:18763"
    C = Client(base)
    if not C.wait_healthy(tries=30):
        die("server never became healthy")

    # ------------------------------------------------------------- C1 spot-check
    st_root, txt_root = C.get("/")
    record("TG-16", f"C1 GET / -> {st_root} {txt_root!r}")
    st, body = C.raw_post({"action": "version", "version": 6}, path="/")
    check(
        "TG-16",
        st == 200 and body == {"result": 6, "error": None},
        f"C1 POST / version -> {st} {body!r}",
    )

    # ------------------------------------------------------------------- fixture
    C.create_deck("Tags")
    n1 = C.add_note("Tags", "tags-F1", "tags-B1", ["alpha", "keep"])
    n2 = C.add_note("Tags", "tags-F2", "tags-B2", ["beta"])
    n3 = C.add_note("Tags", "tags-F3", "tags-B3")
    n4 = C.add_note("Tags", "tags-F4", "tags-B4", ["alpha", "delta"])
    record("FIX", f"note ids n1={n1} n2={n2} n3={n3} n4={n4}")

    # TG-01 replaceTags happy: alpha -> gamma on n1 only
    # Spec: TG-01 — replaceTags happy replaceTags {notes:[n1], tag_to_replace:"alpha",
    #       replace_with_tag:"gamma"} → result null; getNoteTags(n1) → tags contain "gamma" and "keep",
    #       NOT "alpha". Record exact list (order!).
    null_env(
        "TG-01",
        "replaceTags",
        {"notes": [n1], "tag_to_replace": "alpha", "replace_with_tag": "gamma"},
    )
    t1 = note_tags("TG-01", n1)
    if t1 is not None:
        check(
            "TG-01",
            "gamma" in t1 and "keep" in t1 and "alpha" not in t1,
            f"n1 tags={t1!r} (want gamma+keep, no alpha)",
        )
        record("TG-01", f"exact getNoteTags(n1)={t1!r}")

    # TG-02 replaceTags scope: n4 untouched
    # Spec: TG-02 — replaceTags scope after TG-01, n4 still has "alpha" (only listed notes touched).
    t4 = note_tags("TG-02", n4)
    if t4 is not None:
        check(
            "TG-02",
            "alpha" in t4 and "gamma" not in t4,
            f"n4 tags={t4!r} (want alpha kept, no gamma)",
        )

    # TG-03 replaceTags tag absent on note: no-op
    # Spec: TG-03 — replaceTags tag absent replaceTags {notes:[n2], tag_to_replace:"alpha",
    #       replace_with_tag:"x"} → null; n2 unchanged (has no "alpha").
    null_env(
        "TG-03", "replaceTags", {"notes": [n2], "tag_to_replace": "alpha", "replace_with_tag": "x"}
    )
    t2 = note_tags("TG-03", n2)
    if t2 is not None:
        check("TG-03", t2 == ["beta"], f"n2 tags={t2!r} (want ['beta'], no x/alpha)")

    # TG-04 replaceTags with a missing note id: silent skip, listed note still processed
    # Spec: TG-04 — replaceTags missing note id {notes:[n1, 999999999999], tag_to_replace:"gamma",
    #       replace_with_tag:"back"} → null (silent skip); n1 got the replacement.
    null_env(
        "TG-04",
        "replaceTags",
        {"notes": [n1, MISSING], "tag_to_replace": "gamma", "replace_with_tag": "back"},
    )
    t1 = note_tags("TG-04", n1)
    if t1 is not None:
        check(
            "TG-04",
            "back" in t1 and "gamma" not in t1 and "keep" in t1,
            f"n1 tags={t1!r} (want back+keep, no gamma)",
        )
        record("TG-04", f"exact getNoteTags(n1)={t1!r}")

    # TG-05 replaceTagsInAllNotes: alpha -> omega everywhere
    # Spec: TG-05 — replaceTagsInAllNotes happy {tag_to_replace:"alpha", replace_with_tag:"omega"} → null;
    #       BOTH n1 (currently gamma — no) and n4 (alpha) — verify n4 has "omega"; n3/n2 unaffected.
    #       Record all four notes' tags.
    null_env(
        "TG-05", "replaceTagsInAllNotes", {"tag_to_replace": "alpha", "replace_with_tag": "omega"}
    )
    t1 = note_tags("TG-05", n1)
    t2 = note_tags("TG-05", n2)
    t3 = note_tags("TG-05", n3)
    t4 = note_tags("TG-05", n4)
    if t4 is not None:
        check(
            "TG-05",
            "omega" in t4 and "alpha" not in t4 and "delta" in t4,
            f"n4 tags={t4!r} (want omega+delta, no alpha)",
        )
    if t1 is not None:
        check(
            "TG-05",
            "omega" not in t1 and "back" in t1,
            f"n1 tags={t1!r} (alpha absent on n1 -> untouched, no omega)",
        )
    if t2 is not None:
        check("TG-05", t2 == ["beta"], f"n2 tags={t2!r} (unaffected)")
    if t3 is not None:
        check("TG-05", t3 == [], f"n3 tags={t3!r} (unaffected)")
    record(
        "TG-05", f"all tags after replaceTagsInAllNotes: n1={t1!r} n2={t2!r} n3={t3!r} n4={t4!r}"
    )

    # TG-06 clearUnusedTags via dangling 'junk' tag
    # Spec: TG-06 — clearUnusedTags happy addTags {notes:[n3], tags:"junk"} → getTags contains "junk" →
    #       deleteNotes [n3] → getTags STILL contains "junk" (dangling) → clearUnusedTags → getTags no
    #       longer contains "junk"; tags still used by notes (e.g. "keep") remain.
    null_env("TG-06", "addTags", {"notes": [n3], "tags": "junk"})
    st, body = call("getTags")
    gt = body.get("result") if isinstance(body, dict) else None
    check(
        "TG-06",
        st == 200 and isinstance(gt, list) and "junk" in gt,
        f"req=getTags status={st} resp={body!r} (junk should be registered)",
    )
    null_env("TG-06", "deleteNotes", {"notes": [n3]})
    st, body = call("getTags")
    gt = body.get("result") if isinstance(body, dict) else None
    check(
        "TG-06",
        st == 200 and isinstance(gt, list) and "junk" in gt,
        f"req=getTags status={st} resp={body!r} (junk must dangle after deleteNotes)",
    )
    record("TG-06", f"getTags after deleteNotes (dangling)={gt!r}")
    null_env("TG-06", "clearUnusedTags", {})
    st, body = call("getTags")
    gt = body.get("result") if isinstance(body, dict) else None
    check(
        "TG-06",
        st == 200 and isinstance(gt, list) and "junk" not in gt,
        f"req=getTags status={st} resp={body!r} (junk cleared)",
    )
    check(
        "TG-06",
        isinstance(gt, list) and "keep" in gt,
        f"getTags={gt!r} (tags still in use, e.g. keep, must remain)",
    )
    record("TG-06", f"getTags after clearUnusedTags={gt!r}")

    # TG-07 getNoteTags happy
    # Spec: TG-07 — getNoteTags happy getNoteTags {note:n2} → ["beta"] exactly.
    t2 = note_tags("TG-07", n2)
    if t2 is not None:
        check("TG-07", t2 == ["beta"], f"n2 tags={t2!r} (want exactly ['beta'])")
        record("TG-07", f"exact getNoteTags(n2)={t2!r}")

    # TG-08 getNoteTags missing note -> exact error
    # Spec: TG-08 — getNoteTags missing {note:999999999999} → error envelope, exact message Note was not
    #       found: 999999999999.
    e = err_env("TG-08", "getNoteTags", {"note": MISSING})
    if e is not None:
        check("TG-08", e == "Note was not found: 999999999999", f"error={e!r}")
    healthy("TG-08")

    # TG-09 updateNoteTags list form replaces all previous tags
    # Spec: TG-09 — updateNoteTags list form {note:n1, tags:["x","y"]} → null; getNoteTags(n1) → ["x","y"]
    #       — ALL previous tags replaced.
    null_env("TG-09", "updateNoteTags", {"note": n1, "tags": ["x", "y"]})
    t1 = note_tags("TG-09", n1)
    if t1 is not None:
        check("TG-09", t1 == ["x", "y"], f"n1 tags={t1!r} (want ['x','y'], all previous gone)")
        record("TG-09", f"exact getNoteTags(n1)={t1!r}")

    # TG-10 updateNoteTags string form == single tag
    # Spec: TG-10 — updateNoteTags string form {note:n2, tags:"solo"} → null; getNoteTags(n2) == ["solo"]
    #       (string accepted as a single tag).
    null_env("TG-10", "updateNoteTags", {"note": n2, "tags": "solo"})
    t2 = note_tags("TG-10", n2)
    if t2 is not None:
        check("TG-10", t2 == ["solo"], f"n2 tags={t2!r} (want ['solo'])")
        record("TG-10", f"exact getNoteTags(n2)={t2!r}")

    # TG-11 updateNoteTags string with a space (exploratory)
    # Spec: TG-11 — updateNoteTags string with space (exploratory) {note:n2, tags:"one two"} → record
    #       resulting getNoteTags — implementation wraps the string as ONE tag literally "one two"; anki
    #       may reject/sanitize/store it. Record exact outcome + whether findNotes query:"tag:one" matches
    #       (OBS; potential ISSUE if a space-containing tag is stored raw).
    null_env("TG-11", "updateNoteTags", {"note": n2, "tags": "one two"})
    t2 = note_tags("TG-11", n2)
    record("TG-11", f'getNoteTags(n2) after tags="one two" -> {t2!r}')
    st, body = call("findNotes", {"query": "tag:one"})
    rec = body.get("result") if isinstance(body, dict) else None
    record("TG-11", f"findNotes tag:one -> {rec!r} (n2={n2}) status={st}")
    st, body = call("findNotes", {"query": "tag:two"})
    rec = body.get("result") if isinstance(body, dict) else None
    record("TG-11", f"findNotes tag:two -> {rec!r} (n2={n2}) status={st}")
    st, body = call("findNotes", {"query": "tag:one two"})
    rec = body.get("result") if isinstance(body, dict) else None
    record("TG-11", f'findNotes "tag:one two" -> {rec!r} (n2={n2}) status={st}')
    if t2 is not None:
        record(
            "TG-11",
            f"space-in-tag stored raw: {t2 == ['one two']!r} "
            f"(potential ISSUE if True; anki split/sanitize if False)",
        )

    # TG-12 updateNoteTags empty list clears tags
    # Spec: TG-12 — updateNoteTags empty list {note:n2, tags:[]} → null; getNoteTags(n2) == [] (tags
    #       cleared).
    null_env("TG-12", "updateNoteTags", {"note": n2, "tags": []})
    t2 = note_tags("TG-12", n2)
    if t2 is not None:
        check("TG-12", t2 == [], f"n2 tags={t2!r} (want [])")

    # TG-13 updateNoteTags missing note -> error. P3-2 fixed contract: the
    # Spec: TG-13 — updateNoteTags missing note {note:999999999999, tags:["a"]} → error envelope (message
    #       differs from getNoteTags' — record exact: expected Note 999999999999 not found: ...).
    # wording is now the clean upstream form, identical to getNoteTags.
    e = err_env("TG-13", "updateNoteTags", {"note": MISSING, "tags": ["a"]})
    if e is not None:
        record("TG-13", f"exact error message: {e!r}")
        check(
            "TG-13",
            e == "Note was not found: 999999999999",
            f"error={e!r} (expected the clean 'Note was not found: 999999999999')",
        )
    healthy("TG-13")

    # TG-14 wire-name validation
    # Spec: TG-14 — wire-name validation camelCase tagToReplace → error envelope (extra=forbid); missing
    #       replace_with_tag → error envelope.
    e = err_env(
        "TG-14", "replaceTags", {"notes": [n1], "tagToReplace": "x", "replace_with_tag": "y"}
    )
    if e is not None:
        record("TG-14", f"camelCase tagToReplace error: {e!r}")
    e = err_env("TG-14", "replaceTags", {"notes": [n1], "tag_to_replace": "x"})
    if e is not None:
        record("TG-14", f"missing replace_with_tag error: {e!r}")
    healthy("TG-14")

    # TG-15 tag: search integration (n1 has ["x","y"] since TG-09)
    # Spec: TG-15 — tag:list search integration after TG-09, findNotes {query:"tag:x"} returns n1;
    #       findNotes {query:"tag:nope"} → [].
    st, body = call("findNotes", {"query": "tag:x"})
    rec = body.get("result") if isinstance(body, dict) else None
    check(
        "TG-15",
        st == 200 and isinstance(rec, list) and n1 in rec and len(rec) == 1,
        f"req=findNotes tag:x status={st} resp={body!r} (want exactly [n1])",
    )
    st, body = call("findNotes", {"query": "tag:nope"})
    rec = body.get("result") if isinstance(body, dict) else None
    check(
        "TG-15",
        st == 200 and rec == [],
        f"req=findNotes tag:nope status={st} resp={body!r} (want [])",
    )

    # TG-16 envelope/legacy + resilience (C2-C5)
    # Spec: TG-16 — envelope/legacy + resilience per common criteria C2-C5.
    st, body = call("version")
    check(
        "TG-16",
        st == 200 and body == {"result": 6, "error": None},
        f"C2 version envelope: status={st} resp={body!r}",
    )
    st, body = call("getTags", {}, version=4)
    check(
        "TG-16",
        st == 200 and isinstance(body, list),
        f"C4 version=4 bare result: status={st} resp={body!r}",
    )
    st, body = call("version", {}, version=3)
    check(
        "TG-16",
        st == 200 and not isinstance(body, dict),
        f"C4 version=3 bare result: status={st} resp={body!r}",
    )
    st, body = C.raw_post({"action": "getTags", "params": {}})
    check(
        "TG-16",
        st == 200 and isinstance(body, list),
        f"C4 missing version -> bare result: status={st} resp={body!r}",
    )
    st, body = call("nope")
    check(
        "TG-16",
        st == 200
        and isinstance(body, dict)
        and isinstance(body.get("error"), str)
        and body.get("result") is None,
        f"C3 unknown action: status={st} resp={body!r}",
    )
    healthy("TG-16")

    return summary()


if __name__ == "__main__":
    sys.exit(main())
