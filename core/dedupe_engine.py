import hashlib
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from urllib.parse import urlparse, urlunparse
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field

try:
    from rapidfuzz import fuzz
except ImportError:
    # Fallback to simple ratio if rapidfuzz not installed
    class fuzz:
        @staticmethod
        def ratio(s1, s2):
            from difflib import SequenceMatcher
            return int(SequenceMatcher(None, s1, s2).ratio() * 100)


@dataclass
class DedupConfig:
    url_normalize: bool = True
    content_fingerprint_ngram: int = 5          # number of tokens for fingerprint
    content_fingerprint_stopwords: bool = True
    title_fuzzy_threshold: int = 85             # 0-100
    max_history_days: int = 30                  # retain records for this many days
    store_urls_only: bool = False               # if True, only hash URLs, not content


class DedupEngine:
    """
    Deduplication engine using URL hashing, content fingerprinting,
    and fuzzy title matching.
    """

    def __init__(self, config: Optional[DedupConfig] = None):
        self.config = config or DedupConfig()
        # In-memory storage: maps hash -> timestamp and metadata
        self._url_hashes: Dict[str, datetime] = {}
        self._content_fingerprints: Dict[str, datetime] = {}
        self._title_hashes: Dict[str, datetime] = {}  # exact title hash for quick lookup
        self._all_titles: List[Tuple[str, datetime]] = []  # for fuzzy matching
        self._stopwords = {
            "the", "a", "an", "of", "for", "and", "or", "on", "at", "to", "in",
            "with", "without", "by", "from", "up", "down", "off", "over", "under"
        }

    def _normalize_url(self, url: str) -> str:
        """Normalize URL: lowercase, remove fragments, sort query params."""
        if not self.config.url_normalize:
            return url
        parsed = urlparse(url)
        # lower netloc and path
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip('/')
        # Sort query parameters
        query = parsed.query
        query_parts = []
        if query:
            params = query.split('&')
            params.sort()
            query = '&'.join(params)
        # rebuild without fragment
        normalized = urlunparse((parsed.scheme.lower(), netloc, path, parsed.params, query, ''))
        return normalized

    def _url_hash(self, url: str) -> str:
        """Compute MD5 hash of normalized URL."""
        norm = self._normalize_url(url)
        return hashlib.md5(norm.encode('utf-8')).hexdigest()

    def _extract_tokens(self, text: str) -> List[str]:
        """Tokenize and optionally remove stopwords."""
        if not text:
            return []
        # Lowercase and split on non-alphanumeric
        words = re.findall(r'\b[a-z0-9]+\b', text.lower())
        if self.config.content_fingerprint_stopwords:
            words = [w for w in words if w not in self._stopwords]
        return words

    def _content_fingerprint(self, content: Union[str, Dict]) -> str:
        """
        Compute a fingerprint from content.
        If content is dict, JSON dump then process.
        """
        if isinstance(content, dict):
            content = json.dumps(content, sort_keys=True)
        elif not isinstance(content, str):
            content = str(content)

        tokens = self._extract_tokens(content)
        if not tokens:
            return hashlib.md5(content.encode('utf-8')).hexdigest()

        # Use n-gram hashing: take first N tokens and hash them
        ngram_size = self.config.content_fingerprint_ngram
        if len(tokens) >= ngram_size:
            # Use first ngram as fingerprint
            ngram = " ".join(tokens[:ngram_size])
        else:
            ngram = " ".join(tokens)
        # Hash the ngram
        return hashlib.md5(ngram.encode('utf-8')).hexdigest()

    def _clean_title(self, title: str) -> str:
        """Remove extra spaces, punctuation for title comparison."""
        if not title:
            return ""
        title = re.sub(r'\s+', ' ', title).strip()
        # Remove common prefixes/suffixes like "Listing:"
        title = re.sub(r'^(listing|ad|item|post):\s*', '', title, flags=re.I)
        return title

    def _is_title_duplicate(self, title: str, threshold: int = None) -> Tuple[bool, str]:
        """
        Check if title is fuzzy duplicate of existing titles.
        Returns (is_duplicate, best_match_title)
        """
        if not title:
            return False, ""
        cleaned = self._clean_title(title)
        if not cleaned:
            return False, ""

        # Exact hash check first
        exact_hash = hashlib.md5(cleaned.lower().encode('utf-8')).hexdigest()
        if exact_hash in self._title_hashes:
            return True, cleaned

        # Fuzzy search over recent titles
        threshold = threshold or self.config.title_fuzzy_threshold
        best_ratio = 0
        best_match = ""
        # Limit search to recent (e.g., last 1000 or last few days)
        for stored_title, dt in self._all_titles:
            if stored_title:
                ratio = fuzz.ratio(cleaned.lower(), stored_title.lower())
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = stored_title
                    if best_ratio >= threshold:
                        break
        if best_ratio >= threshold:
            return True, best_match
        return False, ""

    def is_duplicate(self, url: str, content: Any = None, title: str = None) -> Tuple[bool, Dict]:
        """
        Check if the given URL/content/title is a duplicate.
        Returns (is_duplicate, details_dict)
        """
        details = {"url": url, "reason": "", "matched": ""}

        # 1. URL hash check
        url_h = self._url_hash(url)
        if url_h in self._url_hashes:
            details["reason"] = "url_hash"
            details["matched"] = "same URL"
            return True, details

        # 2. If store_urls_only, no further checks
        if self.config.store_urls_only:
            return False, details

        # 3. Content fingerprint
        if content is not None:
            c_fp = self._content_fingerprint(content)
            if c_fp in self._content_fingerprints:
                details["reason"] = "content_fingerprint"
                details["matched"] = "similar content"
                return True, details

        # 4. Title fuzzy match
        if title:
            is_dup, match_title = self._is_title_duplicate(title)
            if is_dup:
                details["reason"] = "title_fuzzy"
                details["matched"] = f"title: {match_title[:50]}"
                return True, details

        return False, details

    def add_record(self, url: str, content: Any = None, title: str = None) -> None:
        """Add a record to the history to prevent future duplicates."""
        now = datetime.utcnow()

        # Add URL hash
        url_h = self._url_hash(url)
        self._url_hashes[url_h] = now

        # Add content fingerprint
        if content is not None and not self.config.store_urls_only:
            c_fp = self._content_fingerprint(content)
            self._content_fingerprints[c_fp] = now

        # Add title exact hash and fuzzy list
        if title:
            cleaned = self._clean_title(title)
            if cleaned:
                exact_hash = hashlib.md5(cleaned.lower().encode('utf-8')).hexdigest()
                self._title_hashes[exact_hash] = now
                self._all_titles.append((cleaned, now))

        # Clean old records periodically (optional)
        self._clean_old_records()

    def _clean_old_records(self, max_age_days: int = None):
        """Remove records older than max_age_days to prevent unbounded growth."""
        if max_age_days is None:
            max_age_days = self.config.max_history_days
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)

        # Clean URL hashes
        for key in list(self._url_hashes.keys()):
            if self._url_hashes[key] < cutoff:
                del self._url_hashes[key]

        # Clean content fingerprints
        for key in list(self._content_fingerprints.keys()):
            if self._content_fingerprints[key] < cutoff:
                del self._content_fingerprints[key]

        # Clean title hashes
        for key in list(self._title_hashes.keys()):
            if self._title_hashes[key] < cutoff:
                del self._title_hashes[key]

        # Clean fuzzy title list
        self._all_titles = [(t, dt) for t, dt in self._all_titles if dt >= cutoff]

    def reset(self):
        """Clear all stored history."""
        self._url_hashes.clear()
        self._content_fingerprints.clear()
        self._title_hashes.clear()
        self._all_titles.clear()