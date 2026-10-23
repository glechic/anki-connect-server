# AnkiConnect Server

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/anki-connect-server.svg)](https://pypi.org/project/anki-connect-server/)
[![Docker](https://img.shields.io/docker/v/glechic/anki-connect-server)](https://hub.docker.com/r/glechic/anki-connect-server)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)

Headless AnkiConnect-compatible REST API server with AnkiWeb sync support and MCP server integration.

## ❓ Problem & Solution

**Problem:** Traditional AnkiConnect requires the Anki desktop app running, works only on localhost, and can't be deployed to servers.

**Solution:** This headless server provides direct collection access without Anki desktop, supports remote deployment, and includes automatic AnkiWeb sync.


## ✨ Features

- **Server Deployment** - Run on VPS, Raspberry Pi, or cloud without GUI
- **AI Integration** - MCP server for AI assistant access to your cards
- **Full AnkiConnect API Compatibility** - Version 6 API with all standard actions
- **Headless Operation** - No Qt/GUI required, perfect for servers and containers
- **AnkiWeb Sync** - Automatic synchronization with AnkiWeb (optional)
- **MCP Server** - Model Context Protocol integration for AI assistants

## 📋 Table of Contents

- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Reference](#-api-reference)
- [MCP Server](#-mcp-server)
- [Docker](#-docker)

## ⚙️ Configuration

Set environment variables before running the server:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANKICONNECT_COLLECTION_PATH` | No | temp path | Path to your `.anki2` collection file |
| `ANKICONNECT_PORT` | No | `8765` | Server port |
| `ANKICONNECT_BIND` | No | `127.0.0.1` | Bind address (use `0.0.0.0` for external access) |
| `ANKICONNECT_ANKIWEB_USER` | No | - | AnkiWeb username (required for sync) |
| `ANKICONNECT_ANKIWEB_PASS` | No | - | AnkiWeb password (required for sync) |
| `ANKICONNECT_ANKIWEB_URL` | No | - | Custom sync server URL (optional) |

### Example `.env` File

```bash
# Required: Path to your Anki collection
ANKICONNECT_COLLECTION_PATH=/path/to/collection.anki2

# Optional: Server configuration
ANKICONNECT_PORT=8765
ANKICONNECT_BIND=127.0.0.1

# Optional: AnkiWeb sync credentials
ANKICONNECT_ANKIWEB_USER=your@email.com
ANKICONNECT_ANKIWEB_PASS=your_password

# Optional: Custom sync server
ANKICONNECT_ANKIWEB_URL=https://your-sync-server.com
```

## 🚀 Usage

### Quick Start with uvx (No Installation)

```bash
# Run the API server
ANKICONNECT_COLLECTION_PATH=/path/to/collection.anki2 \
ANKICONNECT_ANKIWEB_USER=your@email.com \
ANKICONNECT_ANKIWEB_PASS=your_password \
uvx anki-connect-server api

# Run the MCP server
ANKICONNECT_COLLECTION_PATH=/path/to/collection.anki2 \
ANKICONNECT_ANKIWEB_USER=your@email.com \
ANKICONNECT_ANKIWEB_PASS=your_password \
uvx anki-connect-server mcp
```

## 📚 API Reference

The server exposes a single POST endpoint at `/api` that accepts AnkiConnect-style JSON requests.

### Request Format

```json
{
  "action": "actionName",
  "version": 6,
  "params": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

### Response Format

```json
{
  "result": <action_result>,
  "error": null
}
```

On error:

```json
{
  "result": null,
  "error": "Error message"
}
```

### Examples

#### Get Deck Names

```bash
curl -X POST http://localhost:8765/api \
  -H "Content-Type: application/json" \
  -d '{"action": "deckNames", "version": 6}'
```

#### Create a Deck

```bash
curl -X POST http://localhost:8765/api \
  -H "Content-Type: application/json" \
  -d '{"action": "createDeck", "version": 6, "params": {"deck": "My New Deck"}}'
```

#### Add a Note

```bash
curl -X POST http://localhost:8765/api \
  -H "Content-Type: application/json" \
  -d '{
    "action": "addNote",
    "version": 6,
    "params": {
      "note": {
        "deckName": "Default",
        "modelName": "Basic",
        "fields": {
          "Front": "Hello",
          "Back": "World"
        },
        "tags": ["api"]
      }
    }
  }'
```

#### Store Media from a URL (no base64 needed)

`storeMediaFile` accepts base64 `data`, a `url` to download, or a server-side `path`.
When several are given, `data` takes precedence over `url`, which takes precedence over `path`.

```bash
# Download audio from a dictionary on the server side (~100-byte request)
curl -X POST http://localhost:8765/api \
  -H "Content-Type: application/json" \
  -d '{
    "action": "storeMediaFile",
    "version": 6,
    "params": {
      "filename": "sky_us.ogg",
      "url": "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-sky.ogg"
    }
  }'
```

```bash
# Copy a file already visible to the server (e.g. a mounted volume)
curl -X POST http://localhost:8765/api \
  -H "Content-Type: application/json" \
  -d '{
    "action": "storeMediaFile",
    "version": 6,
    "params": {"filename": "sky.mp3", "path": "/data/media-in/sky.mp3"}
  }'
```

Then reference the stored file in a note field with `[sound:sky_us.ogg]`.

#### Sync with AnkiWeb

```bash
curl -X POST http://localhost:8765/api \
  -H "Content-Type: application/json" \
  -d '{"action": "sync", "version": 6}'
```

#### Batch Multiple Actions

```bash
curl -X POST http://localhost:8765/api \
  -H "Content-Type: application/json" \
  -d '{
    "action": "multi",
    "version": 6,
    "params": {
      "actions": [
        {"action": "deckNames", "params": {}},
        {"action": "modelNames", "params": {}}
      ]
    }
  }'
```

### Supported Actions

#### Misc
- `version` - Get API version
- `sync` - Sync with AnkiWeb
- `syncStatus` - Get sync status (returns the sync requirement; `server`/`status` are included only when the sync backend provides them)
- `syncMedia` - Sync media only (bidirectional; runs independently of collection sync)
- `apiReflect` - Introspect the supported actions (scopes: ["actions"])
- `reloadCollection` - No-op on a headless server (anki's reset is deprecated and does nothing)
- `requestPermission` - Always granted (headless; no GUI prompt or CORS allowlist)
- `multi` - Execute multiple actions (each entry replies per its own `version`, like upstream: failures always `{"result": null, "error": "..."}`; successes are the bare value for version ≤ 4, or `{"result": ..., "error": null}` for version ≥ 5)
- `importPackage` - Import `.apkg` file
- `exportPackage` - Export deck to `.apkg`

#### Decks
- `deckNames` - Get all deck names
- `deckNamesAndIds` - Get deck names with IDs
- `deckNameFromId` - Get a deck name from its ID
- `createDeck` - Create a new deck
- `deleteDecks` - Delete decks
- `changeDeck` - Move cards to different deck
- `getDecks` - Get decks for cards
- `getDeckConfig` - Get deck configuration
- `saveDeckConfig` - Save deck configuration
- `setDeckConfigId` - Assign config to decks
- `cloneDeckConfigId` - Clone deck config
- `removeDeckConfigId` - Remove deck config

#### Models
- `modelNames` - Get all model names
- `modelNamesAndIds` - Get model names with IDs
- `modelNameFromId` - Get a model name from its ID
- `modelFieldNames` - Get field names for model
- `modelFieldsOnTemplates` - Get fields used in templates
- `createModel` - Create a new note model (returns the created model, like upstream)
- `modelTemplates` - Get card templates
- `modelStyling` - Get CSS styling
- `updateModelTemplates` - Update templates
- `updateModelStyling` - Update CSS
- `modelFieldAdd` - Add a field to a model (optionally positioned at an index)
- `modelFieldRemove` - Remove a field from a model (destroys that field's data in all notes)
- `modelFieldRename` - Rename a model field (anki 26.8 also rewrites the renamed field's references in templates on save)
- `modelFieldReposition` - Move a field to a new position
- `modelFieldSetFont` - Set a field's font
- `modelFieldSetFontSize` - Set a field's font size
- `modelFieldSetDescription` - Set a field's description
- `modelFieldDescriptions` - Get field descriptions
- `modelFieldFonts` - Get per-field font and size
- `modelTemplateAdd` - Add or update a card template
- `modelTemplateRemove` - Remove a card template (a model must keep at least one)
- `modelTemplateRename` - Rename a card template
- `modelTemplateReposition` - Move a card template to a new position
- `findAndReplaceInModels` - Find and replace text in templates/CSS across models (empty modelName = all models; replacements that would leave a dangling field reference are refused with a validation error — unlike upstream, broken templates are never persisted)

#### Notes
- `addNote` - Add a single note
- `addNotes` - Add multiple notes
- `canAddNote` - Check if a single note can be added
- `canAddNotes` - Check if notes can be added
- `canAddNotesWithErrorDetail` - Check whether notes can be added, with per-note error details
- `updateNoteFields` - Update note fields
- `updateNote` - Update note fields and/or tags in one call
- `findNotes` - Search for notes
- `notesInfo` - Get note details
- `deleteNotes` - Delete notes
- `removeEmptyNotes` - Remove unused note types (upstream parity: despite the name, removes note types with zero notes)
- `addTags` - Add tags to notes
- `removeTags` - Remove tags from notes
- `getTags` - Get all tags
- `replaceTags` - Replace a tag with another across the given notes
- `replaceTagsInAllNotes` - Replace a tag with another across all notes
- `clearUnusedTags` - Remove tags not used by any note
- `getNoteTags` - Get a single note's tags
- `updateNoteTags` - Replace all tags of a note (accepts a tag string or list; a string becomes one tag, but anki re-splits tags on whitespace when the note loads — prefer the list form)

#### Cards
- `findCards` - Search for cards
- `cardsToNotes` - Get note IDs from card IDs
- `cardsInfo` - Get card details (upstream's full shape: `factor` is the ease factor x10; `ease` is kept as a legacy alias)
- `cardsModTime` - Get card modification timestamps
- `suspend` - Suspend cards
- `unsuspend` - Unsuspend cards
- `areSuspended` - Check if cards are suspended
- `suspended` - Check if a single card is suspended
- `areDue` - Check if cards are due
- `getIntervals` - Get card intervals
- `answerCards` - Answer cards with a given ease (1=Again, 2=Hard, 3=Good, 4=Easy); returns a per-card success list; an invalid ease rejects the whole batch at validation time (upstream applies earlier answers first)
- `forgetCards` - Reset cards back to new, clearing all scheduling state
- `relearnCards` - Move cards into the relearning queue
- `setEaseFactors` - Set card ease factors (10x the ease percentage, e.g. 3100 = 310%)
- `getEaseFactors` - Get card ease factors (10x the ease percentage)
- `setSpecificValueOfCard` - Raw/dangerous: set arbitrary card fields directly (critical fields are refused unless `warning_check` is true)

#### Stats
- `cardReviews` - Get review log entries for a deck since a given review ID (unknown deck names are created, as upstream does)
- `getReviewsOfCards` - Get full review history per card
- `getLatestReviewID` - Get the newest review ID for a deck (deck required; unknown names are created, as upstream does)
- `getNumCardsReviewedToday` - Count reviews made today
- `getNumCardsReviewedByDay` - Count reviews grouped by day
- `insertReviews` - Raw review-log insertion (developer utility, rows of 9 integers)
- `getDeckStats` - Deck due counts by deck name (keys are deck IDs; due counts aggregate child decks, `total_in_deck` counts direct cards per upstream, `total_including_children` is the aggregated total; `name` is the deck's own name per anki's due tree)
- `getCollectionStatsHTML` - Full stats report as HTML

#### Media
- `getMediaDirPath` - Get media directory path
- `getMediaFilesNames` - List media file names matching a glob pattern (patterns are confined to the media directory; absolute paths and `..` are rejected)
- `storeMediaFile` - Store a media file (base64 `data`, `url`, or server-side `path`)
- `retrieveMediaFile` - Retrieve a media file
- `deleteMediaFile` - Delete a media file

#### Not supported (headless server)

These upstream AnkiConnect actions require the Anki desktop GUI or profile
manager and are intentionally not implemented:

- `getProfiles`, `loadProfile` - multi-profile support is an Anki desktop concept; this server serves a single collection via `ANKICONNECT_COLLECTION_PATH`
- `guiAddCards`, `guiAnswerCard`, `guiBrowse`, `guiCheckDatabase`, `guiCurrentCard`, `guiDeckBrowser`, `guiDeckOverview`, `guiDeckReview`, `guiEditNote`, `guiExitAnki`, `guiImportFile`, `guiReviewActive`, `guiSelectedNotes`, `guiShowAnswer`, `guiShowQuestion`, `guiStartCardTimer`, `guiUndo` - all `gui*` actions open or drive Anki desktop windows

## 🤖 MCP Server

The server includes a Model Context Protocol (MCP) integration for AI assistants.

### Starting the MCP Server

```bash
ANKICONNECT_COLLECTION_PATH=/path/to/collection.anki2 \
ANKICONNECT_ANKIWEB_USER=your@email.com \
ANKICONNECT_ANKIWEB_PASS=your_password \
uvx anki-connect-server mcp
```

### Transports: stdio vs http

The MCP server supports two transports via `--transport`:

| Transport | Flag | Behavior |
|-----------|------|----------|
| `stdio` (default) | `--transport stdio` | One process per client connection. The MCP client (e.g. Claude Desktop, Hermes) spawns a new process for each session. |
| `http` | `--transport http` | A single long-lived server holds the collection and serves all clients over HTTP. |

```bash
# stdio (default)
uvx anki-connect-server mcp

# http
uvx anki-connect-server mcp --transport http
```

### ⚠️ Concurrent MCP processes and the "already open" error

The Anki collection is a single-writer SQLite database: **only one process can hold the lock at a time.** The default `stdio` transport spawns a new process per client connection, so if your MCP client (Hermes, Claude Desktop, etc.) starts a new process before the previous one has exited, you will see:

```
anki.errors.DBError: Anki already open, or media currently syncing.
```

This is a **SQLite lock contention** error, not a media-sync issue — despite what the message says.

**Workarounds:**

1. **Use HTTP transport** (recommended for multi-client setups):
   ```bash
   uvx anki-connect-server mcp --transport http
   # Server runs on http://127.0.0.1:8765/mcp
   ```
   Configure your MCP client to connect to the HTTP endpoint instead of spawning a stdio process. Only one process holds the collection and serves all connections.

2. **Leave `ANKICONNECT_COLLECTION_PATH` unset.** When not configured, each process gets a random temp collection (`anki-connect-server-<random>.anki2`), so concurrent processes don't contend for the same file. Note: each process will have its own empty collection — set the path explicitly if you need a shared collection.

3. **Ensure only one process is running.** If you stick with stdio, make sure your MCP client kills the previous process before starting a new one.

### Available MCP Tools

- `get_deck_names` - Get all deck names
- `get_deck_names_and_ids` - Get decks with IDs
- `create_deck` - Create a new deck
- `delete_decks` - Delete decks
- `get_model_names` - Get all model names
- `get_model_field_names` - Get fields for a model
- `create_model` - Create a note model (fields + card templates)
- `model_add_field` / `model_remove_field` / `model_rename_field` / `model_reposition_field` - Manage model fields
- `update_note_fields` - Update fields of an existing note
- `add_note` - Add a new note
- `find_notes` - Search for notes
- `get_notes_info` - Get note details
- `delete_notes` - Delete notes
- `find_cards` - Search for cards
- `get_cards_info` - Get card details
- `suspend_cards` / `unsuspend_cards` - Manage card suspension
- `are_suspended` / `are_due` - Check card status
- `get_card_intervals` - Get card intervals
- `get_all_tags` - Get all tags
- `add_tags` / `remove_tags` - Manage tags
- `get_media_dir_path` - Get media directory
- `store_media_file` / `retrieve_media_file` / `delete_media_file` - Media operations (`store_media_file` accepts base64 `data`, `url`, or server-side `path`)
- `update_note` / `update_note_fields` - Edit note fields and/or tags
- `change_deck` - Move cards between decks
- `cards_to_notes` - Convert card IDs to note IDs
- `get_deck_config` - Get deck configuration
- `get_model_templates` / `get_model_styling` - Model customization
- `update_model_templates` / `update_model_styling` - Edit model templates/CSS
- `get_api_version` - Get API version
- `import_package` / `export_package` - Import/export decks
- `sync` / `sync_media` / `get_sync_status` - Sync operations

### Adding to Claude Desktop

**Option A — stdio (default, one process per session):**

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "anki-connect-server": {
      "command": "uvx",
      "args": ["anki-connect-server", "mcp"],
      "env": {
        "ANKICONNECT_COLLECTION_PATH": "/path/to/collection.anki2",
        "ANKICONNECT_ANKIWEB_USER": "your@email.com",
        "ANKICONNECT_ANKIWEB_PASS": "your_password"
      }
    }
  }
}
```

**Option B — http (single long-lived server, avoids lock contention):**

First start the HTTP server (e.g. as a systemd service or background process):

```bash
uvx anki-connect-server mcp --transport http
```

Then point your MCP client at `http://127.0.0.1:8765/mcp`.

## 🐳 Docker

### Using Pre-built Image

```bash
docker run -d \
  -p 8765:8765 \
  -v /path/to/collection.anki2:/data/collection.anki2 \
  -e ANKICONNECT_COLLECTION_PATH=/data/collection.anki2 \
  -e ANKICONNECT_ANKIWEB_USER=your@email.com \
  -e ANKICONNECT_ANKIWEB_PASS=your_password \
  --name anki-connect-server \
  glechic/anki-connect-server:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  anki-connect-server:
    image: glechic/anki-connect-server:latest
    ports:
      - "8765:8765"
    volumes:
      - ./collection.anki2:/data/collection.anki2
    environment:
      - ANKICONNECT_COLLECTION_PATH=/data/collection.anki2
      - ANKICONNECT_ANKIWEB_USER=${ANKIWEB_USER}
      - ANKICONNECT_ANKIWEB_PASS=${ANKIWEB_PASS}
    restart: unless-stopped
```

### Building from Source

```bash
docker build -t anki-connect-server .
```


