# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-10-23

### Added
- 43 AnkiConnect actions, bringing the server from 48 to **91/110 upstream
  actions** (94 total with this server's extras) in six milestone clusters
  (`6bf2e7e`, `b92a7d6`, `0d584e2`, `215a7d0`, `5e17e9e`, `ba5c3fe`):
  - Scheduling: `answerCards`, `forgetCards`, `relearnCards`,
    `setEaseFactors`, `setSpecificValueOfCard`.
  - Reads: `canAddNote`, `cardsModTime`, `deckNameFromId`, `getEaseFactors`,
    `modelNameFromId`, `suspended`, `getMediaFilesNames`,
    `removeEmptyNotes` (removes unused note *types* — upstream quirk,
    documented).
  - Tags: `replaceTags`, `replaceTagsInAllNotes`, `clearUnusedTags`,
    `getNoteTags`, `updateNoteTags`.
  - Revlog & stats: `cardReviews`, `getReviewsOfCards`, `getLatestReviewID`,
    `getNumCardsReviewedToday`, `getNumCardsReviewedByDay`, `insertReviews`,
    `getDeckStats` (serves upstream's `total_in_deck` direct-count semantics
    plus this server's `total_including_children` aggregate),
    `getCollectionStatsHTML`.
  - Models: `modelFieldAdd`, `modelFieldRemove`, `modelFieldRename`,
    `modelFieldReposition`, `modelFieldSetFont`, `modelFieldSetFontSize`,
    `modelFieldSetDescription`, `modelFieldDescriptions`, `modelFieldFonts`,
    `modelTemplateAdd`, `modelTemplateRemove`, `modelTemplateRename`,
    `modelTemplateReposition`, `findAndReplaceInModels`. `modelTemplateAdd`
    persists the update-existing path (upstream silently discards the
    change).
  - Meta: `apiReflect`, `reloadCollection` (documented no-op on anki 26.8),
    `requestPermission` (always granted on the headless server).
- `canAddNotesWithErrorDetail` action: batch-create notes and get per-note
  creation errors for invalid ones, with nothing persisted on failure
  (`8aa6d5d`, `3bd15a0`).
- `updateNote` action and `update_note` MCP tool: update the fields and/or
  tags of an existing note in one call (fields are patched, tags replace the
  existing set; at least one of the two is required, mirroring upstream)
  (`f2b0034`).
- GET banner: `GET /` and `GET /api` serve a server/action-count banner
  (`15a312d`).
- README "Supported actions" and "Not supported (headless server)" sections
  documenting the full parity surface, including the 19 intentionally
  unsupported upstream actions (17 `gui*`, 2 profile).
- Black-box E2E suite under `e2e/`: seven revision-agnostic, API-only suites
  (stdlib-only client, every case's criteria inline), `run_all.py` runner,
  and the sync topology recipe in the sync suite docstring; 322 single-server
  checks plus 33 sync checks against a local `anki.syncserver` (`5fff9e3`).

### Changed
- `sync` now seeds a fresh sync account with a **full upload** when the
  remote collection is empty (anki's `FULL_UPLOAD` requirement, which by
  protocol construction has no remote data to lose); `SyncResult` outcomes
  include the new `uploaded` case, and the MCP `sync` tool documents the
  new semantics (`fe0292e`).
- Sync and media-sync failures (bad credentials, unreachable endpoint,
  concurrent lock) return upstream-style HTTP 200 error envelopes instead of
  HTTP 500, log at WARNING without tracebacks, and auth errors name the
  required environment variables (`6925ad6`, `cb2dab6`).
- `multi` reply shapes match upstream exactly: per-entry failures are always
  `{"result": null, "error": "..."}` and per-entry successes follow the
  entry's own `version` semantics (`cb8e4c5`).
- `cardsInfo` returns upstream's full card shape (`ord`, `fieldOrder`,
  `css`, `type`, `queue`, `due`, `reps`, `lapses`, `left`, `mod`, and
  scheduling fields; `factor` is the wire name, `ease` kept as a legacy
  alias) (`69b6e12`).
- `createModel` returns the created model object instead of null — upstream
  parity (`fbde96d`).
- `syncStatus` omits anki 26.8's always-empty `server`/`status` keys
  (`cb2dab6`).
- `getLatestReviewID` requires `deck` — the previous `""` default silently
  created a deck named "blank" (`cb2dab6`).
- POST endpoints use `response_model=None` so JSON-legal int-keyed objects
  (upstream's dict-shaped `getDeckStats` / `getReviewsOfCards` results)
  serialize exactly like upstream (`215a7d0`).
- Client-facing strictness validated by tests and documented in code:
  `answerCards` validates the whole batch before applying anything (no
  partial answers), `insertReviews` uses parameterized SQL and validates
  9-element rows, `setEaseFactors` reports a clean length-mismatch error,
  and missing model/field/template/deck/note/card errors use anki's exact
  upstream messages (`2d87401`).

### Fixed
- `getMediaFilesNames` globs are confined to the media directory:
  absolute or traversal patterns (`/etc/*`, `../etc/*`) no longer list
  arbitrary container paths (`590f2c6`).
- Removing a model's last template returns a clean client error envelope
  instead of HTTP 500 (`6d8a19b`).
- Invalid client template data raises anki's `CardTypeError` into the HTTP
  200 error envelope instead of a 500 (`5e17e9e`).
- Config-defaults unit test no longer fails inside `COLLECTION_PATH`-only
  (Docker) deployments; the container runs the full 304-test unit suite
  green (`15a312d`).
- CI: buildx GHA cache export is non-fatal — PR-triggered `workflow_run`
  jobs get read-only Actions cache access and `ignore-error=true` keeps the
  Docker build green (`776bed5`).

## [0.4.0] - 2026-09-27

### Added
- `storeMediaFile` accepts `url` (server-side download, httpx with redirects
  and a 30s timeout) and `path` (server-side file) in addition to base64
  `data`; precedence `data` > `url` > `path`, mirroring upstream Anki-Connect.
  Missing source, unreachable URL, or unreadable path raise client-facing
  errors. The MCP `store_media_file` tool exposes the same options.

### Fixed
- Return the bare result with no `{result, error}` envelope for requests at
  version ≤4 (missing `version` now defaults to 4), matching the AnkiConnect
  spec used by legacy clients such as Yomitan.

## [0.3.1] - 2026-09-27

### Fixed
- `retrieveMediaFile` / `deleteMediaFile`: replace the removed
  `MediaManager.read_data` (anki 26.x) with a direct disk read of the media
  dir, and route deletions through `trash_files` as upstream Anki-Connect
  does (`1fd7779`).
- Sanitize media filenames (basename + NFC + illegal-char stripping) for
  retrieve/delete, closing a path-traversal vector in `retrieveMediaFile`
  (`1fd7779`).

## [0.3.0] - 2026-08-05

### Added
- MCP server instructions and per-tool safety annotations (read-only,
  idempotent, additive, destructive) so AI assistants can reason about
  mutating operations (`642f9dc`).
- Serve the AnkiConnect API at `POST /` in addition to `/api` (`6a2a5f7`).

### Changed
- Resolve sync requirements via `SyncCollectionResponse` enums and return a
  structured `SyncResult` describing the collection outcome, media counters,
  and any server message (`98a949b`).
- Wire Pydantic models / TypedDict input shapes into every handler with a
  registry-based dispatch (`95021d1`, `c64d9f9`, `723e44b`).
- Route blocking `col.*` calls through `asyncio.to_thread` so the FastAPI
  event loop stays responsive (`5ec1a4d`).
- Remove the global wrapper singleton in favor of `app.state` for FastAPI
  (`6a47cf9`).
- Make `cli.main` testable via an `argv` parameter (`a201a8b`).

### Fixed
- `updateNoteFields` silently succeeded for missing/nonexistent note ids;
  it now raises a clear error (`5d2a021`).
- Distinguish validation errors (HTTP 200 with `error`) from server errors
  (HTTP 500) in the API layer (`11c0437`).
- Dockerfile `CMD` referenced a non-existent `server` subcommand (`bcf8753`).
- Validate `COLLECTION_PATH` instead of failing opaquely inside
  `Collection()` (`2a57e68`).
- `findNotes` / `findCards` with an empty query returned the entire
  collection (`ff1a2ef`).
- `multi` aborted the whole batch when one sub-action failed (`c644819`).
- `suspend` returned `False` when no cards were newly suspended (`20447f5`).
- `getIntervals` `last_interval` reported the lapse count instead of the
  previous interval (`bea9ec5`).
- `areSuspended` crashed on missing card ids (`4f66f16`).
- Restore the collection safely when a sync fails (`5944473`).
- Actually wait for media sync completion in `syncMedia` (`7e97720`).
- Reject concurrent AnkiWeb syncs with a `_sync_lock` (`3f22ed6`).
- Handle the `required=2` sync action (`90bf4fa`).

### Tests
- Cover `model_fields_on_templates`, `syncStatus`, and `app_lifespan`
  (`5a57e6a`).
- Cover `collection_generation` increments across sync paths (`34aaa19`).
- Isolate the test working directory to prevent `.env` credential leak
  (`743a0d0`).
- Use `monkeypatch` instead of mutating global config (`b173322`).

### CI / Tooling
- Add quality gates (ruff + pyright), strict typing, and tightened
  dependency floors (`d5d700d`, `c3abd20`).
- Separate Docker build and description update jobs (`b5cd41a`).

## [0.2.0] - 2026-04-23

### Added
- Unified CLI with `api` and `mcp` subcommands (`69b5f10`).
- Dockerfile for containerized deployment (`e66e89f`).
- Mount FastMCP to FastAPI at the `/mcp` endpoint (`d7740bd`).
- Move source files to the `src/anki_connect_server` package layout
  (`9ed6478`).
- Add credentials to all `uvx` usage examples (`9ef2005`, `1b04bd8`).

### Changed
- Move dev dependencies to `[dependency-groups]` (`10fd09b`).

### Fixed
- Rename `main` to `run` for the MCP server CLI entry point (`7b1f0d0`).
- Add a `run` function alias for the MCP server CLI entry point (`d090a88`).

## [0.1.3] - 2026-03-25

### Fixed
- CLI entry point fixes for PyPI release.

## [0.1.2] - 2026-03-24

### Fixed
- Rename `main` to `run` for the MCP server CLI entry point (`7b1f0d0`).
- Add a `run` function alias for the MCP server CLI entry point (`d090a88`).

## [0.1.1] - 2026-03-20

### Fixed
- Initial CLI entry point fixes.

## [0.1.0] - 2026-03-15

### Added
- Initial release of the headless AnkiConnect-compatible REST API server
  with AnkiWeb sync support and MCP server integration.