"""
CV OCR — read image-based / scanned PDF resumes with Gemini vision.

pypdf can only extract embedded text; many real CVs are exported as images
(Canva, scans, screenshots) and yield 0 characters. This module renders the
PDF pages to PNG (pypdfium2) and asks Gemini's vision model (via the same
OpenAI-compatible endpoint the LLM chain already uses) to transcribe them.

    text = await ocr_pdf(pdf_bytes)     # '' if no key / failure (fail-soft)
"""

from __future__ import annotations

import base64
import io
import logging
import os

logger = logging.getLogger(__name__)

_MAX_PAGES = 4          # resumes are 1-3 pages; cap the vision cost
_RENDER_SCALE = 2.0     # ~144 dpi — sharp enough for OCR, small enough to send


def _pdf_to_pngs(data: bytes) -> list:
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(data)
    out = []
    for i in range(min(len(pdf), _MAX_PAGES)):
        bitmap = pdf[i].render(scale=_RENDER_SCALE)
        pil = bitmap.to_pil()
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        out.append(base64.b64encode(buf.getvalue()).decode())
    return out


async def ocr_pdf(data: bytes) -> str:
    """Transcribe an image-based PDF via Gemini vision. '' on any failure."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not (key and data):
        return ""
    try:
        pngs = _pdf_to_pngs(data)
        if not pngs:
            return ""
        content = [{"type": "text", "text":
                    "Transcribe ALL text from this resume exactly as written "
                    "(names, roles, dates, skills, education, certifications). "
                    "Output plain text only, no commentary."}]
        for png in pngs:
            content.append({"type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{png}"}})
        import httpx
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": "gemini-2.0-flash",
                      "messages": [{"role": "user", "content": content}],
                      "max_tokens": 4000})
            if r.status_code != 200:
                logger.info("cv_ocr: gemini vision status=%s %s",
                            r.status_code, r.text[:200])
                return ""
            text = (r.json()["choices"][0]["message"]["content"] or "").strip()
            logger.info("cv_ocr: extracted %d chars from %d page(s)",
                        len(text), len(pngs))
            return text
    except Exception as exc:
        logger.info("cv_ocr failed: %s", exc)
        return ""
