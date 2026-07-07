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

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# well-known certifications: regex safety-net so certs never come back empty
# just because the LLM skipped them (word-boundary matched, case-aware)
_CERT_PATTERNS = [
    (r"\bPMP\b|Project Management Professional", "PMP"),
    (r"\bPRINCE2\b", "PRINCE2"),
    (r"\bPMI-ACP\b", "PMI-ACP"),
    (r"\bCSM\b|Certified Scrum ?Master", "CSM"),
    (r"\bPSM\b|Professional Scrum Master", "PSM"),
    (r"\bSAFe\b", "SAFe"),
    (r"\bITIL\b", "ITIL"),
    (r"\bSix Sigma\b|\bLean Six\b", "Six Sigma"),
    (r"AWS Certified|\bAWS SA\b", "AWS Certified"),
    (r"Azure (Certified|Administrator|Architect|Fundamentals)", "Azure Certified"),
    (r"Google Cloud (Certified|Professional)|\bGCP Certified\b", "GCP Certified"),
    (r"\bCISSP\b", "CISSP"), (r"\bCISM\b", "CISM"), (r"\bCISA\b", "CISA"),
    (r"\bCEH\b", "CEH"), (r"\bCompTIA\b", "CompTIA"),
    (r"\bCAPM\b", "CAPM"), (r"\bCBAP\b", "CBAP"),
]


def _extract_certs(text: str) -> List[str]:
    found = []
    for pat, name in _CERT_PATTERNS:
        if re.search(pat, text, re.I if name not in ("CSM", "PSM", "CISM", "CISA") else 0):
            if name not in found:
                found.append(name)
    # generic "<Something> Certified" (e.g. "Scrum Fundamentals Certified -
    # SCRUMstudy") — names the fixed list can't know about
    for m in re.finditer(r"\b([A-Z][\w+#./-]*(?:\s+[A-Z&][\w+#./-]*){0,4})\s+Certified\b", text):
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        # drop section headers that leak into the capture
        name = re.sub(r"^((Licenses?|Certifications?|Training|Education)(\s*&\s*|\s+and\s+|\s+))+",
                      "", name, flags=re.I).strip()
        if 2 < len(name) < 45:
            label = f"{name} Certified"
            if label not in found and not any(name.lower() in f.lower() for f in found):
                found.append(label)
    return found[:6]


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
                "location (candidate's current city+country from the CV, '' if absent), "
                "languages (array of languages the candidate speaks, default ['English']), "
                "summary (one sentence). CV:\n" + text[:7000],
                system="You output only compact valid JSON.", max_tokens=500)
            m = re.search(r"\{.*\}", out, re.S)
            if m:
                p = json.loads(m.group(0))
                p.setdefault("alternate_roles", [])
                p.setdefault("skills", [])
                p.setdefault("education", "")
                p.setdefault("certifications", [])
                p.setdefault("location", "")
                p.setdefault("languages", ["English"])
                # regex safety-net: catch well-known certs the LLM missed
                for c in _extract_certs(text):
                    if c not in p["certifications"]:
                        p["certifications"].append(c)
                p["_source"] = "llm"
                return p
    except Exception as exc:
        logger.info("job_matcher.analyze_profile fallback: %s", exc)
    # deterministic fallback
    from core.concierge import analyze_cv
    cv = await analyze_cv(text)
    return {"role": cv.get("role", ""), "alternate_roles": [], "domain": "",
            "seniority": cv.get("seniority", ""), "skills": cv.get("skills", []),
            "education": "", "certifications": _extract_certs(text),
            "summary": "", "_source": "fallback"}


async def rank(profile: Dict[str, Any], jobs: List[Dict[str, Any]],
               keep_min: int = 30, top: int = 30) -> List[Dict[str, Any]]:
    """LLM scores each job 0-100 for TRUE fit vs the profile (domain+seniority+skills
    aware, reading the description). Returns only genuinely-relevant jobs, each with
    a match% and a plain reason. Deterministic fallback if no LLM."""
    if not jobs:
        return []
    cand = jobs[:40]
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if llm:
            lines = []
            for i, j in enumerate(cand):
                desc = (j.get("description") or "")[:200]
                lines.append(f"[{i}] {j.get('title','')} @ {j.get('company','')} · "
                             f"{j.get('location','')} — {desc}")
            prompt = (
                f"Candidate: role={profile.get('role')}, domain={profile.get('domain')}, "
                f"seniority={profile.get('seniority')}, skills={profile.get('skills')}, "
                f"location={profile.get('location') or 'unknown'}, "
                f"languages={profile.get('languages') or ['English']}. "
                "Score each job 0-100 for TRUE fit. Same domain/industry AND seniority AND "
                "skills = high; a different industry (e.g. manufacturing vs IT, oncology/"
                "clinical-trials vs IT, tax/accounting vs IT) or wrong seniority = low, even "
                "if the job title is similar. HARD RULE: if the listing restricts hiring to a "
                "country/region the candidate is NOT in (e.g. 'remote from Argentina', "
                "'US residents only') or requires a language the candidate does not speak, "
                "score it 20 or less regardless of skills. For each job give three "
                "short fit phrases (<=8 words each): skill_fit (which skills match/miss), "
                "seniority_fit (level match), domain_fit (industry match). Return ONLY a JSON "
                "array [{\"i\":<index>,\"score\":<0-100>,\"skill_fit\":\"<..>\","
                "\"seniority_fit\":\"<..>\",\"domain_fit\":\"<..>\"}]. Jobs:\n"
                + "\n".join(lines))
            # up to 3 attempts: one malformed reply must NOT silently downgrade
            # the whole system to keyword scoring while 4 healthy models exist
            m, scored = None, None
            for _attempt in range(3):
                out = await llm.complete(prompt, system="You output only a JSON array.",
                                         max_tokens=1100)
                m = re.search(r"\[.*\]", out, re.S)
                if m:
                    try:
                        scored = json.loads(m.group(0))
                        break
                    except Exception:
                        m = None
                logger.info("job_matcher.rank: bad JSON (attempt %d) — retrying", _attempt + 1)
            if m and scored is not None:
                by_i = {int(s["i"]): s for s in scored if "i" in s}
                enriched = []
                for i, j in enumerate(cand):
                    s = by_i.get(i, {})
                    sc = float(s.get("score", 40))
                    j = dict(j)
                    j["match"] = round(sc / 100, 2)
                    j["match_type"] = "ai"   # LLM-judged score (vs keyword overlap)
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
                # GUARANTEE: never fewer than `top` when candidates exist —
                # a harsh model pads from the best of the rest
                if len(strong) < top:
                    strong = enriched[:top]
                return strong[:top]
    except Exception as exc:
        logger.info("job_matcher.rank fallback: %s", exc)
    # deterministic fallback: keep as-is (already overlap-ranked upstream) —
    # tag honestly so the UI can show these are keyword scores, not AI judgment
    return [dict(j, match_type="keyword") for j in cand[:top]]




async def _full_desc(url: str) -> str:
    """Fetch a job page and extract its body text. Direct first; blocked or
    thin pages retry through Jina Reader (JINA_API_KEY lifts its rate-limit).
    Fail-soft: '' on any error."""
    if not (url or "").startswith("http"):
        return ""
    def _strip(html: str) -> str:
        html = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", html)
        text = re.sub(r"(?s)<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", text).strip()[:2500]
    try:
        import httpx
        import os as _o
        async with httpx.AsyncClient(timeout=20, verify=False, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0"}) as client:
            try:
                r = await client.get(url, timeout=10)
                if r.status_code == 200:
                    text = _strip(r.text)
                    if len(text) > 400:
                        return text
            except Exception:
                pass
            # blocked / JS-rendered / thin → Jina Reader (renders + bypasses IP block)
            jheads = {}
            if _o.getenv("JINA_API_KEY"):
                jheads["Authorization"] = f"Bearer {_o.getenv('JINA_API_KEY')}"
            r = await client.get(f"https://r.jina.ai/{url}", headers=jheads, timeout=20)
            if r.status_code == 200 and len(r.text) > 400:
                return re.sub(r"\s+", " ", r.text).strip()[:2500]
        return ""
    except Exception:
        return ""


async def deep_rescore(profile: Dict[str, Any], ranked: List[Dict[str, Any]],
                       top_n: int = 6) -> List[Dict[str, Any]]:
    """Precision pass for the top N: fetch each job's FULL description page and
    re-judge fit on the complete JD (the first rank pass only saw a snippet).
    Fail-soft at every step — on any failure the original ranking is returned."""
    if not ranked:
        return ranked
    import asyncio
    head, tail = ranked[:top_n], ranked[top_n:]
    try:
        from core.llm_client import get_llm
        llm = get_llm()
        if not llm:
            return ranked
        fulls = await asyncio.wait_for(
            asyncio.gather(*[_full_desc(j.get("url", "")) for j in head],
                           return_exceptions=True), timeout=35)
        lines, any_full = [], False
        for i, j in enumerate(head):
            fd = fulls[i] if isinstance(fulls[i], str) else ""
            if len(fd) > len(j.get("description") or ""):
                any_full = True
            desc = fd or (j.get("description") or "")[:600]
            lines.append(f"[{i}] {j.get('title','')} @ {j.get('company','')} — {desc[:1800]}")
        if not any_full:
            return ranked   # nothing new to judge — keep the snippet-based scores
        _prompt = (
            f"Candidate: role={profile.get('role')}, domain={profile.get('domain')}, "
            f"seniority={profile.get('seniority')}, skills={profile.get('skills')}. "
            "These are the FULL job descriptions. Re-score each 0-100 for true fit "
            "and give skill_fit/seniority_fit/domain_fit (<=8 words each). Return ONLY "
            "a JSON array [{\"i\":<index>,\"score\":<0-100>,\"skill_fit\":\"..\","
            "\"seniority_fit\":\"..\",\"domain_fit\":\"..\"}]. Jobs:\n" + "\n".join(lines))
        scored = None
        for _attempt in range(2):   # retry once on malformed JSON
            out = await llm.complete(_prompt, system="You output only a JSON array.",
                                     max_tokens=700)
            m = re.search(r"\[.*\]", out, re.S)
            if m:
                try:
                    scored = json.loads(m.group(0))
                    break
                except Exception:
                    pass
        if scored is None:
            return ranked
        by_i = {int(s["i"]): s for s in scored if "i" in s}
        rescored = []
        for i, j in enumerate(head):
            s = by_i.get(i)
            j = dict(j)
            if s:
                j["match"] = round(float(s.get("score", j["match"] * 100)) / 100, 2)
                fit = {"skill": (s.get("skill_fit") or "").strip(),
                       "seniority": (s.get("seniority_fit") or "").strip(),
                       "domain": (s.get("domain_fit") or "").strip()}
                j["fit"] = fit
                parts = [f"Skills: {fit['skill']}" if fit["skill"] else "",
                         f"Level: {fit['seniority']}" if fit["seniority"] else "",
                         f"Domain: {fit['domain']}" if fit["domain"] else ""]
                j["why_match"] = " · ".join(p for p in parts if p) or j.get("why_match", "")
                j["match_type"] = "ai"
                j["deep"] = True   # scored on the full JD, not just the snippet
            rescored.append(j)
        merged = rescored + [dict(j) for j in tail]
        merged.sort(key=lambda x: x["match"], reverse=True)
        return merged
    except Exception as exc:
        logger.info("job_matcher.deep_rescore skipped: %s", exc)
        return ranked
