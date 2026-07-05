"""
CV Tools — on-demand, per-job helpers (NOT part of the main search flow).

Two independent, optional actions the user triggers per job:

    gap    = await keyword_gap(cv_text, job_description)   # ATS-style skill gap
    tailor = await tailor_cv(cv_text, job_description, title)  # targeted CV tweaks

Each is a single LLM call, self-contained and fail-soft: on any error it returns
a small structured object so the UI never breaks. These never run during search
— they fire only when the user clicks "Gap" / "Tailor" on a specific job.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _json_obj(raw: str) -> Dict[str, Any]:
    m = re.search(r"\{.*\}", raw or "", re.S)
    return json.loads(m.group(0)) if m else {}


async def keyword_gap(cv_text: str, job_description: str,
                      job_title: str = "") -> Dict[str, Any]:
    """ATS-style gap: which of the job's key skills the CV already shows vs
    misses, plus concrete additions. Deterministic-empty fallback on no LLM."""
    cv = (cv_text or "").strip()
    jd = (job_description or "").strip()
    if not cv or not jd:
        return {"matched": [], "missing": [], "suggestions": [],
                "note": "Need both CV and a job description."}
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if llm:
            out = await llm.complete(
                f"Job title: {job_title}\nJob description:\n{jd[:1500]}\n\n"
                f"Candidate CV:\n{cv[:4000]}\n\n"
                "Act as an ATS gap analyzer. Return ONLY JSON with keys: "
                "matched (array of up to 8 important skills/keywords the CV already "
                "demonstrates for THIS job), missing (array of up to 8 important "
                "skills/keywords the job wants but the CV lacks), suggestions (array "
                "of up to 4 short, concrete lines the candidate could add to close the "
                "gap). Keep every item short.",
                system="You output only compact valid JSON.", max_tokens=500)
            p = _json_obj(out)
            if p:
                return {"matched": p.get("matched", []) or [],
                        "missing": p.get("missing", []) or [],
                        "suggestions": p.get("suggestions", []) or [],
                        "note": ""}
    except Exception as exc:
        logger.info("cv_tools.keyword_gap fallback: %s", exc)
    return {"matched": [], "missing": [], "suggestions": [],
            "note": "Analysis unavailable right now — try again shortly."}


async def tailor_cv(cv_text: str, job_description: str,
                    job_title: str = "") -> Dict[str, Any]:
    """Targeted tailoring for ONE job: a rewritten professional summary + a few
    resume bullets aligned to the JD. Not a full-CV rewrite (keeps it fast)."""
    cv = (cv_text or "").strip()
    jd = (job_description or "").strip()
    if not cv or not jd:
        return {"summary": "", "bullets": [],
                "note": "Need both CV and a job description."}
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if llm:
            out = await llm.complete(
                f"Job title: {job_title}\nJob description:\n{jd[:1500]}\n\n"
                f"Candidate CV:\n{cv[:4000]}\n\n"
                "Tailor the candidate for THIS specific job using ONLY facts present "
                "in the CV (do not invent experience). Return ONLY JSON with keys: "
                "summary (a 2-3 sentence professional summary rewritten to target this "
                "job) and bullets (array of 3-5 resume bullet points, each starting "
                "with a strong verb, emphasising the CV experience most relevant to "
                "this job). Keep it truthful and concise.",
                system="You output only compact valid JSON.", max_tokens=650)
            p = _json_obj(out)
            if p:
                return {"summary": (p.get("summary") or "").strip(),
                        "bullets": p.get("bullets", []) or [], "note": ""}
    except Exception as exc:
        logger.info("cv_tools.tailor_cv fallback: %s", exc)
    return {"summary": "", "bullets": [],
            "note": "Tailoring unavailable right now — try again shortly."}
