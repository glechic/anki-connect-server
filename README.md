# AnkiConnect Server

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/anki-connect-server.svg)](https://pypi.org/project/anki-connect-server/)
[![Docker](https://img.shields.io/docker/v/your-docker-username/anki-connect-server)](https://hub.docker.com/r/your-docker-username/anki-connect-server)
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
| `ANKI_COLLECTION_PATH` | **Yes** | - | Path to your `.anki21` collection file |
| `ANKICONNECT_PORT` | No | `8765` | Server port |
| `ANKICONNECT_BIND` | No | `127.0.0.1` | Bind address (use `0.0.0.0` for external access) |
| `ANKICONNECT_ANKIWEB_USER` | No | - | AnkiWeb username (required for sync) |
| `ANKICONNECT_ANKIWEB_PASS` | No | - | AnkiWeb password (required for sync) |
| `ANKIWEB_URL` | No | - | Custom sync server URL (optional) |
| `ANKICONNECT_FULL_UPLOAD` | No | `false` | Allow full upload on sync conflict |

### Example `.env` File

```bash
# Required: Path to your Anki collection
ANKI_COLLECTION_PATH=/path/to/collection.anki21

# Optional: Server configuration
ANKICONNECT_PORT=8765
ANKICONNECT_BIND=127.0.0.1

# Optional: AnkiWeb sync credentials
ANKICONNECT_ANKIWEB_USER=your@email.com
ANKICONNECT_ANKIWEB_PASS=your_password

# Optional: Custom sync server
ANKIWEB_URL=https://your-sync-server.com
```

## 🚀 Usage

### Quick Start with uvx (No Installation)

```bash
# Run the API server
ANKI_COLLECTION_PATH=/path/to/collection.anki21 \
ANKICONNECT_ANKIWEB_USER=your@email.com \
ANKICONNECT_ANKIWEB_PASS=your_password \
uvx anki-connect-server api

# Run the MCP server
ANKI_COLLECTION_PATH=/path/to/collection.anki21 \
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
- `syncStatus` - Get sync status
- `syncMedia` - Sync media only
- `multi` - Execute multiple actions
- `importPackage` - Import `.apkg` file
- `exportPackage` - Export deck to `.apkg`

#### Decks
- `deckNames` - Get all deck names
- `deckNamesAndIds` - Get deck names with IDs
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
- `modelFieldNames` - Get field names for model
- `modelFieldsOnTemplates` - Get fields used in templates
- `createModel` - Create a new note model
- `modelTemplates` - Get card templates
- `modelStyling` - Get CSS styling
- `updateModelTemplates` - Update templates
- `updateModelStyling` - Update CSS

#### Notes
- `addNote` - Add a single note
- `addNotes` - Add multiple notes
- `canAddNotes` - Check if notes can be added
- `updateNoteFields` - Update note fields
- `findNotes` - Search for notes
- `notesInfo` - Get note details
- `deleteNotes` - Delete notes
- `addTags` - Add tags to notes
- `removeTags` - Remove tags from notes
- `getTags` - Get all tags

#### Cards
- `findCards` - Search for cards
- `cardsToNotes` - Get note IDs from card IDs
- `cardsInfo` - Get card details
- `suspend` - Suspend cards
- `unsuspend` - Unsuspend cards
- `areSuspended` - Check if cards are suspended
- `areDue` - Check if cards are due
- `getIntervals` - Get card intervals

#### Media
- `getMediaDirPath` - Get media directory path
- `storeMediaFile` - Store a media file (base64)
- `retrieveMediaFile` - Retrieve a media file
- `deleteMediaFile` - Delete a media file

## 🤖 MCP Server

The server includes a Model Context Protocol (MCP) integration for AI assistants.

### Starting the MCP Server

```bash
ANKI_COLLECTION_PATH=/path/to/collection.anki21 \
ANKICONNECT_ANKIWEB_USER=your@email.com \
ANKICONNECT_ANKIWEB_PASS=your_password \
uvx anki-connect-server mcp
```

### Available MCP Tools

- `get_deck_names` - Get all deck names
- `get_deck_names_and_ids` - Get decks with IDs
- `create_deck` - Create a new deck
- `delete_decks` - Delete decks
- `get_model_names` - Get all model names
- `get_model_field_names` - Get fields for a model
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
- `store_media_file` / `retrieve_media_file` / `delete_media_file` - Media operations
- `change_deck` - Move cards between decks
- `cards_to_notes` - Convert card IDs to note IDs
- `get_deck_config` - Get deck configuration
- `get_model_templates` / `get_model_styling` - Model customization
- `get_api_version` - Get API version
- `import_package` / `export_package` - Import/export decks
- `sync` / `sync_media` / `get_sync_status` - Sync operations

### Adding to Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "anki-connect-server": {
      "command": "uvx",
      "args": ["anki-connect-server", "mcp"],
      "env": {
        "ANKI_COLLECTION_PATH": "/path/to/collection.anki21",
        "ANKICONNECT_ANKIWEB_USER": "your@email.com",
        "ANKICONNECT_ANKIWEB_PASS": "your_password"
      }
    }
  }
}
```

## 🐳 Docker

### Using Pre-built Image

```bash
docker run -d \
  -p 8765:8765 \
  -v /path/to/collection.anki21:/data/collection.anki21 \
  -e ANKI_COLLECTION_PATH=/data/collection.anki21 \
  -e ANKICONNECT_ANKIWEB_USER=your@email.com \
  -e ANKICONNECT_ANKIWEB_PASS=your_password \
  --name anki-connect-server \
  your-docker-username/anki-connect-server:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  anki-connect-server:
    image: your-docker-username/anki-connect-server:latest
    ports:
      - "8765:8765"
    volumes:
      - ./collection.anki21:/data/collection.anki21
    environment:
      - ANKI_COLLECTION_PATH=/data/collection.anki21
      - ANKICONNECT_ANKIWEB_USER=${ANKIWEB_USER}
      - ANKICONNECT_ANKIWEB_PASS=${ANKIWEB_PASS}
    restart: unless-stopped
```

### Building from Source

```bash
docker build -t anki-connect-server .
```


