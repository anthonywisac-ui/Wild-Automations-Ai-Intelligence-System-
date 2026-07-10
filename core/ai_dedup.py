"""AI Deduplication — removes duplicate job postings across sources."""
from __future__ import annotations
import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _slug(title: str, company: str, location: str) -> str:
    t = _normalize(title)
    c = _normalize(company)
    l = _normalize(location)
    # Remove seniority noise for better dedup
    t = re.sub(r"\b(senior|junior|sr|jr|lead|principal|staff)\b", "", t).strip()
    combined = f"{t}|{c}|{l}"
    return hashlib.md5(combined.encode()).hexdigest()


def _url_key(url: str) -> str:
    """Normalize URL — strip UTM params and trailing slashes."""
    url = re.sub(r"[?&](utm_[^&]+|ref=[^&]+|source=[^&]+)", "", url)
    return url.rstrip("/").lower()


class JobDeduplicator:
    """
    Two-tier deduplication:
    1. Exact URL match (same job page)
    2. Fuzzy slug match (title+company+location hash, ignoring seniority words)
    """

    def __init__(self):
        self._url_seen: Dict[str, dict] = {}
        self._slug_seen: Dict[str, dict] = {}

    def add(self, job: dict) -> Tuple[bool, Optional[str]]:
        """
        Add a job. Returns (is_duplicate, duplicate_reason).
        Keeps the version with the highest confidence/source score.
        """
        url = _url_key(job.get("apply_url") or job.get("url") or "")
        title = job.get("title") or ""
        company = job.get("company") or ""
        location = job.get("location") or ""

        # Tier 1: URL dedup
        if url and url in self._url_seen:
            return True, "duplicate_url"

        # Tier 2: content slug dedup
        if title and company:
            slug = _slug(title, company, location)
            if slug in self._slug_seen:
                existing = self._slug_seen[slug]
                # Keep higher confidence
                if _score(job) > _score(existing):
                    self._slug_seen[slug] = job
                    if url:
                        self._url_seen[url] = job
                return True, "duplicate_content"

        # Not a duplicate — record it
        if url:
            self._url_seen[url] = job
        if title and company:
            slug = _slug(title, company, location)
            self._slug_seen[slug] = job

        return False, None

    def deduplicate(self, jobs: List[dict]) -> List[dict]:
        """Filter a list of jobs, returning unique ones."""
        seen_urls: Dict[str, int] = {}
        seen_slugs: Dict[str, int] = {}
        result: List[dict] = []
        best: Dict[str, dict] = {}

        for job in jobs:
            url = _url_key(job.get("apply_url") or job.get("url") or "")
            title = job.get("title") or ""
            company = job.get("company") or ""
            location = job.get("location") or ""

            is_dup = False
            key = None

            if url and url in seen_urls:
                is_dup = True
                key = url
            elif title and company:
                slug = _slug(title, company, location)
                if slug in seen_slugs:
                    is_dup = True
                    key = slug

            if not is_dup:
                result.append(job)
                if url:
                    seen_urls[url] = len(result) - 1
                if title and company:
                    slug = _slug(title, company, location)
                    seen_slugs[slug] = len(result) - 1
            # If duplicate but better score, replace
            elif key:
                idx = seen_urls.get(key) or seen_slugs.get(key)
                if idx is not None and _score(job) > _score(result[idx]):
                    result[idx] = job

        return result


def _score(job: dict) -> float:
    return float(job.get("confidence", 0) or job.get("score", 0) or 0)


def deduplicate_jobs(jobs: List[dict]) -> List[dict]:
    """Convenience function — deduplicate a flat list of job dicts."""
    return JobDeduplicator().deduplicate(jobs)
