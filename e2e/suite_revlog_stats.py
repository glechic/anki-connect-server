#!/usr/bin/env python3
"""E2E black-box suite — revlog & stats actions (cardReviews, getReviewsOfCards, getLatestReviewID, review counts, insertReviews, getDeckStats, getCollectionStatsHTML).

Implements every case (ST-01..ST-23) against any anki-connect-server build.
Every case's criteria are inlined as a "# Spec:" comment under its banner.
API-only: all fixture setup and assertions go through anki_client.py's HTTP
client (POST /api); the server library and the collection DB are never touched
directly.

Fixture (via API): deck Stats; 2 notes (stats-F1, stats-F2); answer card of
note 1 with ease 3 (Good) via answerCards, card of note 2 with ease 1
(Again). Child deck Stats::Child with 1 note (stats-C1).

Run from the repo root:
    python3 e2e/suite_revlog_stats.py http://localhost:18764
"""

from __future__ import annotations

import re
import sys
import time

from anki_client import Client, check, die, record, summary

REV_KEYS = {"id", "usn", "ease", "ivl", "lastIvl", "factor", "time", "type"}
DAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def main() -> int:
    if len(sys.argv) != 2:
        die("usage: python3 e2e/suite_revlog_stats.py <base_url>")
    c = Client(sys.argv[1])
    if not c.wait_healthy(tries=15):
        die(f"server at {sys.argv[1]} not healthy")
    c1 = c2 = c3 = 0

    try:
        # ---------------------------------------------------------------- fixture
        stats_id = c.create_deck("Stats")
        c.add_note("Stats", "stats-F1", "back-F1")
        c.add_note("Stats", "stats-F2", "back-F2")
        c1_list = c.find_cards('deck:"Stats" Front:"stats-F1"')
        c2_list = c.find_cards('deck:"Stats" Front:"stats-F2"')
        check(
            "FX-01",
            isinstance(stats_id, int) and stats_id > 0 and len(c1_list) == 1 and len(c2_list) == 1,
            f"stats_id={stats_id} c1={c1_list} c2={c2_list}",
        )
        c1, c2 = c1_list[0], c2_list[0]
        ans1 = c.ok("answerCards", {"answers": [{"cardId": c1, "ease": 3}]})
        ans2 = c.ok("answerCards", {"answers": [{"cardId": c2, "ease": 1}]})
        check("FX-02", ans1 == [True] and ans2 == [True], f"answerCards: {ans1}, {ans2}")
        c.add_note("Stats::Child", "stats-C1", "back-C1")
        c3_list = c.find_cards('deck:"Stats::Child" Front:"stats-C1"')
        check("FX-03", len(c3_list) == 1, f"child cards: {c3_list}")
        c3 = c3_list[0]
        record(
            "FX-04",
            f"fixture: deck Stats id={stats_id}, cards c1={c1} (ease 3), c2={c2} (ease 1), c3={c3} (Stats::Child)",
        )

        # ---------------------------------------------------------------- ST-01 cardReviews happy
        # Spec: ST-01 — cardReviews happy {deck:"Stats", startID:0} → ≥1 rows; each row is a 9-int array
        #       [id, cid, usn, ease, ivl, lastIvl, factor, time, type]; ease ∈ {1,2,3,4}; all rows' cid
        #       belong to Stats' cards; ids > 0 (ms epoch).
        rows = c.ok("cardReviews", {"deck": "Stats", "startID": 0})
        check("ST-01a", isinstance(rows, list) and len(rows) >= 1, f"got {rows!r}")
        well_formed = all(
            isinstance(r, list) and len(r) == 9 and all(isinstance(x, int) for x in r) for r in rows
        )
        check(
            "ST-01b",
            well_formed,
            "each row must be a 9-int array [id,cid,usn,ease,ivl,lastIvl,factor,time,type]",
        )
        check(
            "ST-01c",
            all(r[0] > 0 and r[3] in (1, 2, 3, 4) for r in rows),
            f"ids/eases: {[(r[0], r[3]) for r in rows]}",
        )
        check(
            "ST-01d",
            all(r[1] in (c1, c2) for r in rows),
            f"all cids must be Stats cards (c1={c1}, c2={c2}); got cids {[r[1] for r in rows]}",
        )
        record("ST-01e", f"{len(rows)} rows: {rows}")
        max_id = max(r[0] for r in rows) if rows else 0
        n_at_max = sum(1 for r in rows if r[0] == max_id)

        # ---------------------------------------------------------------- ST-02 startID filter
        # Spec: ST-02 — cardReviews startID filter startID = <max row id from ST-01> → []; startID =
        #       max_id - 1 → exactly 1 row (the newest).
        r_at_max = c.ok("cardReviews", {"deck": "Stats", "startID": max_id})
        check(
            "ST-02a",
            r_at_max == [],
            f"startID={max_id} (the max row id) → expected [], got {r_at_max!r}",
        )
        r_before = c.ok("cardReviews", {"deck": "Stats", "startID": max_id - 1})
        newest = [r for r in r_before if r[0] == max_id]
        check(
            "ST-02b",
            len(r_before) == n_at_max and len(newest) == n_at_max and n_at_max == 1,
            f"startID={max_id - 1} → expected exactly 1 newest row, got {len(r_before)} rows: {r_before!r}",
        )

        # ---------------------------------------------------------------- ST-03 cardReviews unknown deck (parity quirk)
        # Spec: ST-03 — cardReviews unknown deck (parity quirk) {deck:"Ghost", startID:0} → [] AND
        #       deckNames now contains "Ghost" (decks.id() creates it — upstream parity; verify + record).
        ghost_rows = c.ok("cardReviews", {"deck": "Ghost", "startID": 0})
        check("ST-03a", ghost_rows == [], f"unknown deck → expected [], got {ghost_rows!r}")
        names = c.ok("deckNames")
        check(
            "ST-03b",
            "Ghost" in names,
            f"'Ghost' must appear in deckNames after cardReviews; deckNames={names}",
        )
        record(
            "ST-03c",
            "parity quirk confirmed: cardReviews with an unknown deck CREATES the deck (decks.id() side effect); 'Ghost' now in deckNames — upstream does the same",
        )

        # ---------------------------------------------------------------- ST-04 cardReviews missing params
        # Spec: ST-04 — cardReviews missing params no deck → error envelope; startID string "0" → record
        #       (coercion? OBS).
        err = c.err("cardReviews", {"startID": 0})
        check(
            "ST-04a", "deck" in err and "required" in err.lower(), f"missing deck → error: {err!r}"
        )
        status, body = c.request("cardReviews", {})
        check(
            "ST-04b",
            status == 200 and isinstance(body.get("error"), str) and body.get("result") is None,
            f"empty params → status={status} body={body!r}",
        )
        status, body = c.request("cardReviews", {"deck": "Stats", "startID": "0"})
        if body.get("error") is None:
            record(
                "ST-04c",
                f"startID='0' (string) is coerced to int 0 by pydantic and accepted: {len(body['result'])} rows (same as ST-01)",
            )
        else:
            record("ST-04c", f"startID='0' (string) rejected with error: {body['error']!r}")

        # ---------------------------------------------------------------- ST-05 getReviewsOfCards happy
        # Spec: ST-05 — getReviewsOfCards happy {cards:[c1]} → {"<c1>": [
        #       {id,usn,ease,ivl,lastIvl,factor,time,type}, ... ]} — rows have the 8 keys and NO cid key.
        roc = c.ok("getReviewsOfCards", {"cards": [c1]})
        check(
            "ST-05a",
            isinstance(roc, dict) and set(roc) == {str(c1)},
            f"expected key '{c1}', got {list(roc)!r}",
        )
        rrows = roc[str(c1)]
        check(
            "ST-05b",
            len(rrows) >= 1 and all(set(row) == REV_KEYS for row in rrows),
            f"each row must have exactly the 8 keys {sorted(REV_KEYS)}; got {[sorted(r) for r in rrows]}",
        )
        check(
            "ST-05c",
            all("cid" not in row and isinstance(row["id"], int) and row["id"] > 0 for row in rrows),
            f"no cid key, ids>0; rows={rrows!r}",
        )
        record("ST-05d", f"rows for card {c1}: {rrows}")

        # ---------------------------------------------------------------- ST-06 getReviewsOfCards no reviews + missing
        # Spec: ST-06 — getReviewsOfCards no reviews + missing {cards:[999999999999]} → {"999999999999":
        #       []}; mixed [c1, 999999999999] → both keys.
        miss = c.ok("getReviewsOfCards", {"cards": [999999999999]})
        check(
            "ST-06a",
            miss == {"999999999999": []},
            f"unknown card → expected {{'999999999999': []}}, got {miss!r}",
        )
        mixed = c.ok("getReviewsOfCards", {"cards": [c1, 999999999999]})
        check(
            "ST-06b",
            set(mixed) == {str(c1), "999999999999"}
            and mixed["999999999999"] == []
            and len(mixed[str(c1)]) >= 1,
            f"mixed request → both keys expected; got {mixed!r}",
        )

        # ---------------------------------------------------------------- ST-07 getLatestReviewID happy
        # Spec: ST-07 — getLatestReviewID happy {deck:"Stats"} → int > 0 AND == max row id from ST-01
        #       (cross-check).
        lid = c.ok("getLatestReviewID", {"deck": "Stats"})
        check("ST-07a", isinstance(lid, int) and lid > 0, f"expected int > 0, got {lid!r}")
        check("ST-07b", lid == max_id, f"expected {max_id} (max row id from ST-01), got {lid}")

        # ---------------------------------------------------------------- ST-08 getLatestReviewID empty deck
        # Spec: ST-08 — getLatestReviewID empty deck fresh deck Empty (create it) → 0.
        c.create_deck("Empty")
        lid_empty = c.ok("getLatestReviewID", {"deck": "Empty"})
        check("ST-08", lid_empty == 0, f"fresh deck 'Empty' → expected 0, got {lid_empty!r}")

        # ---------------------------------------------------------------- ST-09 getLatestReviewID unknown deck
        # Spec: ST-09 — getLatestReviewID unknown deck {deck:"Ghost2"} → 0 + deck created (record; parity
        #       quirk as ST-03).
        lid_ghost = c.ok("getLatestReviewID", {"deck": "Ghost2"})
        check("ST-09a", lid_ghost == 0, f"unknown deck → expected 0, got {lid_ghost!r}")
        names = c.ok("deckNames")
        check(
            "ST-09b",
            "Ghost2" in names,
            f"'Ghost2' must appear in deckNames after getLatestReviewID; deckNames={names}",
        )
        record(
            "ST-09c",
            "parity quirk confirmed: getLatestReviewID with an unknown deck CREATES the deck (decks.id() side effect) — same as ST-03",
        )
        names_before = c.ok("deckNames")
        status, body = c.request("getLatestReviewID", {})
        names_after = c.ok("deckNames")
        created = sorted(set(names_after) - set(names_before))
        # P3-7 fixed contract: deck is required. Previously the "" default
        # made anki normalize and CREATE a deck named "blank"; a missing
        # param is now a clean validation error and no deck is created.
        check(
            "ST-09d",
            status == 200
            and isinstance(body.get("error"), str)
            and "Field required" in body.get("error", "")
            and not created,
            f"missing deck must be a validation error with no deck created; got HTTP {status} "
            f"result={body.get('result')!r} error={body.get('error')!r}; decks created: {created}",
        )

        # ---------------------------------------------------------------- ST-10 getNumCardsReviewedToday
        # Spec: ST-10 — getNumCardsReviewedToday ≥ 2 (the two answers) and ≤ total revlog rows. Record
        #       value.
        # The count is collection-global; when suites share one container
        # this includes other suites' reviews, so assert the suite's own
        # contribution (>= 2) rather than an exact count.
        total_before = len(rows)
        today = c.ok("getNumCardsReviewedToday")
        check(
            "ST-10a",
            isinstance(today, int) and today >= 2,
            f"expected >= 2 reviews today (this suite answered 2; the count is collection-global "
            f"and may include other suites' reviews on a shared container); got {today!r}",
        )
        record(
            "ST-10b",
            f"getNumCardsReviewedToday = {today} (fixture answered 2 cards; revlog rows so far: {total_before})",
        )

        # ---------------------------------------------------------------- ST-11 getNumCardsReviewedByDay
        # Spec: ST-11 — getNumCardsReviewedByDay list of [day, count] pairs, day matches
        #       \d{4}-\d{2}-\d{2}, newest day first, one entry has count ≥ 2. Record list.
        by_day = c.ok("getNumCardsReviewedByDay")
        shape_ok = (
            isinstance(by_day, list)
            and len(by_day) >= 1
            and all(
                isinstance(p, list)
                and len(p) == 2
                and isinstance(p[0], str)
                and DAY_RE.fullmatch(p[0])
                and isinstance(p[1], int)
                for p in by_day
            )
        )
        check(
            "ST-11a",
            shape_ok,
            f"list of [day, count] pairs with YYYY-MM-DD days expected; got {by_day!r}",
        )
        days = [p[0] for p in by_day]
        check(
            "ST-11b", days == sorted(days, reverse=True), f"newest day first expected; got {days}"
        )
        check(
            "ST-11c",
            any(p[1] >= 2 for p in by_day),
            f"one entry ≥ 2 expected (this suite answered 2; totals are collection-global "
            f"on a shared container); got {by_day!r}",
        )
        record("ST-11d", f"getNumCardsReviewedByDay = {by_day}")

        # ---------------------------------------------------------------- ST-12 insertReviews happy
        # Spec: ST-12 — insertReviews happy row = [<now_ms>, c2, 0, 2, 3, 1, 2500, 1500, 2] (9 ints) →
        #       result null; getReviewsOfCards [c2] includes a row with ease==2, ivl==3, factor==2500 (the
        #       inserted one).
        now_ms = int(time.time() * 1000)
        ins_row = [now_ms, c2, 0, 2, 3, 1, 2500, 1500, 2]
        c2_before = c.ok("getReviewsOfCards", {"cards": [c2]})[str(c2)]
        status, body = c.request("insertReviews", {"reviews": [ins_row]})
        check(
            "ST-12a",
            status == 200 and body == {"result": None, "error": None},
            f"expected result null + error null, status={status}, body={body!r}",
        )
        c2_after = c.ok("getReviewsOfCards", {"cards": [c2]})[str(c2)]
        inserted = [
            r
            for r in c2_after
            if r["id"] == now_ms and r["ease"] == 2 and r["ivl"] == 3 and r["factor"] == 2500
        ]
        check(
            "ST-12b",
            len(c2_after) == len(c2_before) + 1 and len(inserted) == 1,
            f"row {ins_row} must appear in getReviewsOfCards({c2}); before={len(c2_before)} after={len(c2_after)} match={inserted}",
        )
        record("ST-12c", f"inserted row readable back: {inserted}")

        # snapshot used by ST-13/14/16 (nothing must change after failed inserts)
        snap = c.ok("getReviewsOfCards", {"cards": [c1, c2]})
        day_sum = sum(p[1] for p in c.ok("getNumCardsReviewedByDay"))

        # ---------------------------------------------------------------- ST-13 insertReviews wrong length
        # Spec: ST-13 — insertReviews wrong length [1,2,3,4,5,6,7,8] (8) → error envelope containing each
        #       review row must have 9 elements, got 8; verify row NOT inserted (revlog count unchanged
        #       via getReviewsOfCards).
        err = c.err("insertReviews", {"reviews": [[1, 2, 3, 4, 5, 6, 7, 8]]})
        check("ST-13a", "each review row must have 9 elements, got 8" in err, f"error: {err!r}")
        snap2 = c.ok("getReviewsOfCards", {"cards": [c1, c2]})
        day_sum2 = sum(p[1] for p in c.ok("getNumCardsReviewedByDay"))
        check(
            "ST-13b",
            snap2 == snap and day_sum2 == day_sum,
            f"nothing must be inserted; reviews changed: {snap2 != snap}; global revlog count {day_sum} → {day_sum2}",
        )

        # ---------------------------------------------------------------- ST-14 insertReviews all-or-nothing
        # Spec: ST-14 — insertReviews multiple rows all-or-nothing [[row_ok_9], [bad_8]] → refused with
        #       the 9-element message; row_ok NOT inserted (validation precedes any insert).
        row_ok = [now_ms + 1, c2, 0, 4, 3, 1, 2500, 1500, 2]
        err = c.err("insertReviews", {"reviews": [row_ok, [1, 2, 3, 4, 5, 6, 7, 8]]})
        check("ST-14a", "each review row must have 9 elements, got 8" in err, f"error: {err!r}")
        c2_rows = c.ok("getReviewsOfCards", {"cards": [c2]})[str(c2)]
        leaked = [r for r in c2_rows if r["id"] == now_ms + 1]
        day_sum3 = sum(p[1] for p in c.ok("getNumCardsReviewedByDay"))
        check(
            "ST-14b",
            not leaked
            and day_sum3 == day_sum
            and c.ok("getReviewsOfCards", {"cards": [c1, c2]}) == snap,
            f"valid first row must NOT be inserted (validation precedes any insert); leaked={leaked}; global count {day_sum} → {day_sum3}",
        )
        record(
            "ST-14c",
            "all-or-nothing confirmed: the valid first row was refused together with the malformed second row",
        )

        # ---------------------------------------------------------------- ST-15 insertReviews empty list
        # Spec: ST-15 — insertReviews empty list → null, no change.
        status, body = c.request("insertReviews", {"reviews": []})
        check(
            "ST-15a",
            status == 200 and body == {"result": None, "error": None},
            f"expected result null + error null; status={status}, body={body!r}",
        )
        check(
            "ST-15b",
            c.ok("getReviewsOfCards", {"cards": [c1, c2]}) == snap,
            "empty list must leave the revlog unchanged",
        )

        # ---------------------------------------------------------------- ST-16 insertReviews non-integer element
        # Spec: ST-16 — insertReviews non-integer element [[1, "x", ...]] → pydantic error envelope;
        #       nothing inserted.
        err = c.err("insertReviews", {"reviews": [[1, "x", 3, 4, 5, 6, 7, 8, 9]]})
        check(
            "ST-16a",
            "integer" in err.lower() and "InsertReviewsParams" in err,
            f"expected pydantic error envelope about an invalid integer; got {err!r}",
        )
        day_sum4 = sum(p[1] for p in c.ok("getNumCardsReviewedByDay"))
        check(
            "ST-16b",
            day_sum4 == day_sum and c.ok("getReviewsOfCards", {"cards": [c1, c2]}) == snap,
            f"nothing must be inserted; global revlog count {day_sum} → {day_sum4}",
        )

        # ---------------------------------------------------------------- ST-17 getDeckStats happy
        # Spec: ST-17 — getDeckStats happy {decks:["Stats"]} → dict keyed by deck id (JSON stringifies int
        #       keys — assert the key equals str(deckId)); entry == {deck_id, name:"Stats", new_count,
        #       learn_count, review_count, total_in_deck} with snake_case keys; total_in_deck == 2 (2
        #       cards directly + aggregation includes child: verify total_in_deck == 3 if it counts
        #       descendants — record exact; upstream deckStatsToJson aggregates descendants: expect
        #       total_in_deck 3, counts include child's card).
        deck_id = c.create_deck("Stats")  # idempotent: returns the existing id
        stats = c.ok("getDeckStats", {"decks": ["Stats"]})
        check(
            "ST-17a",
            isinstance(stats, dict) and set(stats) == {str(deck_id)},
            f"result must be keyed by str(deckId) == {deck_id}; got keys {list(stats)!r}",
        )
        entry = stats[str(deck_id)]
        # P2-6 fixed contract: upstream's total_in_deck (direct cards only)
        # plus the aggregate total_including_children.
        entry_keys = {
            "deck_id",
            "name",
            "new_count",
            "learn_count",
            "review_count",
            "total_in_deck",
            "total_including_children",
        }
        check(
            "ST-17b",
            set(entry) == entry_keys,
            f"expected snake_case keys {sorted(entry_keys)}; got {sorted(entry)}",
        )
        check(
            "ST-17c",
            entry["name"] == "Stats" and entry["deck_id"] == deck_id,
            f"expected name 'Stats' and deck_id {deck_id}; got name={entry.get('name')!r} deck_id={entry.get('deck_id')!r}",
        )
        numeric_ok = all(isinstance(entry[k], int) for k in entry_keys - {"name"})
        check("ST-17d", numeric_ok, f"all count fields must be ints; entry={entry!r}")
        check(
            "ST-17e",
            entry["total_in_deck"] == 2,
            f"total_in_deck counts DIRECT cards only (upstream parity); got {entry['total_in_deck']}",
        )
        check(
            "ST-17e2",
            entry["total_including_children"] == 3,
            f"total_including_children aggregates descendants (2 in Stats + 1 child); got {entry.get('total_including_children')}",
        )
        due_sum = entry["new_count"] + entry["learn_count"] + entry["review_count"]
        check(
            "ST-17f",
            due_sum >= 2 and entry["new_count"] >= 1,
            f"due counts must include the child deck's new card; entry={entry!r}",
        )

        # ---------------------------------------------------------------- ST-18 getDeckStats child
        # Spec: ST-18 — getDeckStats child {decks:["Stats::Child"]} → its own entry with total_in_deck ==
        #       1.
        child_id = c.create_deck("Stats::Child")
        child_stats = c.ok("getDeckStats", {"decks": ["Stats::Child"]})
        check(
            "ST-18a",
            isinstance(child_stats, dict) and set(child_stats) == {str(child_id)},
            f"expected single key str({child_id}); got {list(child_stats)!r}",
        )
        centry = child_stats[str(child_id)]
        check("ST-18b", centry["total_in_deck"] == 1, f"Stats::Child holds 1 card; got {centry!r}")
        record(
            "ST-18c",
            f"getDeckStats(['Stats::Child']) entry = {centry}; note the 'name' field is the LEAF name "
            f"({centry.get('name')!r}), not the full path 'Stats::Child' — anki DeckTreeNode leaf naming (upstream parity)",
        )

        # ---------------------------------------------------------------- ST-19 getDeckStats unknown deck
        # Spec: ST-19 — getDeckStats unknown deck (parity quirk) {decks:["GhostStats"]} → deck created in
        #       deckNames (record) and result contains entry with zero counts (or empty — record which).
        ghost_stats = c.ok("getDeckStats", {"decks": ["GhostStats"]})
        names = c.ok("deckNames")
        check(
            "ST-19a",
            "GhostStats" in names,
            f"'GhostStats' must appear in deckNames after getDeckStats; deckNames={names}",
        )
        has_zero_entry = (
            isinstance(ghost_stats, dict)
            and len(ghost_stats) == 1
            and next(iter(ghost_stats)).isdigit()
            and all(v["total_in_deck"] == 0 and v["new_count"] == 0 for v in ghost_stats.values())
        )
        check(
            "ST-19b",
            has_zero_entry,
            f"expected a zero-count entry for the created deck; got {ghost_stats!r}",
        )
        record(
            "ST-19c",
            f"parity quirk confirmed: getDeckStats with an unknown deck CREATES it and returns a zero-count entry keyed by the new deck id: {ghost_stats}",
        )

        # ---------------------------------------------------------------- ST-20 getCollectionStatsHTML whole=true
        # Spec: ST-20 — getCollectionStatsHTML whole=true non-empty HTML string containing <html or
        #       <!doctype (case-insensitive) and some visible text (e.g. "Today"). Record length.
        html = c.ok("getCollectionStatsHTML", {"wholeCollection": True})
        check(
            "ST-20a",
            isinstance(html, str) and len(html) > 0 and "Today" in html,
            f"expected non-empty HTML with visible text; type={type(html).__name__} len={len(html) if isinstance(html, str) else 'n/a'}",
        )
        low = html.lower()
        # Decided contract (E2E P3-16): anki 26.8's stats.report() returns a
        # <center> fragment, not a full document — same as upstream and the
        # commit's own unit test (startswith("<center")).
        check(
            "ST-20b",
            "<html" in low or "<!doctype" in low or low.startswith("<center"),
            f"expected an HTML fragment (anki 26.8 emits a <center> fragment); report starts with {html[:40]!r}",
        )
        record(
            "ST-20c",
            f"len={len(html)}; starts {html[:40]!r}, ends ...{html[-60:]!r}; the report is anki's stats.report() "
            f"centered fragment (matches the commit's unit test expectation startswith('<center')), not a full HTML document",
        )

        # ---------------------------------------------------------------- ST-21 getCollectionStatsHTML whole=false
        # Spec: ST-21 — getCollectionStatsHTML whole=false still HTML; record.
        html2 = c.ok("getCollectionStatsHTML", {"wholeCollection": False})
        check(
            "ST-21a",
            isinstance(html2, str) and len(html2) > 0 and "Today" in html2,
            f"expected non-empty HTML; type={type(html2).__name__} len={len(html2) if isinstance(html2, str) else 'n/a'}",
        )
        record(
            "ST-21b",
            f"wholeCollection=false → len={len(html2)}; contains 'whole collection' text: {'whole collection' in html2.lower()}",
        )

        # ---------------------------------------------------------------- ST-22 bad param type (pydantic coercion)
        # Spec: ST-22 — bad param type {wholeCollection:"yes"} → record (pydantic bool coercion of "yes"
        #       fails? error envelope?). OBS.
        status, body = c.request("getCollectionStatsHTML", {"wholeCollection": "yes"})
        if body.get("error") is None and isinstance(body.get("result"), str):
            record(
                "ST-22",
                f"wholeCollection='yes' (string) is coerced to True by pydantic (lax bool coercion) and accepted with a success envelope: result=HTML str len={len(body['result'])}, error=null",
            )
        else:
            record(
                "ST-22",
                f"wholeCollection='yes' → status={status}, result null: {body.get('result') is None}, error: {body.get('error')!r}",
            )

        # ---------------------------------------------------------------- ST-23 envelope / legacy / resilience (C1-C5)
        # Spec: ST-23 — envelope/legacy + resilience per C2-C5; verify /health after the error cases and
        #       that revlog reads still work after insertReviews failures.
        # C1: actions also respond on POST /
        status, body = c.request("cardReviews", {"deck": "Stats", "startID": 0}, path="/")
        check(
            "ST-23c1",
            status == 200
            and isinstance(body, dict)
            and body.get("error") is None
            and isinstance(body.get("result"), list),
            f"POST / spot-check: status={status}, body={str(body)[:120]}",
        )
        # C2: exact success envelope on POST /api
        status, body = c.request("cardReviews", {"deck": "Stats", "startID": 0})
        check(
            "ST-23c2",
            status == 200
            and set(body) == {"result", "error"}
            and body["error"] is None
            and isinstance(body["result"], list),
            f"v6 success envelope {{result, error: null}} expected; got status={status}, keys={list(body) if isinstance(body, dict) else body!r}",
        )
        # C3: unknown action → HTTP 200 error envelope (c.err asserts status 200 + result null)
        err = c.err("noSuchAction")
        check("ST-23c3", "Unsupported action" in err, f"unknown action → error: {err!r}")
        # C4: legacy versions → bare result, no envelope
        status, bare = c.request("cardReviews", {"deck": "Stats", "startID": 0}, version=4)
        check(
            "ST-23c4a",
            status == 200 and isinstance(bare, list) and len(bare) >= 1,
            f"version=4 must return the bare result (no envelope); got status={status}, body type={type(bare).__name__}",
        )
        status, bare2 = c.raw_post({"action": "getLatestReviewID", "params": {"deck": "Stats"}})
        check(
            "ST-23c4b",
            status == 200 and isinstance(bare2, int),
            f"missing version (defaults to 4) must return the bare result; got status={status}, body={bare2!r}",
        )
        status, legacy_err = c.raw_post({"action": "cardReviews", "version": 4, "params": {}})
        record(
            "ST-23c4c",
            f"legacy v4 + client error → error envelope regardless of version: status={status}, body={legacy_err!r}",
        )
        # C5: resilience — health after all error cases; revlog reads still work after insertReviews failures
        hstatus, _ = c.get("/health")
        check("ST-23c5a", hstatus == 200, f"GET /health after error cases → {hstatus}")
        rows_after = c.ok("cardReviews", {"deck": "Stats", "startID": 0})
        check(
            "ST-23c5b",
            len(rows_after) >= 2 and all(isinstance(r, list) and len(r) == 9 for r in rows_after),
            f"revlog reads still work after insertReviews failures; got {len(rows_after)} rows",
        )
        latest = c.ok("getLatestReviewID", {"deck": "Stats"})
        check(
            "ST-23c5c",
            isinstance(latest, int) and latest == max(r[0] for r in rows_after),
            f"getLatestReviewID consistent with cardReviews rows: latest={latest}, max row id={max(r[0] for r in rows_after)}",
        )
        hstatus, _ = c.get("/health")
        check("ST-23c5d", hstatus == 200, f"final GET /health → {hstatus}")

    except (AssertionError, Exception) as exc:  # report instead of crashing
        check("FATAL", False, f"suite aborted by unexpected exception: {type(exc).__name__}: {exc}")

    return summary()


if __name__ == "__main__":
    sys.exit(main())
