"""
Lead Export — CRM / automation-ready output.

Flattens qualified, explained leads into rows that can be sent directly to a CRM,
an outreach bot, or a scraper without manual cleaning. Every row carries the
answer set, scores, evidence, provenance, and trace context.

    rows(scored)      -> List[dict]   (one flat row per qualified lead)
    to_csv(scored)    -> str
    to_json(scored)   -> str
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, List

# stable column order for CSV / CRM import mapping
COLUMNS = [
    "name", "category", "location", "ticket", "qualification_score", "decision",
    "overall_confidence", "buyer_score", "service_score", "opportunity_evidence",
    "website", "phone", "whatsapp", "email", "instagram",
    "what_to_sell", "who_to_contact", "outreach_channel",
    "expected_close_probability", "spend_crawl", "spend_llm",
    "why_buyer", "trace_id", "canonical_id",
]


def _dim_score(md: Dict[str, Any], name: str) -> float:
    dims = ((md.get("qualification") or {}).get("dimensions") or {})
    return round(float((dims.get(name) or {}).get("score", 0)), 1)


def rows(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in scored:
        od = s.get("original_data") or s
        md = od.get("metadata") or {}
        if md.get("type") != "lead":
            continue
        q = md.get("qualification") or {}
        # only QUALIFIED leads are exportable — never a rejected competitor
        if not q or not q.get("qualified"):
            continue
        expl = md.get("explanation") or {}
        enr = md.get("enrichment") or {}
        out.append({
            "name": od.get("title") or md.get("name", ""),
            "category": md.get("category", ""),
            "location": md.get("location", ""),
            "ticket": md.get("ticket") or (md.get("ticket_profile") or {}).get("ticket", ""),
            "qualification_score": q.get("overall", 0),
            "decision": q.get("decision", ""),
            "overall_confidence": expl.get("confidence", ""),
            "buyer_score": _dim_score(md, "buyer"),
            "service_score": _dim_score(md, "service"),
            "opportunity_evidence": "; ".join(expl.get("evidence", [])),
            "website": md.get("website") or enr.get("website", ""),
            "phone": md.get("phone") or enr.get("phone", ""),
            "whatsapp": md.get("whatsapp") or enr.get("whatsapp", ""),
            "email": md.get("email") or enr.get("email", ""),
            "instagram": (enr.get("socials") or {}).get("instagram", ""),
            "what_to_sell": expl.get("what_to_sell", ""),
            "who_to_contact": expl.get("who_to_contact", ""),
            "outreach_channel": expl.get("outreach_channel", ""),
            "expected_close_probability": expl.get("expected_close_probability", ""),
            "spend_crawl": expl.get("spend_crawl", ""),
            "spend_llm": expl.get("spend_llm", ""),
            "why_buyer": "; ".join(expl.get("why_buyer", [])),
            "trace_id": md.get("trace_id", ""),
            "canonical_id": md.get("canonical_id", ""),
        })
    # rank by qualification score desc (CRM shows hottest first; still sortable
    # by any independent column downstream)
    out.sort(key=lambda r: float(r.get("qualification_score") or 0), reverse=True)
    return out


def to_csv(scored: List[Dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, extrasaction="ignore")
    w.writeheader()
    for r in rows(scored):
        w.writerow(r)
    return buf.getvalue()


def to_json(scored: List[Dict[str, Any]]) -> str:
    return json.dumps(rows(scored), ensure_ascii=False, indent=2)
