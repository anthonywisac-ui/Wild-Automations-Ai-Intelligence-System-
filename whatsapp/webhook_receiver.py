"""
WhatsApp Webhook Receiver — FastAPI router for Meta webhook.
Documented in: docs/WHATSAPP AI ARCHITECTURE.md § 2.1

Two endpoints:
  GET  /webhook  — Meta verification challenge (VERIFY_TOKEN from .env)
  POST /webhook  — Incoming messages, forwarded to MessageProcessor

Environment variables used (already in .env):
  WHATSAPP_VERIFY_TOKEN — webhook verification token
  WHATSAPP_API_KEY      — Cloud API key (used by delivery_engine, not here)

Mount in main FastAPI app:
    from whatsapp.webhook_receiver import router as whatsapp_router
    app.include_router(whatsapp_router, prefix="/api/v1/webhooks")
"""

import hashlib
import hmac
import json
import logging
import os
from typing import Any, Dict

try:
    from fastapi import APIRouter, HTTPException, Request, Response
    from fastapi.responses import JSONResponse, PlainTextResponse
    _FASTAPI = True
except ImportError:
    _FASTAPI = False

logger = logging.getLogger(__name__)

# FastAPI router — only wired when FastAPI is installed
if _FASTAPI:
    router = APIRouter(prefix="/whatsapp", tags=["whatsapp-webhook"])
else:
    router = None  # type: ignore

_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "wildautomations_verify")
_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")

# Injected at startup by main app
_processor = None


def set_processor(processor) -> None:
    """Wire in the MessageProcessor at startup."""
    global _processor
    _processor = processor


def _verify_signature(payload: bytes, signature: str) -> bool:
    if not _APP_SECRET:
        return True  # skip in dev
    expected = hmac.new(_APP_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


if _FASTAPI and router:

    @router.get("")
    async def verify_webhook(request: Request) -> Response:
        """Meta webhook verification handshake."""
        params = request.query_params
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge")

        if mode == "subscribe" and token == _VERIFY_TOKEN:
            logger.info("webhook_receiver: verified successfully")
            return PlainTextResponse(challenge)

        logger.warning("webhook_receiver: verification failed mode=%s token=%s", mode, token)
        raise HTTPException(status_code=403, detail="Forbidden")

    @router.post("")
    async def receive_message(request: Request) -> JSONResponse:
        """Receive incoming WhatsApp messages."""
        body = await request.body()

        # Signature check
        sig = request.headers.get("X-Hub-Signature-256", "")
        if _APP_SECRET and not _verify_signature(body, sig):
            raise HTTPException(status_code=401, detail="Invalid signature")

        try:
            data: Dict[str, Any] = json.loads(body)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        # Extract messages
        messages = _extract_messages(data)

        for msg in messages:
            user_id = msg.get("from", "")
            phone = user_id
            text = msg.get("text", {}).get("body", "")

            if not text or not user_id:
                continue

            logger.info("webhook_receiver: message from=%s text=%s", user_id, text[:60])

            if _processor:
                try:
                    response = await _processor.process(user_id, phone, text)
                    logger.debug("webhook_receiver: processed intent=%s", response.get("metadata", {}))
                except Exception as exc:
                    logger.error("webhook_receiver: processor error: %s", exc)
            else:
                logger.warning("webhook_receiver: no processor configured — message dropped")

        return JSONResponse({"status": "ok"})


def _extract_messages(data: Dict[str, Any]):
    """Parse Meta webhook payload to extract message objects."""
    messages = []
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    messages.append(msg)
    except Exception as exc:
        logger.warning("webhook_receiver: parse error: %s", exc)
    return messages
