# E2E black-box test suite for anki-connect-server

Black-box suites that verify the running server **only through its HTTP
API** — no imports of the server package, no direct collection/DB
access, no AnkiWeb credentials. They are revision-agnostic: build a
container from any revision (a commit, a PR head, a dirty working tree)
and point the suites at it.

## Layout

- `anki_client.py` — stdlib-only HTTP client + PASS/FAIL/OBS ledger.
- `suite_<topic>.py` — one runnable suite per action cluster:
  | Suite | Covers |
  |---|---|
  | `suite_scheduling.py` | `answerCards`, `forgetCards`, `relearnCards`, `setEaseFactors`, `setSpecificValueOfCard` |
  | `suite_reads.py` | `canAddNote`, `cardsModTime`, `deckNameFromId`, `getEaseFactors`, `modelNameFromId`, `suspended`, `getMediaFilesNames`, `removeEmptyNotes` |
  | `suite_tags.py` | `replaceTags`, `replaceTagsInAllNotes`, `clearUnusedTags`, `getNoteTags`, `updateNoteTags` |
  | `suite_revlog_stats.py` | `cardReviews`, `getReviewsOfCards`, `getLatestReviewID`, review counts, `insertReviews`, `getDeckStats`, `getCollectionStatsHTML` |
  | `suite_models.py` | `modelField*`, `modelTemplate*`, `findAndReplaceInModels` |
  | `suite_meta.py` | `apiReflect`, `reloadCollection`, `requestPermission` + README/action-registry parity |
  | `suite_sync.py` | `sync`/`syncStatus`/`syncMedia` end-to-end against a real local `anki.syncserver` (topology commands in its module docstring) |
- `run_all.py` — runs the six single-server suites sequentially against
  one server and aggregates the ledger totals.

Case docs are inline: every case banner in a suite carries a `# Spec:`
comment with its criteria (case IDs like `SC-01`, `RD-17`, `SY-10` are
stable references), and the module docstring describes the fixture the
suite builds through the API. The common criteria below (C1–C6) apply
to every suite.

## Running

```bash
# 1. Build an image from the revision under test and start a container
#    (fresh collection, no volumes, no AnkiWeb credentials):
podman build -t acs-e2e:test <checkout-dir-or-repo>
podman run -d --name acs-e2e-test -p 18799:8765 acs-e2e:test
curl http://localhost:18799/health   # wait for {"status":"healthy"}

# 2. All suites at once:
python3 e2e/run_all.py http://localhost:18799

# 2b. Or one suite at a time (each takes the base URL as argv[1]):
python3 e2e/suite_models.py http://localhost:18799

# 3. In-container unit tests (deployment-environment check):
podman exec acs-e2e-test uv run pytest tests/ -q
```

For a full regression pass, also run the sync suite with its own
three-server topology (commands in `suite_sync.py`'s docstring). The
suites are deterministic on a fresh container: compare outcomes with the
previous run — any behavioral difference is a regression. Review-count
assertions are relative by design when several suites share one
collection.

The suites create all fixture data through the API (decks, notes,
models, media). Running several suites against the same container is
supported — fixture names are disjoint — but a fresh container per run
keeps results deterministic; review-count assertions are relative by
design. `suite_meta.py` reads the repo `README.md` (path configurable
via argv[2]) to verify the documented action list against `apiReflect`.

## Common criteria (apply to every suite)

- **C1 transport**: every action responds on POST `/api` (spot-check `/` too).
- **C2 envelope (version 6)**: success → `{"result": <value>, "error": null}`.
- **C3 client errors**: unknown actions, invalid params, and missing entities
  → HTTP **200** with `{"result": null, "error": "<message>"}`. **Never a 500.**
  Any 500 on a client-caused error is a failure.
- **C4 legacy versions**: `version <= 4` (and missing version, which defaults to
  4) → bare result, no envelope.
- **C5 resilience**: after each failing case, `GET /health` is 200 and the
  server keeps serving (no wedged state).
- **C6 API-only**: tests never import `anki_connect_server` or `anki`, never
  read the collection file; all assertions are made through API responses.

## Reporting

Each suite prints one line per case — `[PASS]`, `[FAIL]`, or `[OBS]` for
exploratory observations — and a `TOTAL: X passed, Y failed, Z
observations` summary; the exit code is non-zero on failures. Failed
checks include the raw request and response in their detail line; grab
`podman logs <container>` if the server itself misbehaves.