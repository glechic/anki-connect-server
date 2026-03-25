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
ENV ANKICONNECT_COLLECTION_PATH=/data/collection.anki21
ENV ANKICONNECT_PORT=8765
ENV ANKICONNECT_BIND=0.0.0.0

# Expose port
EXPOSE 8765

# Run the server directly
CMD ["uv", "run", "server"]
