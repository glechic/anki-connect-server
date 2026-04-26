from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from anki_connect_server.config import config
from anki_connect_server.anki_wrapper import AnkiWrapper
from anki_connect_server.handlers import dispatch
from anki_connect_server import wrapper


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    wrapper.set_wrapper(AnkiWrapper(config.COLLECTION_PATH))
    yield
    wrapper.close_wrapper()


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
    error: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/api", response_model=AnkiConnectResponse)
async def handle_request(req: AnkiConnectRequest):
    if not wrapper.get_anki_wrapper():
        return {"result": None, "error": "Server not initialized"}

    try:
        result = await dispatch(req.action, req.params, wrapper.get_anki_wrapper())
        return {"result": result, "error": None}
    except Exception as e:
        return {"result": None, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.BIND, port=config.PORT)
