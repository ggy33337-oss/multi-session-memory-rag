from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.api.routes_chat import router as chat_router
from app.api.routes_health import router as health_router
from app.api.routes_history import router as history_router
from app.core.config import get_settings


app = FastAPI(
    title="Memory RAG API",
    description="Turn-level conversation memory service based on FastAPI, FAISS, and JSON storage.",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(history_router)

web_dir = Path(__file__).resolve().parent.parent / "web"
app.mount("/static", StaticFiles(directory=web_dir), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(web_dir / "index.html")


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
