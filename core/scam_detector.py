"""Scam Job Detector — flags likely fraudulent postings."""
from __future__ import annotations
import re
from typing import Tuple

_SCAM_HIGH = [
    r"earn\s+\$[\d,]+\s*(per|a)\s*(day|week|hour)",
    r"make\s+(money|cash)\s+from\s+home",
    r"no\s+experience\s+.{0,20}(high|great|amazing)\s+(pay|salary|income)",
    r"investment\s+required|pay\s+to\s+(work|train|start)",
    r"send\s+(money|payment|fee)\s+to",
    r"wire\s+transfer.{0,30}job",
    r"bank\s+account\s+details.{0,30}(apply|required|needed)",
    r"social\s+security.{0,30}(apply|required|upfront)",
    r"passport\s+(copy|scan).{0,40}before\s+(interview|offer)",
    r"unlimited\s+(earning|income|potential)",
    r"be\s+your\s+own\s+boss.{0,40}guaranteed",
    r"get\s+paid\s+to\s+(like|share|post|watch)",
    r"\$\d{3,}\s*per\s*(day|hour).{0,30}(easy|simple|no experience)",
]
_SCAM_MEDIUM = [
    r"work\s+from\s+home.{0,30}(easy|simple|anyone)",
    r"guaranteed\s+(income|salary|earnings)",
    r"this\s+is\s+not\s+a\s+(scam|fraud)",
    r"100%\s+legitimate",
    r"urgent\s+hiring.{0,30}worldwide",
    r"confidential\s+company|company\s+name\s+(disclosed|revealed)\s+later",
    r"data\s+entry.{0,20}\$[\d,]+\s*per\s*hour",
]
_LEGIT_SIGNALS = [
    r"boards\.greenhouse\.io|jobs\.lever\.co|ashbyhq\.com|workday\.com",
    r"bamboohr|smartrecruiters|teamtailor|workable\.com",
    r"linkedin\.com/jobs/view|indeed\.com/viewjob",
    r"\.careers\.|/careers/|/jobs/\d{5,}",
]


def scam_score(title: str, description: str, url: str = "") -> Tuple[float, list[str]]:
    """
    Returns (score 0.0–1.0, list of triggered signals).
    0.0 = definitely legit, 1.0 = definitely scam.
    """
    text = f"{title} {description}".lower()
    signals: list[str] = []

    # Legit ATS URL = very low scam probability
    for pat in _LEGIT_SIGNALS:
        if re.search(pat, url, re.I):
            return 0.03, []

    # High-confidence scam signals
    for pat in _SCAM_HIGH:
        if re.search(pat, text, re.I):
            signals.append(f"HIGH: {pat[:50]}")

    # Medium signals
    for pat in _SCAM_MEDIUM:
        if re.search(pat, text, re.I):
            signals.append(f"MED: {pat[:50]}")

    high_count = sum(1 for s in signals if s.startswith("HIGH"))
    med_count = sum(1 for s in signals if s.startswith("MED"))
    score = min(1.0, high_count * 0.35 + med_count * 0.15)
    return round(score, 3), signals


def is_scam(title: str, description: str, url: str = "",
            threshold: float = 0.5) -> bool:
    score, _ = scam_score(title, description, url)
    return score >= threshold
