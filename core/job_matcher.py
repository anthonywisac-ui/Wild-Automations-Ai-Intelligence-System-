"""
Job Matcher — LLM-driven semantic matching (not keyword/title matching).

Reads the FULL CV and the FULL job descriptions and judges true fit: same
domain/industry + seniority + skills. An IT project manager is NOT matched to a
manufacturing (air-cooler) PM role, because the model reasons over the whole
profile + description, not the job title.

    profile = await analyze_profile(cv_text)          # rich structured profile
    ranked  = await rank(profile, jobs)               # semantic relevance + reason

Falls back to deterministic overlap if no LLM key is configured, so it never
returns nothing.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def analyze_profile(cv_text: str) -> Dict[str, Any]:
    """LLM → rich candidate profile from the full CV."""
    text = (cv_text or "").strip()
    if not text:
        return {}
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if llm:
            out = await llm.complete(
                "Read this CV and return ONLY JSON with keys: "
                "role (best-fit current job title), alternate_roles (array of 3 realistic "
                "adjacent titles), domain (industry/field, e.g. 'IT / software delivery'), "
                "seniority (junior/mid/senior/lead), years (number), "
                "skills (array of up to 8), summary (one sentence). CV:\n" + text[:7000],
                system="You output only compact valid JSON.", max_tokens=400)
            m = re.search(r"\{.*\}", out, re.S)
            if m:
                p = json.loads(m.group(0))
                p.setdefault("alternate_roles", [])
                p.setdefault("skills", [])
                p["_source"] = "llm"
                return p
    except Exception as exc:
        logger.info("job_matcher.analyze_profile fallback: %s", exc)
    # deterministic fallback
    from core.concierge import analyze_cv
    cv = await analyze_cv(text)
    return {"role": cv.get("role", ""), "alternate_roles": [], "domain": "",
            "seniority": cv.get("seniority", ""), "skills": cv.get("skills", []),
            "summary": "", "_source": "fallback"}


async def rank(profile: Dict[str, Any], jobs: List[Dict[str, Any]],
               keep_min: int = 45, top: int = 20) -> List[Dict[str, Any]]:
    """LLM scores each job 0-100 for TRUE fit vs the profile (domain+seniority+skills
    aware, reading the description). Returns only genuinely-relevant jobs, each with
    a match% and a plain reason. Deterministic fallback if no LLM."""
    if not jobs:
        return []
    cand = jobs[:24]
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if llm:
            lines = []
            for i, j in enumerate(cand):
                desc = (j.get("description") or "")[:280]
                lines.append(f"[{i}] {j.get('title','')} @ {j.get('company','')} · "
                             f"{j.get('location','')} — {desc}")
            prompt = (
                f"Candidate: role={profile.get('role')}, domain={profile.get('domain')}, "
                f"seniority={profile.get('seniority')}, skills={profile.get('skills')}. "
                "Score each job 0-100 for TRUE fit. Same domain/industry AND seniority AND "
                "skills = high; a different industry (e.g. manufacturing vs IT) or wrong "
                "seniority = low, even if the job title is similar. Return ONLY a JSON array "
                "[{\"i\":<index>,\"score\":<0-100>,\"reason\":\"<short why>\"}]. Jobs:\n"
                + "\n".join(lines))
            out = await llm.complete(prompt, system="You output only a JSON array.",
                                     max_tokens=900)
            m = re.search(r"\[.*\]", out, re.S)
            if m:
                scored = json.loads(m.group(0))
                by_i = {int(s["i"]): s for s in scored if "i" in s}
                res = []
                for i, j in enumerate(cand):
                    s = by_i.get(i)
                    if not s:
                        continue
                    sc = float(s.get("score", 0))
                    if sc < keep_min:
                        continue
                    j = dict(j)
                    j["match"] = round(sc / 100, 2)
                    j["why_match"] = s.get("reason", j.get("why_match", ""))
                    res.append(j)
                res.sort(key=lambda x: x["match"], reverse=True)
                return res[:top]
    except Exception as exc:
        logger.info("job_matcher.rank fallback: %s", exc)
    # deterministic fallback: keep as-is (already overlap-ranked upstream)
    return cand[:top]
