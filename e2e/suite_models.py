#!/usr/bin/env python3
"""E2E black-box suite — model management actions (modelField*, modelTemplate*, findAndReplaceInModels).

Run from the repo root:

    python3 e2e/suite_models.py http://localhost:18765

Implements every case MD-01..MD-33 plus the common criteria C1-C6 from
e2e/README.md; every case's criteria are inlined as a "# Spec:" comment under
its banner (or its section header). API-only: all fixture data and assertions
go through POST /api via e2e/anki_client.py.

Fixture (via API): model "E2EModel": fields [F1, F2], template
[{Name:"T1", Front:"{{F1}}", Back:"{{F2}}" + " black"}], css
"body { color: black; }". A note is added in deck Models (F1="m-F1",
F2="m-F2") using E2EModel. The built-in Basic model also exists with its
default css (contains "color: black").
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from anki_client import Client, check, record, summary

MODEL = "E2EModel"
DECK = "Models"
NOTE_FRONT = "m-F1"
NOTE_BACK = "m-F2"
MISSING_MODEL = "NoSuchModel"
MISSING_FIELD = "Nope"
MISSING_TEMPLATE = "Nope"
ERR_MODEL = f"model was not found: {MISSING_MODEL}"
ERR_FIELD = f"field was not found in {MODEL}: {MISSING_FIELD}"
ERR_TEMPLATE = f"template was not found in {MODEL}: {MISSING_TEMPLATE}"

c = Client("")  # re-bound in main


# ------------------------------------------------------------------ helpers


def names() -> list[str]:
    return c.ok("modelFieldNames", {"modelName": MODEL})


def tpls() -> dict[str, dict[str, str]]:
    return c.ok("modelTemplates", {"modelName": MODEL})


def css(model: str = MODEL) -> str:
    return str(c.ok("modelStyling", {"modelName": model}).get("css", ""))


def cards() -> int:
    return len(c.ok("findCards", {"query": f'deck:"{DECK}"'}))


def note_fields(nid: int) -> dict[str, str]:
    infos = c.ok("notesInfo", {"notes": [nid]})
    return {k: v.get("value") for k, v in infos[0]["fields"].items()}


def is_error_envelope(st: int, body: object) -> bool:
    """HTTP 200 + {'result': None, 'error': str} per C3."""
    return (
        st == 200
        and isinstance(body, dict)
        and isinstance(body.get("error"), str)
        and body.get("result") is None
    )


def is_null_envelope(st: int, body: object) -> bool:
    """HTTP 200 + {'result': None, 'error': None} per C2."""
    return st == 200 and body == {"result": None, "error": None}


def expect_error(case_id: str, action: str, params: dict, exact: str | None = None) -> object:
    """Assert a client-error envelope (C3) and post-failure health (C5)."""
    st, body = c.request(action, params)
    ok = is_error_envelope(st, body)
    if ok and exact is not None:
        ok = body["error"] == exact  # type: ignore[index]
    detail = f"POST /api {action} {params!r} -> HTTP {st} {body!r}"
    if ok:
        hst, _ = c.get("/health")
        ok = hst == 200
        detail += f" | health after: {hst}"
    check(case_id, ok, detail)
    return body


# ------------------------------------------------------------------ cases


def fixture() -> int:
    """E2EModel + one note in deck Models; Basic exists with default css."""
    st, body = c.request(
        "createModel",
        {
            "modelName": MODEL,
            "inOrderFields": ["F1", "F2"],
            "cardTemplates": [{"Name": "T1", "Front": "{{F1}}", "Back": "{{F2}} black"}],
            "css": "body { color: black; }",
        },
    )
    record("FX", f"createModel -> HTTP {st} {body!r}")
    check(
        "FX-1",
        st == 200 and isinstance(body, dict) and body.get("error") is None,
        f"createModel -> HTTP {st} {body!r}",
    )
    # P2-8 fixed contract: createModel returns the created model (upstream
    # parity), so clients can read the modelId without a second call.
    created = body.get("result") if isinstance(body, dict) else None
    check(
        "FX-1b",
        isinstance(created, dict) and created.get("name") == MODEL and created.get("id") > 0,
        f"createModel must return the created model with name/id; got {created!r}",
    )

    c.ok("createDeck", {"deck": DECK})
    nid = c.ok(
        "addNote",
        {
            "note": {
                "deckName": DECK,
                "modelName": MODEL,
                "fields": {"F1": NOTE_FRONT, "F2": NOTE_BACK},
            }
        },
    )
    check("FX-2", isinstance(nid, int), f"addNote returned {nid!r}")

    check("FX-3", names() == ["F1", "F2"], f"modelFieldNames -> {names()!r}")
    check(
        "FX-3",
        tpls() == {"T1": {"Front": "{{F1}}", "Back": "{{F2}} black"}},
        f"modelTemplates -> {tpls()!r}",
    )
    check("FX-3", css() == "body { color: black; }", f"modelStyling css -> {css()!r}")
    check(
        "FX-3",
        note_fields(nid) == {"F1": NOTE_FRONT, "F2": NOTE_BACK},
        f"notesInfo fields -> {note_fields(nid)!r}",
    )
    check("FX-4", cards() == 1, f"findCards deck:'{DECK}' -> {cards()}")
    models = c.ok("modelNames")
    check("FX-4", "Basic" in models and MODEL in models, f"modelNames -> {models!r}")
    return nid


def md_01_02_03_04() -> None:
    # MD-01: add F3 -> null; names [F1,F2,F3]
    # Spec: MD-01 — modelFieldAdd happy {modelName:"E2EModel", fieldName:"F3"} → null; modelFieldNames ==
    #       ["F1","F2","F3"].
    st, body = c.request("modelFieldAdd", {"modelName": MODEL, "fieldName": "F3"})
    n = names()
    check(
        "MD-01",
        is_null_envelope(st, body) and n == ["F1", "F2", "F3"],
        f"modelFieldAdd F3 -> HTTP {st} {body!r} | names={n!r}",
    )

    # MD-02: add F0 at index 0
    # Spec: MD-02 — modelFieldAdd at index add "F0" with index: 0 → ["F0","F1","F2","F3"].
    st, body = c.request("modelFieldAdd", {"modelName": MODEL, "fieldName": "F0", "index": 0})
    n = names()
    check(
        "MD-02",
        is_null_envelope(st, body) and n == ["F0", "F1", "F2", "F3"],
        f"modelFieldAdd F0 idx 0 -> HTTP {st} {body!r} | names={n!r}",
    )

    # MD-03a: existing name again -> not duplicated
    # Spec: MD-03 — modelFieldAdd existing name {fieldName:"F3"} again → not duplicated (modelFieldNames
    #       unchanged); with index: 0 → "F3" moved to front (existing field repositioned — record exact
    #       order).
    st, body = c.request("modelFieldAdd", {"modelName": MODEL, "fieldName": "F3"})
    n = names()
    check(
        "MD-03a",
        is_null_envelope(st, body) and n == ["F0", "F1", "F2", "F3"],
        f"modelFieldAdd F3 again -> HTTP {st} {body!r} | names={n!r}",
    )

    # MD-03b: existing name with index 0 -> repositioned to front
    st, body = c.request("modelFieldAdd", {"modelName": MODEL, "fieldName": "F3", "index": 0})
    n = names()
    record("MD-03b", f"existing field + index 0 -> order {n!r}")
    check(
        "MD-03b",
        is_null_envelope(st, body) and n == ["F3", "F0", "F1", "F2"],
        f"modelFieldAdd F3 idx 0 -> HTTP {st} {body!r} | names={n!r}",
    )

    # MD-04: missing model
    # Spec: MD-04 — modelFieldAdd missing model {modelName:"NoSuchModel", fieldName:"X"} → error envelope,
    #       exact message model was not found: NoSuchModel.
    expect_error(
        "MD-04", "modelFieldAdd", {"modelName": MISSING_MODEL, "fieldName": "X"}, exact=ERR_MODEL
    )


def md_05_06_07_08_09_10(nid: int) -> None:
    # MD-05: remove F3; note data intact
    # Spec: MD-05 — modelFieldRemove happy remove "F3" → gone from modelFieldNames; the E2E note's F1/F2
    #       data intact (notesInfo), result null.
    st, body = c.request("modelFieldRemove", {"modelName": MODEL, "fieldName": "F3"})
    n, nf = names(), note_fields(nid)
    check(
        "MD-05",
        is_null_envelope(st, body)
        and n == ["F0", "F1", "F2"]
        and nf.get("F1") == NOTE_FRONT
        and nf.get("F2") == NOTE_BACK,
        f"modelFieldRemove F3 -> HTTP {st} {body!r} | names={n!r} | note fields={nf!r}",
    )

    # MD-06: missing field
    # Spec: MD-06 — modelFieldRemove missing field → error field was not found in E2EModel: Nope.
    expect_error(
        "MD-06",
        "modelFieldRemove",
        {"modelName": MODEL, "fieldName": MISSING_FIELD},
        exact=ERR_FIELD,
    )

    # MD-07: rename F1 -> Q1; note data follows; anki 26.8 ALSO rewrites the
    # Spec: MD-07 — modelFieldRename happy {oldFieldName:"F1", newFieldName:"Q1"} → modelFieldNames
    #       updated; note data preserved under Q1 (notesInfo fields contain m-F1 at Q1); old templates
    #       still reference {{F1}} (record: rename does NOT rewrite templates).
    # renamed field's template references on save (documented behavior,
    # E2E P3-15: the backend's schema-change handling updates {{F1}} -> {{Q1}},
    # leaving no dangling refs).
    st, body = c.request(
        "modelFieldRename", {"modelName": MODEL, "oldFieldName": "F1", "newFieldName": "Q1"}
    )
    n, nf, t = names(), note_fields(nid), tpls()
    check(
        "MD-07",
        is_null_envelope(st, body) and n == ["F0", "Q1", "F2"] and nf.get("Q1") == NOTE_FRONT,
        f"rename F1->Q1 -> HTTP {st} {body!r} | names={n!r} | note fields={nf!r}",
    )
    check(
        "MD-07",
        t.get("T1", {}).get("Front") == "{{Q1}}",
        f"rename must rewrite the template ref to the new field name (anki 26.8 save path): T1 -> {t.get('T1')!r}",
    )
    record("MD-07", f"templates after field rename: {t!r}")

    # MD-08: missing old field
    # Spec: MD-08 — modelFieldRename missing old field → error field was not found in E2EModel: Nope.
    expect_error(
        "MD-08",
        "modelFieldRename",
        {"modelName": MODEL, "oldFieldName": MISSING_FIELD, "newFieldName": "X"},
        exact=ERR_FIELD,
    )

    # MD-09: reposition F2 to index 0
    # Spec: MD-09 — modelFieldReposition happy move "F2" to index: 0 → first in modelFieldNames.
    st, body = c.request(
        "modelFieldReposition", {"modelName": MODEL, "fieldName": "F2", "index": 0}
    )
    n = names()
    check(
        "MD-09",
        is_null_envelope(st, body) and n == ["F2", "F0", "Q1"],
        f"reposition F2 idx 0 -> HTTP {st} {body!r} | names={n!r}",
    )

    # MD-10: out-of-range index (OBS — 500 would be an ISSUE)
    # Spec: MD-10 — modelFieldReposition out-of-range index (e.g. 99 or -1): record behavior (error
    #       envelope? clamped? 500 = ISSUE). OBS.
    st, body = c.request(
        "modelFieldReposition", {"modelName": MODEL, "fieldName": "F2", "index": 99}
    )
    n = names()
    check(
        "MD-10a",
        st == 200 and isinstance(body, dict) and body.get("error") is None,
        f"reposition idx 99 -> HTTP {st} {body!r}",
    )
    record("MD-10a", f"index 99 -> order {n!r}")

    st, body = c.request(
        "modelFieldReposition", {"modelName": MODEL, "fieldName": "F2", "index": -1}
    )
    n = names()
    check(
        "MD-10b",
        st == 200 and isinstance(body, dict) and body.get("error") is None,
        f"reposition idx -1 -> HTTP {st} {body!r}",
    )
    record("MD-10b", f"index -1 -> order {n!r}")

    # restore known order for the field-order-dependent cases below
    c.request("modelFieldReposition", {"modelName": MODEL, "fieldName": "F2", "index": 0})
    n = names()
    check("MD-10", n == ["F2", "F0", "Q1"], f"restored field order -> {n!r}")


def md_11_to_15() -> None:
    # MD-11: set font (probe with Courier first so Arial is a real change)
    # Spec: MD-11 — modelFieldSetFont {"F2" font=Arial} → modelFieldFonts "F2".font == "Arial".
    st, body = c.request(
        "modelFieldSetFont", {"modelName": MODEL, "fieldName": "F2", "font": "Courier"}
    )
    f = c.ok("modelFieldFonts", {"modelName": MODEL})
    ok1 = is_null_envelope(st, body) and f.get("F2", {}).get("font") == "Courier"
    st, body = c.request(
        "modelFieldSetFont", {"modelName": MODEL, "fieldName": "F2", "font": "Arial"}
    )
    f = c.ok("modelFieldFonts", {"modelName": MODEL})
    check(
        "MD-11",
        ok1 and is_null_envelope(st, body) and f.get("F2", {}).get("font") == "Arial",
        f"setFont F2 Arial -> HTTP {st} {body!r} | fonts={f!r}",
    )

    # MD-12: font size 42
    # Spec: MD-12 — modelFieldSetFontSize size 42 → modelFieldFonts "F2".size == 42.
    st, body = c.request(
        "modelFieldSetFontSize", {"modelName": MODEL, "fieldName": "F2", "fontSize": 42}
    )
    f = c.ok("modelFieldFonts", {"modelName": MODEL})
    check(
        "MD-12",
        is_null_envelope(st, body) and f.get("F2", {}).get("size") == 42,
        f"setFontSize F2 42 -> HTTP {st} {body!r} | fonts={f!r}",
    )

    # MD-13: set description -> result True; description at F2's index
    # Spec: MD-13 — modelFieldSetDescription desc "my desc" → result == true; modelFieldDescriptions
    #       contains "my desc" at F2's index.
    st, body = c.request(
        "modelFieldSetDescription",
        {"modelName": MODEL, "fieldName": "F2", "description": "my desc"},
    )
    n, d = names(), c.ok("modelFieldDescriptions", {"modelName": MODEL})
    idx = n.index("F2")
    check(
        "MD-13",
        st == 200
        and body == {"result": True, "error": None}
        and idx < len(d)
        and d[idx] == "my desc",
        f"setDescription F2 -> HTTP {st} {body!r} | names={n!r} | descriptions={d!r}",
    )

    # MD-14: descriptions list, one per field, in field order
    # Spec: MD-14 — modelFieldDescriptions happy list, one entry per field, in field order.
    d = c.ok("modelFieldDescriptions", {"modelName": MODEL})
    n = names()
    others_ok = all(v in ("", None) for i, v in enumerate(d) if i != n.index("F2"))
    check(
        "MD-14",
        isinstance(d, list) and len(d) == len(n) and d[n.index("F2")] == "my desc" and others_ok,
        f"modelFieldDescriptions -> {d!r} (fields {n!r})",
    )

    # MD-15: fonts dict covering all fields
    # Spec: MD-15 — modelFieldFonts happy dict {fieldName: {font, size}} covering all fields.
    f = c.ok("modelFieldFonts", {"modelName": MODEL})
    n = names()
    ok = (
        isinstance(f, dict)
        and set(f.keys()) == set(n)
        and all(isinstance(v, dict) and "font" in v and "size" in v for v in f.values())
        and f.get("F2") == {"font": "Arial", "size": 42}
    )
    check("MD-15", ok, f"modelFieldFonts -> {f!r} (fields {n!r})")
    record("MD-15", f"fonts key order = {list(f.keys())!r}, field order = {n!r}")


def md_16_to_20() -> None:
    # MD-16: add T2 -> card count doubles
    # Spec: MD-16 — modelTemplateAdd new template {template: {Name:"T2", Front:"{{Q1}}!", Back:"{{F2}}?"}}
    #       → null; modelTemplates contains T2; findCards deck:Models count DOUBLED (each note now has 2
    #       cards). Record counts before/after.
    before = cards()
    st, body = c.request(
        "modelTemplateAdd",
        {"modelName": MODEL, "template": {"Name": "T2", "Front": "{{Q1}}!", "Back": "{{F2}}?"}},
    )
    t, after = tpls(), cards()
    record("MD-16", f"findCards deck:'{DECK}' before={before} after={after}")
    check(
        "MD-16",
        is_null_envelope(st, body)
        and t.get("T2") == {"Front": "{{Q1}}!", "Back": "{{F2}}?"}
        and after == 2 * before,
        f"modelTemplateAdd T2 -> HTTP {st} {body!r} | templates={t!r} | cards {before}->{after}",
    )

    # MD-17: update-existing must PERSIST (intentional fix of upstream's lost change)
    # Spec: MD-17 — modelTemplateAdd update-existing (the intentional fix) same Name "T2", new Front
    #       "{{Q1}}!!" → null; modelTemplates T2 Front == "{{Q1}}!!" — the change MUST persist (upstream
    #       loses it; this PR intentionally saves). Assert persisted.
    st, body = c.request(
        "modelTemplateAdd",
        {"modelName": MODEL, "template": {"Name": "T2", "Front": "{{Q1}}!!", "Back": "{{F2}}?"}},
    )
    t = tpls()
    check(
        "MD-17",
        is_null_envelope(st, body) and t.get("T2", {}).get("Front") == "{{Q1}}!!",
        f"modelTemplateAdd T2 update -> HTTP {st} {body!r} | templates={t!r}",
    )
    record("MD-17", f"T2 after update-existing call: {t.get('T2')!r}")

    # MD-18: invalid template (Front has no field reference) -> error envelope, NOT 500
    # Spec: MD-18 — modelTemplateAdd invalid template Front without any field reference ("static") → error
    #       envelope (anki CardTypeError mapped to client error); NOT a 500. Record message.
    st, body = c.request(
        "modelTemplateAdd",
        {"modelName": MODEL, "template": {"Name": "T3", "Front": "static", "Back": "{{F2}}"}},
    )
    check(
        "MD-18",
        is_error_envelope(st, body),
        f"modelTemplateAdd T3 Front='static' -> HTTP {st} {body!r}",
    )
    record(
        "MD-18",
        f"CardTypeError mapped to client error: HTTP {st}, error={body.get('error')!r}"
        if isinstance(body, dict)
        else f"raw body: {body!r}",
    )
    check("MD-18", "T3" not in tpls(), f"T3 must not be persisted; templates={tpls()!r}")

    # MD-19: missing model
    # Spec: MD-19 — modelTemplateAdd missing model → error model was not found: NoSuchModel.
    expect_error(
        "MD-19",
        "modelTemplateAdd",
        {
            "modelName": MISSING_MODEL,
            "template": {"Name": "X", "Front": "{{F2}}", "Back": "{{F2}}"},
        },
        exact=ERR_MODEL,
    )

    # MD-20: remove T2 -> card count back to 1 per note
    # Spec: MD-20 — modelTemplateRemove happy remove "T2" → gone; card count back to 1 per note.
    before = cards()
    st, body = c.request("modelTemplateRemove", {"modelName": MODEL, "templateName": "T2"})
    t, after = tpls(), cards()
    check(
        "MD-20",
        is_null_envelope(st, body) and list(t.keys()) == ["T1"] and after == before // 2,
        f"modelTemplateRemove T2 -> HTTP {st} {body!r} | templates={t!r} | cards {before}->{after}",
    )


def md_21_22(nid: int) -> None:
    # MD-21: removing the LAST template must be an error envelope (500 = ISSUE)
    # Spec: MD-21 — modelTemplateRemove LAST template remove "T1" (only remaining) → EXPECT an error
    #       envelope (anki requires ≥1 template). Record status code + message. If HTTP 500 → ISSUE
    #       (non-ValueError exception leaking as server error).
    req = {"modelName": MODEL, "templateName": "T1"}
    st, body = c.request("modelTemplateRemove", req)
    ok = is_error_envelope(st, body)
    check("MD-21", ok, f"modelTemplateRemove last template -> HTTP {st} {body!r}")
    if not ok:
        record("MD-21", f"ISSUE: HTTP {st} (expected 200 error envelope), body={body!r}")
    record("MD-21", f"exact status={st}, body={body!r}")
    t = tpls()
    check("MD-21", "T1" in t, f"T1 still present after rejected removal: {t!r}")
    hst, _ = c.get("/health")
    check("MD-21", hst == 200, f"health after last-template removal -> {hst}")

    # MD-22: missing template
    # Spec: MD-22 — modelTemplateRemove missing template → error template was not found in E2EModel: Nope.
    expect_error(
        "MD-22",
        "modelTemplateRemove",
        {"modelName": MODEL, "templateName": MISSING_TEMPLATE},
        exact=ERR_TEMPLATE,
    )
    _ = nid  # note id re-checked in MD-23


def md_23_24_25(nid: int) -> None:
    # MD-23: rename T1 -> Main
    # Spec: MD-23 — modelTemplateRename happy T1 → "Main" → modelTemplates key updated; note/card data
    #       intact.
    st, body = c.request(
        "modelTemplateRename",
        {"modelName": MODEL, "oldTemplateName": "T1", "newTemplateName": "Main"},
    )
    t, nf, cnt = tpls(), note_fields(nid), cards()
    check(
        "MD-23",
        is_null_envelope(st, body)
        and list(t.keys()) == ["Main"]
        and nf.get("Q1") == NOTE_FRONT
        and nf.get("F2") == NOTE_BACK
        and cnt == 1,
        f"rename T1->Main -> HTTP {st} {body!r} | templates={t!r} | note={nf!r} | cards={cnt}",
    )

    # MD-24: missing old template
    # Spec: MD-24 — modelTemplateRename missing old → error template was not found in E2EModel: Nope.
    expect_error(
        "MD-24",
        "modelTemplateRename",
        {"modelName": MODEL, "oldTemplateName": MISSING_TEMPLATE, "newTemplateName": "X"},
        exact=ERR_TEMPLATE,
    )

    # MD-25: second template added back, reposition Main
    # Spec: MD-25 — modelTemplateReposition happy with a second template added back, reposition "Main" to
    #       index 0 → order in modelTemplates flips (dict preserves template order). Record order.
    st, body = c.request(
        "modelTemplateAdd",
        {"modelName": MODEL, "template": {"Name": "T2", "Front": "{{Q1}}!!", "Back": "{{F2}}?"}},
    )
    order = list(tpls().keys())
    check(
        "MD-25",
        is_null_envelope(st, body) and order == ["Main", "T2"],
        f"re-add T2 -> HTTP {st} {body!r} | order={order!r}",
    )

    st, body = c.request(
        "modelTemplateReposition", {"modelName": MODEL, "templateName": "Main", "index": 0}
    )
    order = list(tpls().keys())
    record("MD-25", f"reposition Main to index 0 (already at 0) -> order {order!r}")
    check(
        "MD-25",
        is_null_envelope(st, body) and order == ["Main", "T2"],
        f"reposition Main idx 0 -> HTTP {st} {body!r} | order={order!r}",
    )

    st, body = c.request(
        "modelTemplateReposition", {"modelName": MODEL, "templateName": "Main", "index": 1}
    )
    order = list(tpls().keys())
    record("MD-25", f"reposition Main to index 1 -> order {order!r}")
    check(
        "MD-25",
        is_null_envelope(st, body) and order == ["T2", "Main"],
        f"reposition Main idx 1 -> HTTP {st} {body!r} | order={order!r}",
    )

    # restore order for MD-26
    c.request("modelTemplateReposition", {"modelName": MODEL, "templateName": "Main", "index": 0})
    order = list(tpls().keys())
    check("MD-25", order == ["Main", "T2"], f"restored template order -> {order!r}")


def md_26_to_30() -> None:
    # MD-26: findAndReplaceInModels to a NON-EXISTENT field is refused.
    # Spec: MD-26 — findAndReplaceInModels single model {modelName:"E2EModel", findText:"{{Q1}}",
    #       replaceText:"{{Question}}"} → result == 1 (models changed); modelTemplates reflects
    #       replacement.
    # Decided contract (E2E P2-7, documented in README): unlike upstream,
    # this server validates templates on save and refuses replacements
    # that would leave a dangling field reference — a clean 200 error
    # envelope, nothing persisted.
    st, body = c.request(
        "findAndReplaceInModels",
        {"modelName": MODEL, "findText": "{{Q1}}", "replaceText": "{{Question}}"},
    )
    t = tpls()
    check(
        "MD-26",
        st == 200
        and isinstance(body.get("error"), str)
        and "Question" in body.get("error", "")
        and t.get("T2", {}).get("Front") == "{{Q1}}!!",
        f"findAndReplaceInModels to a dangling ref must be refused (200 error envelope, "
        f"nothing persisted); got HTTP {st} {body!r} | templates={t!r}",
    )
    record("MD-26", f"templates unchanged after refused replace: {t!r}")

    # MD-26b: replacement to an EXISTING field succeeds (count 1, persisted).
    # findText "{{Q1}}!!" matches only T2's front (Main's front is bare
    # "{{Q1}}"), so exactly one replacement happens.
    st, body = c.request(
        "findAndReplaceInModels",
        {"modelName": MODEL, "findText": "{{Q1}}!!", "replaceText": "{{F0}}!!"},
    )
    t = tpls()
    check(
        "MD-26b",
        st == 200
        and body == {"result": 1, "error": None}
        and t.get("T2", {}).get("Front") == "{{F0}}!!"
        and t.get("Main", {}).get("Front") == "{{Q1}}",
        f"findAndReplaceInModels to an existing field -> HTTP {st} {body!r} | templates={t!r}",
    )
    # restore T2's front for the remaining cases
    c.request(
        "findAndReplaceInModels",
        {"modelName": MODEL, "findText": "{{F0}}!!", "replaceText": "{{Q1}}!!"},
    )

    # MD-27: all flags off -> nothing replaced anywhere
    # Spec: MD-27 — findAndReplaceInModels flags off {front:false, back:false, css:false,
    #       findText:"black", replaceText:"red"} → result == 0; css unchanged.
    st, body = c.request(
        "findAndReplaceInModels",
        {"front": False, "back": False, "css": False, "findText": "black", "replaceText": "red"},
    )
    e2e_css = css()
    check(
        "MD-27",
        st == 200 and body == {"result": 0, "error": None} and "black" in e2e_css,
        f"flags off (modelName omitted) -> HTTP {st} {body!r} | E2EModel css={e2e_css!r}",
    )

    # MD-28: css-only replace on E2EModel
    # Spec: MD-28 — findAndReplaceInModels css only {modelName:"E2EModel", front:false, back:false,
    #       css:true, findText:"black", replaceText:"red"} → result == 1; modelStyling css contains "red",
    #       not "black".
    st, body = c.request(
        "findAndReplaceInModels",
        {
            "modelName": MODEL,
            "front": False,
            "back": False,
            "css": True,
            "findText": "black",
            "replaceText": "red",
        },
    )
    e2e_css = css()
    check(
        "MD-28",
        st == 200
        and body == {"result": 1, "error": None}
        and "red" in e2e_css
        and "black" not in e2e_css,
        f"css-only replace -> HTTP {st} {body!r} | E2EModel css={e2e_css!r}",
    )

    # MD-29: empty modelName -> ALL models; count must equal the models containing 'black'
    # Spec: MD-29 — findAndReplaceInModels all models (empty name) {modelName:"", findText:"black",
    #       replaceText:"red"} → count == 2 (E2EModel + Basic both contain "black" in css — verify Basic's
    #       css before relying on count; record which models matched).
    models = c.ok("modelNames")
    matched: list[str] = []
    state: dict[str, object] = {}
    for m in models:
        m_css = css(m)
        m_tpls = c.ok("modelTemplates", {"modelName": m})
        has = ("black" in m_css) or any(
            "black" in v.get("Front", "") or "black" in v.get("Back", "") for v in m_tpls.values()
        )
        state[m] = {"css": m_css, "templates": m_tpls}
        if has:
            matched.append(m)
    record("MD-29", f"models={models!r}; containing 'black' before replace: {matched!r}")
    check(
        "MD-29",
        "Basic" in matched,
        f"Basic expected to contain 'black' in css; Basic css={css('Basic')!r}",
    )

    st, body = c.request(
        "findAndReplaceInModels", {"modelName": "", "findText": "black", "replaceText": "red"}
    )
    ok = (
        st == 200
        and isinstance(body, dict)
        and body.get("error") is None
        and body.get("result") == len(matched)
    )
    detail = (
        f"POST /api findAndReplaceInModels {{modelName:'', findText:'black', "
        f"replaceText:'red'}} -> HTTP {st} {body!r} | matched={matched!r}"
    )
    if ok:
        leftovers = []
        for m in matched:
            m_css, m_tpls = css(m), c.ok("modelTemplates", {"modelName": m})
            if "black" in m_css or any(
                "black" in v.get("Front", "") or "black" in v.get("Back", "")
                for v in m_tpls.values()
            ):
                leftovers.append(m)
        ok = not leftovers
        detail += f" | models still containing 'black' after: {leftovers!r}"
    check("MD-29", ok, detail)
    record(
        "MD-29",
        f"count reported: {body.get('result') if isinstance(body, dict) else body!r}; "
        f"expected (models containing 'black'): {len(matched)}",
    )

    # MD-30: missing explicit model
    # Spec: MD-30 — findAndReplaceInModels missing explicit model {modelName:"NoSuchModel", ...} → error
    #       model was not found: NoSuchModel.
    expect_error(
        "MD-30",
        "findAndReplaceInModels",
        {"modelName": MISSING_MODEL, "findText": "x", "replaceText": "y"},
        exact=ERR_MODEL,
    )


def md_31_32() -> None:
    # MD-31: missing model across remaining read/write actions — envelopes, no 500s
    # Spec: MD-31 — missing-model/field/template across remaining read actions modelFieldDescriptions /
    #       modelFieldFonts / modelTemplateReposition with NoSuchModel → error envelope each (no 500s).
    expect_error("MD-31", "modelFieldDescriptions", {"modelName": MISSING_MODEL}, exact=ERR_MODEL)
    expect_error("MD-31", "modelFieldFonts", {"modelName": MISSING_MODEL}, exact=ERR_MODEL)
    expect_error(
        "MD-31",
        "modelTemplateReposition",
        {"modelName": MISSING_MODEL, "templateName": "T1", "index": 0},
        exact=ERR_MODEL,
    )

    # MD-32: wire shape — template requires capitalized Name/Front/Back
    # Spec: MD-32 — wire shapes modelTemplateAdd requires template.Name/Front/Back (capitalized,
    #       upstream); missing Front → error envelope. Record.
    req = {"modelName": MODEL, "template": {"Name": "T9", "Back": "{{F2}}"}}
    st, body = c.request("modelTemplateAdd", req)
    check(
        "MD-32",
        is_error_envelope(st, body),
        f"modelTemplateAdd missing Front -> HTTP {st} {body!r}",
    )
    if isinstance(body, dict):
        record("MD-32", f"missing 'Front' error message: {body.get('error')!r}")
    check("MD-32", "T9" not in tpls(), f"T9 must not be added; templates={tpls()!r}")
    hst, _ = c.get("/health")
    check("MD-32", hst == 200, f"health after invalid template -> {hst}")


def md_33() -> None:
    # Spec: MD-33 — envelope/legacy + resilience per C2-C5.
    # C1: POST /api + spot-check POST /
    st, body = c.request("deckNames", {}, path="/api")
    st_root, body_root = c.request("deckNames", {}, path="/")
    check(
        "MD-33-C1",
        st == 200
        and isinstance(body, dict)
        and body.get("error") is None
        and st_root == 200
        and body_root == body,
        f"POST /api -> {st} {body!r}; POST / -> {st_root} {body_root!r}",
    )

    # C2: version action envelope
    st, body = c.request("version")
    check(
        "MD-33-C2",
        st == 200 and body == {"result": 6, "error": None},
        f"version -> HTTP {st} {body!r}",
    )

    # C3: unknown action -> 200 error envelope, never 500
    body = expect_error("MD-33-C3", "definitelyNotAnAction", {})
    if isinstance(body, dict):
        record("MD-33-C3", f"unknown action message: {body.get('error')!r}")

    # C3: invalid params -> 200 error envelope
    expect_error("MD-33-C3", "modelFieldAdd", {"modelName": MODEL})  # fieldName missing

    # C4: legacy versions return the bare result (no envelope)
    st4, bare4 = c.request("deckNames", version=4)
    st2, bare2 = c.request("deckNames", version=2)
    stm, barem = c.raw_post({"action": "deckNames", "params": {}})
    ok = (
        st4 == 200
        and isinstance(bare4, list)
        and st2 == 200
        and isinstance(bare2, list)
        and stm == 200
        and isinstance(barem, list)
    )
    detail = f"v4 -> {st4} {bare4!r}; v2 -> {st2} {bare2!r}; missing version -> {stm} {barem!r}"
    check("MD-33-C4", ok, detail)
    # legacy + error: envelope is still sent (upstream convention) — record shape
    ste, enve = c.request("definitelyNotAnAction", version=4)
    record("MD-33-C4", f"unknown action at version 4 -> HTTP {ste} {enve!r}")

    # C5: server still healthy and serving after all the error cases above
    hst, hbody = c.get("/health")
    still = c.request("modelNames")
    check(
        "MD-33-C5",
        hst == 200
        and still[0] == 200
        and isinstance(still[1], dict)
        and still[1].get("error") is None,
        f"GET /health -> {hst} {hbody!r}; modelNames after everything -> {still[0]} {still[1]!r}",
    )


def main() -> int:
    global c
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:18765"
    c = Client(base)
    print(f"# suite_models against {base} (model management)")
    if not c.wait_healthy(tries=30, delay=1.0):
        check("FX-0", False, "server never became healthy")
        return summary()

    nid = fixture()
    md_01_02_03_04()
    md_05_06_07_08_09_10(nid)
    md_11_to_15()
    md_16_to_20()
    md_21_22(nid)
    md_23_24_25(nid)
    md_26_to_30()
    md_31_32()
    md_33()
    return summary()


if __name__ == "__main__":
    sys.exit(main())
