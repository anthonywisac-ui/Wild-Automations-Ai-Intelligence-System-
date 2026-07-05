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
                "seniority (junior/mid/senior/lead), years (number of years of experience), "
                "skills (array of up to 8), education (highest degree + field, one string, "
                "'' if none), certifications (array of up to 5 named certs, [] if none), "
                "summary (one sentence). CV:\n" + text[:7000],
                system="You output only compact valid JSON.", max_tokens=460)
            m = re.search(r"\{.*\}", out, re.S)
            if m:
                p = json.loads(m.group(0))
                p.setdefault("alternate_roles", [])
                p.setdefault("skills", [])
                p.setdefault("education", "")
                p.setdefault("certifications", [])
                p["_source"] = "llm"
                return p
    except Exception as exc:
        logger.info("job_matcher.analyze_profile fallback: %s", exc)
    # deterministic fallback
    from core.concierge import analyze_cv
    cv = await analyze_cv(text)
    return {"role": cv.get("role", ""), "alternate_roles": [], "domain": "",
            "seniority": cv.get("seniority", ""), "skills": cv.get("skills", []),
            "education": "", "certifications": [], "summary": "", "_source": "fallback"}


async def rank(profile: Dict[str, Any], jobs: List[Dict[str, Any]],
               keep_min: int = 35, top: int = 20) -> List[Dict[str, Any]]:
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
                "seniority = low, even if the job title is similar. For each job give three "
                "short fit phrases (<=8 words each): skill_fit (which skills match/miss), "
                "seniority_fit (level match), domain_fit (industry match). Return ONLY a JSON "
                "array [{\"i\":<index>,\"score\":<0-100>,\"skill_fit\":\"<..>\","
                "\"seniority_fit\":\"<..>\",\"domain_fit\":\"<..>\"}]. Jobs:\n"
                + "\n".join(lines))
            out = await llm.complete(prompt, system="You output only a JSON array.",
                                     max_tokens=1100)
            m = re.search(r"\[.*\]", out, re.S)
            if m:
                scored = json.loads(m.group(0))
                by_i = {int(s["i"]): s for s in scored if "i" in s}
                enriched = []
                for i, j in enumerate(cand):
                    s = by_i.get(i, {})
                    sc = float(s.get("score", 40))
                    j = dict(j)
                    j["match"] = round(sc / 100, 2)
                    fit = {
                        "skill": (s.get("skill_fit") or "").strip(),
                        "seniority": (s.get("seniority_fit") or "").strip(),
                        "domain": (s.get("domain_fit") or "").strip(),
                    }
                    j["fit"] = fit
                    # readable one-line summary for backward-compatible UIs
                    parts = [f"Skills: {fit['skill']}" if fit["skill"] else "",
                             f"Level: {fit['seniority']}" if fit["seniority"] else "",
                             f"Domain: {fit['domain']}" if fit["domain"] else ""]
                    summary = " · ".join(p for p in parts if p)
                    j["why_match"] = summary or s.get("reason") or j.get("why_match", "")
                    enriched.append(j)
                enriched.sort(key=lambda x: x["match"], reverse=True)
                strong = [j for j in enriched if j["match"] * 100 >= keep_min]
                # never collapse to too few — show at least the 6 best even if the
                # model was harsh, so the user always has options to react to
                if len(strong) < 6:
                    strong = enriched[:max(6, len(strong))]
                return strong[:top]
    except Exception as exc:
        logger.info("job_matcher.rank fallback: %s", exc)
    # deterministic fallback: keep as-is (already overlap-ranked upstream)
    return cand[:top]
