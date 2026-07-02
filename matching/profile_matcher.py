"""
Profile Matcher — scores opportunity vs user profile across multiple dimensions.
Documented in: docs/NOTIFICATION ENGINE.md § 2.1

No external dependencies (sklearn/numpy optional — fallback to pure Python).

Usage:
    from matching.profile_matcher import ProfileMatcher
    matcher = ProfileMatcher()
    result = await matcher.match_opportunity(profile, opportunity, domain="jobs")
    # result = {"overall_score": 0.85, "dimensions": {...}, "domain": "jobs"}
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ProfileMatcher:
    """
    Weighted multi-dimension scorer.
    Weights sum to 1.0 for each domain.
    """

    # Default weights for jobs domain
    _JOB_WEIGHTS = {
        "location": 0.25,
        "budget": 0.20,
        "skills": 0.20,
        "education": 0.15,
        "experience": 0.10,
        "visa": 0.10,
    }

    # Default weights for real_estate domain
    _RE_WEIGHTS = {
        "location": 0.35,
        "budget": 0.35,
        "type": 0.15,
        "size": 0.15,
    }

    # Default weights for vehicles domain
    _VEH_WEIGHTS = {
        "location": 0.20,
        "budget": 0.40,
        "make_model": 0.25,
        "year": 0.15,
    }

    # Education level numeric mapping
    _EDU_LEVELS = {
        "high_school": 1, "diploma": 2, "bachelor": 2,
        "master": 3, "phd": 4,
    }

    # Experience level → minimum years
    _EXP_MAP = {
        "entry": 0, "junior": 1, "mid": 3, "senior": 6,
        "lead": 9, "executive": 12,
    }

    # ──────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ──────────────────────────────────────────────────────────────────────────

    async def match_opportunity(
        self,
        profile: Dict[str, Any],
        opportunity: Dict[str, Any],
        domain: str = "jobs",
    ) -> Dict[str, Any]:
        """Return overall_score (0-1) and per-dimension breakdown."""
        try:
            if domain == "jobs":
                return await self._match_job(profile, opportunity)
            elif domain == "real_estate":
                return await self._match_real_estate(profile, opportunity)
            elif domain == "vehicles":
                return await self._match_vehicle(profile, opportunity)
            else:
                return await self._match_general(profile, opportunity, domain)
        except Exception as exc:
            logger.error("profile_matcher error domain=%s: %s", domain, exc)
            return {"overall_score": 0.5, "dimensions": {}, "domain": domain, "error": str(exc)}

    # ──────────────────────────────────────────────────────────────────────────
    # Domain matchers
    # ──────────────────────────────────────────────────────────────────────────

    async def _match_job(self, profile: Dict, job: Dict) -> Dict:
        w = self._JOB_WEIGHTS
        scores = {
            "location": self._match_location(
                profile.get("preferred_countries", []),
                job.get("location", {}),
            ),
            "budget": self._match_budget(
                profile.get("salary_range", {}),
                job.get("salary", {}),
            ),
            "skills": self._match_skills(
                profile.get("skills", []),
                job.get("skills_required", []),
            ),
            "education": self._match_education(
                profile.get("education", {}),
                job.get("education_level", ""),
            ),
            "experience": self._match_experience(
                profile.get("experience_years", 0),
                job.get("experience_level", ""),
            ),
            "visa": self._match_visa(
                profile.get("visa_status", ""),
                job.get("visa_sponsorship", False),
            ),
        }
        overall = sum(scores[k] * w[k] for k in w)
        return {"overall_score": round(overall, 3), "dimensions": scores, "domain": "jobs"}

    async def _match_real_estate(self, profile: Dict, prop: Dict) -> Dict:
        w = self._RE_WEIGHTS
        preferred_locs = profile.get("preferred_countries", []) + profile.get("preferred_cities", [])
        scores = {
            "location": self._match_location(preferred_locs, prop.get("location", {})),
            "budget": self._match_budget(
                profile.get("budget_range", {}),
                {"min": prop.get("price", 0), "max": prop.get("price", 0),
                 "currency": prop.get("currency", "AED")},
            ),
            "type": self._match_text_list(
                profile.get("property_types", []),
                prop.get("property_type", ""),
            ),
            "size": self._match_numeric_range(
                profile.get("min_size_sqft", 0),
                profile.get("max_size_sqft", 99999),
                prop.get("area_sqft", 0),
            ),
        }
        overall = sum(scores[k] * w[k] for k in w)
        return {"overall_score": round(overall, 3), "dimensions": scores, "domain": "real_estate"}

    async def _match_vehicle(self, profile: Dict, vehicle: Dict) -> Dict:
        w = self._VEH_WEIGHTS
        scores = {
            "location": self._match_location(
                profile.get("preferred_countries", []),
                {"country": vehicle.get("location", "")},
            ),
            "budget": self._match_budget(
                profile.get("budget_range", {}),
                {"min": vehicle.get("price", 0), "max": vehicle.get("price", 0),
                 "currency": vehicle.get("currency", "AED")},
            ),
            "make_model": self._match_text_list(
                profile.get("preferred_makes", []),
                vehicle.get("make", ""),
            ),
            "year": self._match_numeric_range(
                profile.get("min_year", 2015),
                profile.get("max_year", 2030),
                vehicle.get("year", 0),
            ),
        }
        overall = sum(scores[k] * w[k] for k in w)
        return {"overall_score": round(overall, 3), "dimensions": scores, "domain": "vehicles"}

    async def _match_general(self, profile: Dict, opportunity: Dict, domain: str) -> Dict:
        loc_score = self._match_location(
            profile.get("preferred_countries", []),
            opportunity.get("location", {}),
        )
        return {"overall_score": round(loc_score * 0.5 + 0.5, 3), "dimensions": {"location": loc_score}, "domain": domain}

    # ──────────────────────────────────────────────────────────────────────────
    # Dimension scorers (pure Python, no sklearn needed)
    # ──────────────────────────────────────────────────────────────────────────

    def _match_location(self, preferred: List[str], location: Any) -> float:
        if not preferred:
            return 0.5
        if isinstance(location, dict):
            haystack = " ".join(str(v) for v in location.values()).lower()
        else:
            haystack = str(location).lower()
        if not haystack:
            return 0.3
        for p in preferred:
            if p.lower() in haystack:
                return 1.0
        return 0.0

    def _match_budget(self, user_range: Dict, item_range: Dict) -> float:
        if not user_range or not item_range:
            return 0.5
        u_min = float(user_range.get("min", 0) or 0)
        u_max = float(user_range.get("max", 0) or 0) or float("inf")
        i_min = float(item_range.get("min", 0) or 0)
        i_max = float(item_range.get("max", 0) or 0) or float("inf")
        overlap_min = max(u_min, i_min)
        overlap_max = min(u_max, i_max)
        if overlap_min > overlap_max:
            return 0.0
        if u_max == float("inf") or i_max == float("inf"):
            return 0.6
        span = u_max - u_min
        if span <= 0:
            return 0.5
        return min(1.0, (overlap_max - overlap_min) / span)

    def _match_skills(self, user_skills: List[str], required: List[str]) -> float:
        if not required:
            return 0.5
        if not user_skills:
            return 0.0
        u = {s.lower().strip() for s in user_skills}
        r = {s.lower().strip() for s in required}
        intersection = u & r
        union = u | r
        return len(intersection) / len(union) if union else 0.0

    def _match_education(self, user_edu: Dict, required: str) -> float:
        if not required:
            return 0.5
        if not user_edu:
            return 0.0
        u_level = self._EDU_LEVELS.get(user_edu.get("level", "").lower(), 0)
        r_level = self._EDU_LEVELS.get(required.lower(), 0)
        if u_level == 0:
            return 0.0
        if r_level == 0:
            return 0.5
        if u_level >= r_level:
            return 1.0
        return u_level / r_level

    def _match_experience(self, user_years: Any, required_level: str) -> float:
        if not required_level:
            return 0.5
        required_years = self._EXP_MAP.get(required_level.lower())
        if required_years is None:
            return 0.5
        if required_years == 0:
            return 1.0
        user_yrs = float(user_years or 0)
        if user_yrs >= required_years:
            return 1.0
        return user_yrs / required_years

    def _match_visa(self, user_visa: str, visa_sponsorship: bool) -> float:
        if visa_sponsorship:
            return 1.0  # job offers sponsorship — great for anyone needing it
        if user_visa.lower() in ("none", "visitor", ""):
            return 0.3
        return 0.8

    def _match_text_list(self, preferred: List[str], value: str) -> float:
        if not preferred:
            return 0.5
        if not value:
            return 0.3
        v = value.lower()
        return 1.0 if any(p.lower() in v for p in preferred) else 0.0

    def _match_numeric_range(self, lo: float, hi: float, value: float) -> float:
        if not value:
            return 0.5
        if lo <= value <= hi:
            return 1.0
        gap = min(abs(value - lo), abs(value - hi))
        span = hi - lo if hi > lo else 1
        return max(0.0, 1.0 - gap / span)
