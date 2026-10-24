"""Main FastAPI application for EventPilot AI."""
import sys
from pathlib import Path

# Ensure project root is on sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.config import settings
from src.api.routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eventpilot.api")

app = FastAPI(
    title="EventPilot AI — Multi-Agent Event Orchestration API",
    description=(
        "REST API supporting Fetch.ai uAgents, ASI Chat Protocol (ACP), "
        "and physical event operations: timeline generation, waitlist promotions, "
        "cryptographic check-ins, and risk recovery."
    ),
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def audit_http_logging(request: Request, call_next):
    logger.info(f"[HTTP] {request.method} {request.url.path}")
    response = await call_next(request)
    return response

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"[HTTP ERROR] Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please consult server audit logs."},
    )

app.include_router(router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "eventpilot-ai",
        "app_env": settings.APP_ENV,
        "database_backend": "MySQL" if "mysql" in settings.DATABASE_URL else "SQLite",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.app:app", host=settings.API_HOST, port=settings.API_PORT, reload=settings.DEBUG)
