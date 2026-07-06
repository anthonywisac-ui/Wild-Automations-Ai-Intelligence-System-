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
LAST_ERROR = ""         # why the last OCR attempt failed (for diagnostics)


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


# vision-capable providers, tried in order (same fallback philosophy as the
# text chain): env key -> (base_url, model)
_VISION_CHAIN = [
    ("GROQ_API_KEY", "https://api.groq.com/openai/v1",
     "meta-llama/llama-4-scout-17b-16e-instruct"),
    ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai",
     "gemini-2.0-flash"),
    ("MISTRAL_API_KEY", "https://api.mistral.ai/v1", "pixtral-12b-2409"),
]


async def ocr_pdf(data: bytes) -> str:
    """Transcribe an image-based PDF via a vision-model fallback chain
    (GROQ Llama-4 Scout → Gemini → Mistral Pixtral). '' on total failure."""
    global LAST_ERROR
    LAST_ERROR = ""
    if not data:
        LAST_ERROR = "empty file"
        return ""
    try:
        pngs = _pdf_to_pngs(data)
    except Exception as exc:
        LAST_ERROR = f"render: {type(exc).__name__}: {exc}"
        return ""
    if not pngs:
        LAST_ERROR = "pdf rendered 0 pages"
        return ""
    content = [{"type": "text", "text":
                "Transcribe ALL text from this resume exactly as written "
                "(names, roles, dates, skills, education, certifications). "
                "Output plain text only, no commentary."}]
    for png in pngs:
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{png}"}})
    import httpx
    errors = []
    async with httpx.AsyncClient(timeout=90) as client:
        for env, base, model in _VISION_CHAIN:
            key = os.getenv(env)
            if not key:
                continue
            try:
                r = await client.post(
                    f"{base}/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": model,
                          "messages": [{"role": "user", "content": content}],
                          "max_tokens": 4000})
                if r.status_code != 200:
                    errors.append(f"{model}:http{r.status_code}")
                    continue
                text = (r.json()["choices"][0]["message"]["content"] or "").strip()
                if len(text) > 60:
                    logger.info("cv_ocr: %s extracted %d chars from %d page(s)",
                                model, len(text), len(pngs))
                    return text
                errors.append(f"{model}:empty")
            except Exception as exc:
                errors.append(f"{model}:{type(exc).__name__}")
    LAST_ERROR = "all vision models failed — " + "; ".join(errors[:4])
    logger.info("cv_ocr: %s", LAST_ERROR)
    return ""
