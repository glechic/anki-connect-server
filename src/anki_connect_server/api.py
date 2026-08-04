from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel

from anki_connect_server.anki_wrapper import AnkiWrapper
from anki_connect_server.config import Config, get_config
from anki_connect_server.handlers import dispatch


def create_anki_wrapper(config: Config | None = None) -> AnkiWrapper:
    settings = config or get_config()
    return AnkiWrapper(settings.COLLECTION_PATH)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    app.state.anki_wrapper = create_anki_wrapper()
    yield
    if app.state.anki_wrapper:
        app.state.anki_wrapper.close()
        app.state.anki_wrapper = None


app = FastAPI(
    title="AnkiConnect Server",
    description="Headless AnkiConnect-compatible REST API server with AnkiWeb sync",
    version="0.1.0",
    lifespan=app_lifespan,
)


class AnkiConnectRequest(BaseModel):
    action: str
    version: int = 6
    params: dict = {}


class AnkiConnectResponse(BaseModel):
    result: Any
    error: str | None = None


def get_request_wrapper(request: Request) -> AnkiWrapper:
    wrapper = getattr(request.app.state, "anki_wrapper", None)
    if wrapper is None:
        raise RuntimeError("Server not initialized")
    return wrapper


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/api", response_model=AnkiConnectResponse)
async def handle_request(req: AnkiConnectRequest, request: Request):
    wrapper = get_request_wrapper(request)
    try:
        result = await dispatch(req.action, req.params, wrapper)
        return {"result": result, "error": None}
    except Exception as e:
        return {"result": None, "error": str(e)}


def run_server():
    """Run the FastAPI server."""
    import uvicorn

    settings = get_config()
    uvicorn.run(app, host=settings.BIND, port=settings.PORT)


if __name__ == "__main__":
    run_server()
