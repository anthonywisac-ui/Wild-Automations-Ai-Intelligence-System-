"""
Job Eligibility Gates — deterministic must-have filters that run BEFORE the
match score is trusted (the "3-layer" fix: gates -> skills -> soft match).

Layer 1 gates (this module):
  - location:  "remote from Argentina", "LatAm only", "US residents", ...
               vs the candidate's country/region
  - language:  "Spanish required", "+ Dutch", "native German", ...
               vs the candidate's languages
  - domain:    oncology/clinical-research, tax/accounting, security
               engineering, sales/account management, nonprofit fundraising
               vs the candidate's domain (e.g. IT/software)

An LLM match score can NEVER lift a job past a failed gate — a 90% "skills
match" for an Argentina-only Spanish-speaking role is worthless to a
candidate in Abu Dhabi. Gates cap the score and attach a visible reason.

    gate = assess(job, user_country="united arab emirates",
                  user_languages=["english"], user_domain="it")
    # {"status": "not_eligible", "reasons": ["Location: Argentina/LatAm only"],
    #  "domain": "clinical_research", "cap": 0.25}
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# ── geography ────────────────────────────────────────────────────────────────

_REGIONS: Dict[str, List[str]] = {
    "latam": ["argentina", "brazil", "mexico", "chile", "colombia", "peru",
              "uruguay", "latam", "latin america", "south america"],
    "usa": ["usa", "u.s.", "us only", "united states", "america"],
    "canada": ["canada"],
    "uk": ["uk", "united kingdom", "britain", "england"],
    "europe": ["europe", "eu ", "eea", "emea", "germany", "netherlands",
               "france", "spain", "poland", "portugal", "italy", "ireland"],
    "apac": ["apac", "australia", "new zealand", "singapore", "japan",
             "philippines", "india"],
    "gcc": ["uae", "united arab emirates", "dubai", "abu dhabi", "saudi",
            "qatar", "kuwait", "bahrain", "oman", "gcc", "middle east"],
    "africa": ["nigeria", "kenya", "south africa", "egypt", "africa"],
}


def _region_of(country: str) -> Optional[str]:
    c = (country or "").lower().strip()
    if not c:
        return None
    for region, names in _REGIONS.items():
        if any(n.strip() in c or c in n.strip() for n in names):
            return region
    return None


# phrases that BIND the job to a place: "remote from X", "based in X",
# "residents of X", "X only", "must be located in X", "eligible to work in X"
_LOC_BIND = re.compile(
    r"(?:remote(?:ly)?\s+(?:from|in)|based in|located in|residing in|"
    r"residents? of|work(?:ing)? from|must (?:be|live|reside) in|"
    r"eligible to work in|authorized to work in|open (?:only )?to|"
    r"available (?:only )?(?:to|in)|candidates? (?:from|in)|only (?:for|in))\s+"
    r"([a-z .&-]{3,30})", re.I)


# ── language requirements ────────────────────────────────────────────────────

_LANGS = ["spanish", "dutch", "german", "french", "portuguese", "italian",
          "mandarin", "cantonese", "japanese", "korean", "arabic", "russian",
          "polish", "turkish", "hebrew", "swedish", "norwegian", "danish",
          "finnish", "czech", "hungarian", "thai", "vietnamese", "hindi", "urdu"]

_LANG_REQ = re.compile(
    r"(?:fluent(?:cy)? in|native|proficien\w+ in|speak(?:ing|er of)?|"
    r"knowledge of|command of|\+\s*|bilingual)\s*(" + "|".join(_LANGS) + r")\b|"
    r"\b(" + "|".join(_LANGS) + r")\s+(?:language|speaking|speaker|fluency|"
    r"proficiency|required|is a must|essential)", re.I)


# ── domain classification (safety net under the LLM) ─────────────────────────

# strong = one hit alone identifies the domain (unambiguous words);
# weak = needs company (2+ points total). strong counts 2 points, weak 1.
_DOMAINS: Dict[str, Dict[str, List[str]]] = {
    "clinical_research": {
        "strong": ["oncology", "clinical trial", "clinical study", "gcp",
                   "ich guidelines", "ctms", "pharmacovigilance"],
        "weak": ["patient recruitment", "regulatory submission", "fda", "ema",
                 "clinical data"]},
    "healthcare_ops": {
        "strong": ["pharmacy", "pharmacist", "dental", "cardiology", "nurse",
                   "telehealth", "medicaid", "medicare"],
        "weak": ["value-based care", "payer", "provider", "ehr", "emr",
                 "patient care", "patient success", "clinical workflow",
                 "hospital", "clinic", "medical center"]},
    "tax_accounting": {
        "strong": ["tax preparation", "tax manager", "tax compliance",
                   "tax advisory", "corporate tax", "bookkeeping"],
        "weak": ["cpa", "audit senior", "tax strategy"]},
    "security_engineering": {
        "strong": ["siem", "incident response", "penetration test",
                   "threat intelligence", "soc analyst", "zero trust",
                   "identity & access", "identity and access"],
        "weak": ["forensics", "iam ", "vulnerability assessment",
                 "security analytics"]},
    "sales_accounts": {
        "strong": ["quota", "consultative selling", "sales enablement",
                   "commissions"],
        "weak": ["account manager", "client success", "customer success",
                 "revenue target", "account growth", "strategic accounts"]},
    "nonprofit": {
        "strong": ["fundraising", "philanthropy", "donor"],
        "weak": ["volunteer management", "grassroots", "advocacy campaign",
                 "nonprofit"]},
    "marketing": {
        "strong": ["product marketing", "go-to-market", "gtm strategy",
                   "demand generation"],
        "weak": ["seo/sem", "brand marketing", "content marketing"]},
    "it_software": {
        "strong": ["sdlc", "devops", "it project", "software delivery",
                   "digital transformation"],
        "weak": ["software", "saas", "erp", "agile", "scrum", "cloud", "api",
                 "web development", "mobile app", "data platform", "crm system"]},
}

_USER_DOMAIN_ALIASES = {
    "it": "it_software", "software": "it_software", "tech": "it_software",
    "digital": "it_software", "information technology": "it_software",
    "healthcare": "healthcare_ops", "medical": "healthcare_ops",
    "finance": "tax_accounting", "accounting": "tax_accounting",
    "security": "security_engineering", "cybersecurity": "security_engineering",
    "sales": "sales_accounts", "marketing": "marketing",
}


def classify_domain(text: str) -> Optional[str]:
    """Dominant domain of a job by weighted keyword hits (None = unclear).
    A single 'strong' keyword (pharmacy, oncology, SIEM...) is enough."""
    t = (text or "").lower()
    best, best_score = None, 0
    for domain, kws in _DOMAINS.items():
        score = sum(2 for k in kws["strong"] if k in t) + \
                sum(1 for k in kws["weak"] if k in t)
        if score > best_score:
            best, best_score = domain, score
    return best if best_score >= 2 else None


def normalize_user_domain(raw: str) -> Optional[str]:
    r = (raw or "").lower()
    for alias, dom in _USER_DOMAIN_ALIASES.items():
        if alias in r:
            return dom
    for dom in _DOMAINS:
        if dom.replace("_", " ") in r or dom in r:
            return dom
    return None


# ── the gate ─────────────────────────────────────────────────────────────────

def assess(job: Dict[str, Any], user_country: str = "",
           user_languages: Optional[List[str]] = None,
           user_domain: str = "") -> Dict[str, Any]:
    """Run all gates on one job. Returns status + reasons + score cap.
    Conservative on purpose: only flags what the listing TEXT actually says."""
    blob = " ".join(str(job.get(k) or "") for k in
                    ("title", "location", "description")).lower()
    reasons: List[str] = []
    cap = 1.0

    # 1) location binding
    user_region = _region_of(user_country)
    for m in _LOC_BIND.finditer(blob):
        place = m.group(1).strip().rstrip(".,;:").lower()
        if place in ("home", "anywhere", "any location", "remote", "worldwide",
                     "any country", "abroad"):
            continue
        bound_region = _region_of(place)
        if bound_region is None:
            continue  # unrecognized place — do not guess
        user_ok = (user_region == bound_region or
                   (user_country and user_country.lower() in place))
        if not user_ok:
            # name the detected place by its cleanest region keyword
            hit = next((n.strip() for n in _REGIONS[bound_region] if n.strip() in place),
                       place)
            reasons.append(f"Location: listing is for {hit.title()} candidates only")
            cap = min(cap, 0.25)
            break

    # 2) language requirement
    langs = [l.lower() for l in (user_languages or ["english"])]
    lm = _LANG_REQ.search(blob)
    if lm:
        need = (lm.group(1) or lm.group(2) or "").lower()
        if need and need not in langs:
            reasons.append(f"Language: {need.title()} required")
            cap = min(cap, 0.25)

    # 3) domain mismatch (only when BOTH sides are confidently known).
    # No "adjacent domain" mercy: an IT candidate asked for IT jobs — a
    # pharmacy/dental org's PM role is not what they searched for.
    job_domain = classify_domain(blob)
    u_dom = normalize_user_domain(user_domain)
    if job_domain and u_dom and job_domain != u_dom:
        reasons.append(f"Domain: {job_domain.replace('_', ' ')} role, "
                       f"candidate is {u_dom.replace('_', ' ')}")
        cap = min(cap, 0.45)

    status = ("not_eligible" if cap <= 0.25 else
              "check" if reasons else "eligible")
    return {"status": status, "reasons": reasons, "cap": cap,
            "job_domain": job_domain}


def apply_gate(job: Dict[str, Any], gate: Dict[str, Any]) -> Dict[str, Any]:
    """Cap the job's match score per the gate and attach visible fields."""
    j = dict(job)
    match = float(j.get("match", 0))
    if gate["cap"] < 1.0 and match > gate["cap"]:
        j["match"] = round(gate["cap"], 2)
        j["match_capped"] = True
    j["eligibility"] = gate["status"]
    if gate["reasons"]:
        j["eligibility_reasons"] = gate["reasons"]
    return j
