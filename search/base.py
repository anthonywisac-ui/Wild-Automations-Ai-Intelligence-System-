from dataclasses import dataclass, field
from typing import Optional, Any, Dict


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    score: float = 0.7
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobRecord:
    title: str
    company: str
    location: str
    remote: bool
    salary: Optional[str]
    posted: Optional[str]
    description: str
    apply_url: str
    source: str
    confidence: int = 0
