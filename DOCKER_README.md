# AnkiConnect Server - Docker Image

[![Docker Pulls](https://img.shields.io/docker/pulls/glechic/anki-connect-server)](https://hub.docker.com/r/glechic/anki-connect-server)
[![Docker Version](https://img.shields.io/docker/v/glechic/anki-connect-server)](https://hub.docker.com/r/glechic/anki-connect-server)
[![Image Size](https://img.shields.io/docker/image-size/glechic/anki-connect-server/latest)](https://hub.docker.com/r/glechic/anki-connect-server)

## Overview

Headless AnkiConnect-compatible REST API server with AnkiWeb sync support and MCP server integration. Run your Anki collection on any server without the Anki desktop app.

## Features

- **No Anki Desktop Required** - Direct collection access, no Qt/GUI needed
- **Full AnkiConnect API** - Version 6 API compatibility
- **AnkiWeb Sync** - Automatic synchronization with your AnkiWeb account
- **MCP Server** - Model Context Protocol integration for AI assistants
- **Lightweight** - Python 3.12 + FastAPI on slim base image
- **Production Ready** - Proper health checks and signal handling

## Quick Start

### Run with Docker

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
    container_name: anki-connect-server
    ports:
      - "8765:8765"
    volumes:
      - ./collection.anki2:/data/collection.anki2
    environment:
      - ANKICONNECT_COLLECTION_PATH=/data/collection.anki2
      - ANKICONNECT_ANKIWEB_USER=${ANKIWEB_USER}
      - ANKICONNECT_ANKIWEB_PASS=${ANKIWEB_PASS}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8765/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANKICONNECT_COLLECTION_PATH` | No | temp path | Path to your `.anki2` collection file |
| `ANKICONNECT_PORT` | No | `8765` | Server port |
| `ANKICONNECT_BIND` | No | `0.0.0.0` | Bind address |
| `ANKICONNECT_ANKIWEB_USER` | No | - | AnkiWeb username (for sync) |
| `ANKICONNECT_ANKIWEB_PASS` | No | - | AnkiWeb password (for sync) |
| `ANKICONNECT_ANKIWEB_URL` | No | - | Custom sync server URL |

## API Usage

### Get Deck Names

```bash
curl -X POST http://localhost:8765/api \
  -H "Content-Type: application/json" \
  -d '{"action": "deckNames", "version": 6}'
```

### Add a Note

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
        "fields": {"Front": "Hello", "Back": "World"}
      }
    }
  }'
```

### Sync with AnkiWeb

```bash
curl -X POST http://localhost:8765/api \
  -H "Content-Type: application/json" \
  -d '{"action": "sync", "version": 6}'
```

## Health Check

The container includes a health check endpoint:

```bash
curl http://localhost:8765/health
# Returns: {"status":"healthy"}
```

## MCP Server

The image also includes MCP server support for AI assistants:

```bash
docker run -d \
  -v /path/to/collection.anki2:/data/collection.anki2 \
  -e ANKICONNECT_COLLECTION_PATH=/data/collection.anki2 \
  glechic/anki-connect-server \
  uv run anki-connect-server mcp
```

## Volumes

- `/data` - Directory for Anki collection and media files
  - Mount your `collection.anki2` file here
  - Anki media directory will be created automatically

## Security Notes

⚠️ **Important:**
- Never expose port 8765 to the public internet without authentication
- Use a reverse proxy with TLS for production deployments
- Store AnkiWeb credentials securely (use Docker secrets or external secret management)
- Bind to `127.0.0.1` if only local access is needed

## Building from Source

```bash
git clone https://github.com/glechic/anki-connect-server.git
cd anki-connect-server
docker build -t anki-connect-server .
```

## Links

- [GitHub Repository](https://github.com/glechic/anki-connect-server)
- [PyPI Package](https://pypi.org/project/anki-connect-server/)
- [Full Documentation](https://github.com/glechic/anki-connect-server#readme)
- [AnkiConnect API Reference](https://github.com/FooSoft/anki-connect)
