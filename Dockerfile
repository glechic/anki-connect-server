FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy pyproject.toml and install dependencies
COPY pyproject.toml ./
COPY uv.lock ./
RUN uv sync --locked

# Copy source code
COPY . ./

# Create data directory for collection
RUN mkdir -p /data

# Environment variables
ENV ANKICONNECT_COLLECTION_PATH=/data/collection.anki2
ENV ANKICONNECT_PORT=8765
ENV ANKICONNECT_BIND=0.0.0.0

# Expose port
EXPOSE 8765

# Run the API server. The CLI exposes 'api' and 'mcp' subcommands; there is
# no 'server' subcommand (the previous CMD ['uv', 'run', 'server'] was a bug
# and the container exited immediately on startup).
CMD ["uv", "run", "anki-connect-server", "api"]
