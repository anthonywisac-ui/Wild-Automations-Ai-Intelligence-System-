"""
Admin API — FastAPI router for system management.
Documented in: docs/ADMIN DASHBOARD.md § 2.1

Endpoints:
  GET  /admin/health         — system health
  GET  /admin/sources        — all scraper sources
  POST /admin/sources/{id}/scrape — trigger manual scrape
  GET  /admin/users          — paginated user list
  GET  /admin/metrics        — system metrics
  GET  /admin/logs           — recent logs
  GET  /admin/analytics      — time-series analytics

Mount in main FastAPI app:
    from admin.api import router as admin_router
    app.include_router(admin_router, prefix="/api/v1")
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from fastapi import APIRouter, HTTPException, Query
    from fastapi.responses import JSONResponse
    _FASTAPI = True
except ImportError:
    _FASTAPI = False

_ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# Injected at startup
_engine = None
_db = None


def set_engine(scraper_engine) -> None:
    global _engine
    _engine = scraper_engine


def set_db(db_layer) -> None:
    global _db
    _db = db_layer


if _FASTAPI:
    router = APIRouter(prefix="/admin", tags=["admin"])

    def _require_admin(token: str = Query(default="", alias="token")) -> None:
        if _ADMIN_TOKEN and token != _ADMIN_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized")

    @router.get("/health")
    async def get_health(token: str = Query(default="", alias="token")) -> Dict[str, Any]:
        _require_admin(token)
        status: Dict[str, Any] = {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "scraper_engine": "ok" if _engine else "not_configured",
                "database": "ok" if _db else "not_configured",
            },
        }
        if _db:
            try:
                await _db.ping()
                status["components"]["database"] = "ok"
            except Exception as exc:
                status["components"]["database"] = f"error: {exc}"
                status["status"] = "degraded"
        return status

    @router.get("/sources")
    async def get_sources(
        token: str = Query(default="", alias="token"),
        status_filter: Optional[str] = Query(default=None, alias="status"),
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        _require_admin(token)
        try:
            from config.bot_manifests import PORTAL_CONFIGS
            sources = []
            for name, cfg in PORTAL_CONFIGS.items():
                src = {
                    "id": name,
                    "name": name,
                    "crawl_mode": cfg.get("crawl_mode", "unknown"),
                    "domain": cfg.get("domain", "unknown"),
                    "status": "active",
                }
                sources.append(src)
            return {"sources": sources, "total": len(sources)}
        except Exception as exc:
            logger.error("admin/sources error: %s", exc)
            return {"sources": [], "total": 0, "error": str(exc)}

    @router.post("/sources/{source_id}/scrape")
    async def trigger_scrape(
        source_id: str,
        token: str = Query(default="", alias="token"),
    ) -> Dict[str, Any]:
        _require_admin(token)
        if not _engine:
            raise HTTPException(status_code=503, detail="Scraper engine not configured")
        try:
            from config.bot_manifests import PORTAL_CONFIGS
            cfg = PORTAL_CONFIGS.get(source_id)
            if not cfg:
                raise HTTPException(status_code=404, detail=f"Source not found: {source_id}")
            results = await _engine.crawl_bot(cfg)
            return {"source_id": source_id, "items_scraped": len(results or []), "status": "ok"}
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("admin/scrape error source=%s: %s", source_id, exc)
            raise HTTPException(status_code=500, detail=str(exc))

    @router.get("/users")
    async def get_users(
        token: str = Query(default="", alias="token"),
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        _require_admin(token)
        if not _db:
            return {"users": [], "total": 0, "page": page, "limit": limit}
        try:
            users = await _db.list_users(page=page, limit=limit, search=search)
            return {"users": users or [], "page": page, "limit": limit}
        except Exception as exc:
            logger.error("admin/users error: %s", exc)
            return {"users": [], "error": str(exc)}

    @router.get("/metrics")
    async def get_metrics(
        token: str = Query(default="", alias="token"),
        period: str = "day",
        metric_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        _require_admin(token)
        metrics: Dict[str, Any] = {
            "period": period,
            "timestamp": datetime.utcnow().isoformat(),
            "scraper": {},
            "notifications": {},
            "users": {},
        }
        if _engine and hasattr(_engine, "get_stats"):
            try:
                metrics["scraper"] = await _engine.get_stats()
            except Exception:
                pass
        return metrics

    @router.get("/logs")
    async def get_logs(
        token: str = Query(default="", alias="token"),
        level: Optional[str] = None,
        component: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        _require_admin(token)
        # In production: query Supabase logs table or loguru handler
        return [{"message": "Log streaming not yet wired to Supabase", "level": "INFO", "timestamp": datetime.utcnow().isoformat()}]

    @router.get("/analytics")
    async def get_analytics(
        token: str = Query(default="", alias="token"),
        metric: str = "opportunities_scraped",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        aggregation: str = "day",
    ) -> Dict[str, Any]:
        _require_admin(token)
        return {
            "metric": metric,
            "aggregation": aggregation,
            "start_date": start_date,
            "end_date": end_date,
            "data": [],
            "note": "Wire to Supabase analytics table when ready",
        }

else:
    router = None  # type: ignore
    logger.info("admin/api: FastAPI not installed — router not created")
