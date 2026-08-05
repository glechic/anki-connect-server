import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from anki_connect_server.anki_wrapper import AnkiWrapper
from anki_connect_server.config import Config, get_config
from anki_connect_server.handlers import dispatch
from anki_connect_server.types import JsonValue

logger = logging.getLogger(__name__)


def create_anki_wrapper(config: Config | None = None) -> AnkiWrapper:
    settings = config or get_config()
    return AnkiWrapper(settings.COLLECTION_PATH)


@asynccontextmanager  # type: ignore[deprecated]
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.anki_wrapper = create_anki_wrapper()
    try:
        yield
    finally:
        wrapper: AnkiWrapper | None = getattr(app.state, "anki_wrapper", None)
        if wrapper is not None:
            wrapper.close()
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
    params: dict[str, JsonValue] = {}


class AnkiConnectResponse(BaseModel):
    result: JsonValue
    error: str | None = None


def get_request_wrapper(request: Request) -> AnkiWrapper:
    wrapper: AnkiWrapper | None = getattr(request.app.state, "anki_wrapper", None)
    if wrapper is None:
        raise RuntimeError("Server not initialized")
    return wrapper


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/", response_model=AnkiConnectResponse)
@app.post("/api", response_model=AnkiConnectResponse)
async def handle_request(req: AnkiConnectRequest, request: Request) -> dict[str, JsonValue]:
    wrapper = get_request_wrapper(request)
    try:
        result = await dispatch(req.action, req.params, wrapper)
        return {"result": result, "error": None}
    except ValueError as e:
        # Client-facing errors (unknown action, missing/invalid params) are
        # reported in the response body per the AnkiConnect convention with
        # HTTP 200 so existing clients keep working.
        return {"result": None, "error": str(e)}
    # Any other exception (corrupted collection, Anki backend crash, etc.) is
    # a server error and propagates as HTTP 500 via the handler below.


@app.exception_handler(Exception)
async def server_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Surface unexpected (non-ValueError) exceptions as HTTP 500 instead of
    swallowing them into a 200 with an error field. A corrupted-collection crash
    is a server fault, not a client error, and should not be reported with 200."""
    logger.error(
        "Unhandled exception processing %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=exc,
    )
    return JSONResponse(status_code=500, content={"result": None, "error": str(exc)})


def run_server() -> None:
    """Run the FastAPI server."""
    import uvicorn

    settings = get_config()
    uvicorn.run(app, host=settings.BIND, port=settings.PORT)


if __name__ == "__main__":
    run_server()
