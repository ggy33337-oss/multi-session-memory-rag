import psycopg
from fastapi import APIRouter

from app.core.config import get_settings


router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    settings = get_settings()
    try:
        with psycopg.connect(settings.database_url) as connection:
            connection.execute("SELECT 1")
    except Exception as exc:
        return {"status": "degraded", "database": "unavailable", "detail": str(exc)}

    return {"status": "ok", "database": "available"}
