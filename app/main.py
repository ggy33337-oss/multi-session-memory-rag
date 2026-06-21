from pathlib import Path
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import psycopg
import uvicorn

from app.api.routes_chat import router as chat_router
from app.api.routes_documents import router as documents_router
from app.api.routes_health import router as health_router
from app.api.routes_history import router as history_router
from app.api.routes_sessions import router as sessions_router
from app.core.database import init_database
from app.core.config import get_settings


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_database(get_settings())
    except psycopg.OperationalError as exc:
        logger.error("Database is unavailable during startup: %s", exc)
    yield


app = FastAPI(
    title="多会话长期记忆 RAG 问答系统 API",
    description="Multi-session long-term memory RAG QA system based on FastAPI, PostgreSQL, and pgvector.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(history_router)
app.include_router(documents_router)
app.include_router(sessions_router)

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
