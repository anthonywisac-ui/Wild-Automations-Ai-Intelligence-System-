"""
Intent Analyzer — find the lead hidden in a LinkedIn comment / post.

Given a person's profile headline + their comment/post text, it decides whether
THIS is a buying signal, how hot, and — crucially — states the BASIS: exactly
which words/phrases triggered the verdict. Deterministic and explainable; an
optional LLM pass can refine wording but never invents the basis.

    analyze(profile_headline, text) -> {
        is_lead, temperature (hot|warm|cold), intent_score 0..1,
        signals[], basis (human-readable), sentiment, is_seller
    }
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

# Buyer signals grouped by strength — a person EXPRESSING A NEED.
_HOT = [
    "looking for", "need a", "need an", "need help", "in need of", "hiring a",
    "who can help", "anyone recommend", "recommendations for", "recommend a",
    "any recommendations", "seeking a", "searching for", "want to hire",
    "need someone", "dm me", "reach out", "get a quote", "budget for",
]
_WARM = [
    "struggling with", "not working", "frustrated with", "tired of", "our website",
    "we need", "we're looking", "planning to", "thinking about", "considering",
    "how do i", "how do we", "what's the best", "suggestions", "advice on",
    "help with", "want to grow", "want more", "generate leads", "more customers",
]
# Seller / provider markers — this is a COMPETITOR, not a lead.
_SELLER = [
    "we offer", "we provide", "our services", "we help businesses", "dm us",
    "our agency", "we specialize", "book a call with", "our team", "we build",
    "contact us for", "we do", "hire us", "our clients", "we're an agency",
]
_NEG_SENTIMENT = ("bad", "worst", "terrible", "disappointed", "poor", "waste",
                  "useless", "frustrated", "annoyed", "problem", "issue", "fail")


def _hits(text: str, phrases: List[str]) -> List[str]:
    t = text.lower()
    return [p for p in phrases if p in t]


def analyze(profile_headline: str, text: str) -> Dict[str, Any]:
    headline = (profile_headline or "")
    body = (text or "")
    blob = f"{headline} {body}".lower()

    seller_hits = _hits(blob, _SELLER)
    hot_hits = _hits(body.lower(), _HOT)
    warm_hits = _hits(body.lower(), _WARM)

    # a headline that literally sells a competing service also marks a seller
    if re.search(r"\b(marketing agency|seo|social media (agency|manager)|"
                 r"digital agency|freelance marketer|smma)\b", headline.lower()):
        seller_hits = seller_hits or ["headline: competitor/service provider"]

    is_seller = bool(seller_hits) and not hot_hits
    score = min(1.0, 0.5 * len(hot_hits) + 0.25 * len(warm_hits))
    if is_seller:
        score *= 0.2

    if score >= 0.5 and not is_seller:
        temp = "hot"
    elif score >= 0.25 and not is_seller:
        temp = "warm"
    else:
        temp = "cold"

    sentiment = "negative" if any(w in blob for w in _NEG_SENTIMENT) else "neutral"
    signals = hot_hits + warm_hits

    # transparent basis
    if is_seller:
        basis = f"Marked NOT-a-lead (seller/competitor): matched {seller_hits}"
    elif signals:
        basis = (f"Buying intent [{temp}] from phrase(s): {signals}"
                 + (f"; negative-experience wording ({[w for w in _NEG_SENTIMENT if w in blob][:3]}) "
                    "suggests they're unhappy with a current provider" if sentiment == "negative" else ""))
    else:
        basis = "No explicit buying-intent phrase in the text — treated as cold/profile-only"

    return {
        "is_lead": bool(signals) and not is_seller,
        "temperature": temp,
        "intent_score": round(score, 3),
        "signals": signals,
        "basis": basis,
        "sentiment": sentiment,
        "is_seller": is_seller,
    }
