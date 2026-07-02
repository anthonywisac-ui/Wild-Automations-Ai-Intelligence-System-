"""
FastAPI application entry point — Layer 2 platform.
Mounts WhatsApp webhook + Admin API.
Shares the same Orchestrator (scraper engine, DB, delivery) as main.py.

Start:
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload

Environment variables (same .env as main.py):
    SUPABASE_URL, SUPABASE_KEY, SUPABASE_TABLE
    WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET
    WHAPI_API_KEY / META_PHONE_NUMBER_ID + META_ACCESS_TOKEN
    ADMIN_TOKEN
"""

import asyncio
import importlib.util
import logging
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# SSL patch (same as main.py)
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import httpx as _httpx_module
_orig = _httpx_module.AsyncClient.__init__
def _patched(self, *a, **kw):
    kw["verify"] = False
    _orig(self, *a, **kw)
_httpx_module.AsyncClient.__init__ = _patched

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from whatsapp.webhook_receiver import router as whatsapp_router, set_processor
from admin.api import router as admin_router, set_engine, set_db

from main import RuntimeConfig, Orchestrator, validate_manifest

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("app")


def _load_manifest():
    manifest_path = BASE_DIR / "config" / "bot_manifests.py.py"
    spec = importlib.util.spec_from_file_location("bot_manifests", manifest_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app = FastAPI(
    title="WildAutomations Platform",
    version="1.0.0",
    description="Opportunity Intelligence Platform — WhatsApp Bot + Admin API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(whatsapp_router, prefix="/api/v1/webhooks")
app.include_router(admin_router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    logger.info("app: startup — wiring orchestrator")

    cfg = RuntimeConfig()
    manifest = _load_manifest()
    validated = validate_manifest(manifest)

    orchestrator = Orchestrator(cfg, manifest, validated)
    app.state.orchestrator = orchestrator

    # Wire message processor into webhook receiver
    set_processor(orchestrator.message_processor)

    # Wire engine + db into admin API
    set_engine(orchestrator.scraper)
    set_db(orchestrator.db)

    # Start notification scheduler as background task
    app.state.scheduler_task = asyncio.create_task(orchestrator.scheduler.run())

    logger.info(
        "app: ready | crawlable_bots=%s",
        list(validated["crawlable"].keys()),
    )


@app.on_event("shutdown")
async def shutdown():
    task = getattr(app.state, "scheduler_task", None)
    if task:
        task.cancel()
    orchestrator = getattr(app.state, "orchestrator", None)
    if orchestrator:
        await orchestrator.delivery.shutdown()
    logger.info("app: shutdown complete")


@app.get("/")
async def root():
    return {"status": "ok", "service": "WildAutomations Platform", "version": "1.0.0"}


@app.get("/health")
async def health():
    orchestrator = getattr(app.state, "orchestrator", None)
    return {
        "status": "ok",
        "db": "connected" if (orchestrator and orchestrator.db) else "not_configured",
        "scheduler_queue": orchestrator.scheduler.queue_size() if orchestrator else 0,
    }
