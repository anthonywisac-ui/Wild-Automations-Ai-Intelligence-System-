import math
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass, field


@dataclass
class ScoringConfig:
    """Configuration for scoring weights per bot."""
    weights: Dict[str, float] = field(default_factory=lambda: {
        "keyword": 1.0,
        "urgency": 1.0,
        "price_drop": 0.8,
        "recency": 0.6,
        "seller_type": 0.4,
    })
    seller_type_scores: Dict[str, float] = field(default_factory=lambda: {
        "dealer": 0.8,
        "private": 1.0,
        "unknown": 0.5,
    })
    recency_decay_factor: float = 0.5  # per hour exponential decay
    min_score: float = 0.0
    max_score: float = 10.0
    normalize: bool = True


class ScoringEngine:
    """
    Weighted scoring engine for AI bot alerts.

    Factors:
        - keyword_match: 0.0 - 1.0 (higher = better match)
        - urgency: 0.0 - 1.0 (higher = urgent)
        - price_drop: 0.0 - 1.0 (higher = bigger drop)
        - recency: datetime or hours ago (more recent = higher score)
        - seller_type: string (mapped via seller_type_scores)

    Each factor is multiplied by its weight, then summed to a raw score.
    Optionally normalized to min_score..max_score range.
    """

    def __init__(self, config: Optional[ScoringConfig] = None):
        self.config = config or ScoringConfig()

    def _compute_recency_score(self, recency: Union[datetime, float]) -> float:
        """Convert recency to a score between 0 and 1."""
        if isinstance(recency, datetime):
            now = datetime.now(timezone.utc)
            delta = now - recency
            hours = delta.total_seconds() / 3600.0
        else:
            hours = float(recency)  # already in hours

        # Exponential decay: score = exp(-decay * hours)
        if hours < 0:
            return 1.0
        return math.exp(-self.config.recency_decay_factor * max(hours, 0))

    def _get_seller_score(self, seller_type: str) -> float:
        """Map seller type to score."""
        return self.config.seller_type_scores.get(seller_type, 0.5)

    def compute_score(self, alert: Dict[str, Any]) -> float:
        """
        Compute a weighted score for a single alert.

        Expected keys in alert dict:
            - keyword_match: float (0-1)
            - urgency: float (0-1)
            - price_drop: float (0-1)
            - recency: datetime or float (hours ago)
            - seller_type: str (optional, defaults to 'unknown')
        """
        weights = self.config.weights

        # Extract factors with defaults
        kw_score = float(alert.get("keyword_match", 0.0))
        urgency = float(alert.get("urgency", 0.0))
        price_drop = float(alert.get("price_drop", 0.0))

        recency_raw = alert.get("recency")
        if recency_raw is None:
            recency_score = 0.0
        else:
            recency_score = self._compute_recency_score(recency_raw)

        seller_type = alert.get("seller_type", "unknown")
        seller_score = self._get_seller_score(seller_type)

        # Weighted sum
        raw_score = (
            weights.get("keyword", 1.0) * kw_score +
            weights.get("urgency", 1.0) * urgency +
            weights.get("price_drop", 0.8) * price_drop +
            weights.get("recency", 0.6) * recency_score +
            weights.get("seller_type", 0.4) * seller_score
        )

        # Normalize to min_score..max_score if requested
        if self.config.normalize:
            # Theoretical max score = sum of all weights (each factor max 1)
            max_possible = sum(weights.values())
            if max_possible > 0:
                normalized = raw_score / max_possible
                # Scale to [min_score, max_score]
                min_s = self.config.min_score
                max_s = self.config.max_score
                final_score = min_s + normalized * (max_s - min_s)
                return round(final_score, 3)
        return round(raw_score, 3)

    def rank_alerts(
        self,
        alerts: List[Dict[str, Any]],
        reverse: bool = True,
        include_score: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Rank a list of alerts by score.

        Args:
            alerts: List of alert dicts. Each dict should contain the factor keys.
            reverse: If True, highest score first.
            include_score: If True, adds '_score' key to each alert.

        Returns:
            Sorted list of alerts (with score included if requested).
        """
        scored = []
        for alert in alerts:
            score = self.compute_score(alert)
            item = alert.copy()
            if include_score:
                item["_score"] = score
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=reverse)
        return [item for _, item in scored]

    def update_weights(self, bot_specific_weights: Dict[str, float]) -> None:
        """Update weights for this engine instance (e.g., per bot)."""
        self.config.weights.update(bot_specific_weights)