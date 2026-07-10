"""ATS Platform Detector — identifies which ATS a job page uses."""
from __future__ import annotations
import re

_ATS_PATTERNS: dict[str, str] = {
    "greenhouse":      r"boards\.greenhouse\.io|greenhouse\.io/jobs|boards-api\.greenhouse",
    "lever":           r"jobs\.lever\.co|lever\.co/[^/]+/[a-f0-9-]{30}",
    "ashby":           r"ashbyhq\.com|jobs\.ashby\.com",
    "workday":         r"myworkdayjobs\.com|wd\d+\.myworkdayjobs|workday\.com/[^/]+/job",
    "bamboohr":        r"bamboohr\.com/careers|\.bamboohr\.com",
    "smartrecruiters": r"smartrecruiters\.com/[^/]+/[^/]+$",
    "taleo":           r"taleo\.net|oracle\.taleo|icims\.com",
    "jobvite":         r"jobvite\.com/[^/]+/job",
    "workable":        r"apply\.workable\.com|\.workable\.com",
    "teamtailor":      r"teamtailor\.com/jobs|\.teamtailor\.com",
    "recruitee":       r"recruitee\.com/o/",
    "personio":        r"personio\.de/jobs|personio\.com/jobs",
    "rippling":        r"rippling\.com/jobs|app\.rippling\.com",
    "gusto":           r"gusto\.com/about/careers",
    "breezyhr":        r"breezy\.hr|app\.breezy\.hr",
    "pinpointhq":      r"pinpointhq\.com",
    "comeet":          r"comeet\.com/jobs",
    "jazz":            r"app\.jazz\.co|resumatorapp\.com",
    "greenhouse_eu":   r"boards\.eu\.greenhouse\.io",
    "lever_eu":        r"jobs\.eu\.lever\.co",
}


def detect_ats(url: str, html: str = "") -> str:
    """Returns ATS name ('greenhouse', 'lever', etc.) or 'unknown'."""
    target = url + " " + html[:3000]
    for platform, pattern in _ATS_PATTERNS.items():
        if re.search(pattern, target, re.I):
            return platform
    return "unknown"


def is_ats_url(url: str) -> bool:
    """True if URL is a known ATS job page (high quality, structured)."""
    return detect_ats(url) != "unknown"


def ats_score(platform: str) -> float:
    """Reliability score for each ATS — ATS pages are structured, real postings."""
    scores = {
        "greenhouse": 0.97, "greenhouse_eu": 0.97,
        "lever": 0.97, "lever_eu": 0.97,
        "ashby": 0.96, "workday": 0.95,
        "bamboohr": 0.94, "smartrecruiters": 0.93,
        "workable": 0.92, "teamtailor": 0.91,
        "recruitee": 0.90, "jobvite": 0.90,
        "taleo": 0.88, "personio": 0.88,
        "rippling": 0.87, "gusto": 0.87,
        "breezyhr": 0.85, "pinpointhq": 0.85,
    }
    return scores.get(platform, 0.70)
