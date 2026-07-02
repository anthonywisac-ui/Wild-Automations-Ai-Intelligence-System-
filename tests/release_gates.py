"""
Release Gates — production acceptance harness.
Run: python -m tests.release_gates

Drives the FROZEN modules (Qualification Engine, Ticket Segmentation, Evidence,
Lead Explanation) over the golden dataset and certifies the release gates with
measurable numbers. DeepEval/RAGAS PATTERNS adopted natively (golden set,
precision/faithfulness, contamination) — no external deps, no copied code.

Gates:
    seller_contamination < 1%
    buyer_precision      > 95%
    duplicate_rate       < 1%
    evidence_coverage    > 90%
    explanation_quality  > 90%
    faithfulness         = 100%   (no hallucinated evidence)
Website/phone coverage are enrichment-dependent (need a live crawl) and are
reported on the golden set as pre-crawl discoverability, not certified here.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from core import qualification_engine as qe
from core import lead_explanation, ticket_segmentation

_GOLDEN = Path(__file__).resolve().parent / "golden_dataset.json"


def _load():
    d = json.loads(_GOLDEN.read_text(encoding="utf-8-sig"))
    return d.get("_meta", {}).get("service", ""), d["records"]


def _to_record(g):
    return {"title": g["name"], "description": "",
            "metadata": {"type": "lead", "category": g["category"],
                         "location": g["location"], "rating": g.get("rating"),
                         "review_count": g.get("review_count"),
                         "website": g.get("website") or None,
                         "phone": g.get("phone") or None,
                         "_service": None}}


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def run() -> int:
    service, records = _load()
    accepted, rejected = [], []

    for g in records:
        rec = _to_record(g)
        rec["metadata"]["_service"] = service
        result = qe.qualify(rec, service=service)
        ticket_segmentation.enrich_record(rec)
        rec["metadata"]["qualification"] = result.as_dict()
        rec["metadata"]["ticket"] = result.dimensions and rec["metadata"].get("ticket")
        entry = {"g": g, "rec": rec, "result": result}
        if result.qualified:
            accepted.append(entry)
        else:
            rejected.append(entry)

    n_acc = len(accepted)
    # ── contamination + precision ──
    true_buyers_acc = [e for e in accepted if e["g"]["is_buyer"]]
    non_buyers_acc = [e for e in accepted if not e["g"]["is_buyer"]]
    contamination = (len(non_buyers_acc) / n_acc) if n_acc else 0.0
    precision = (len(true_buyers_acc) / n_acc) if n_acc else 0.0
    # recall (informational)
    all_buyers = [g for g in records if g["is_buyer"]]
    recall = len(true_buyers_acc) / len(all_buyers) if all_buyers else 0.0

    # ── duplicate rate (normalized name+location on accepted) ──
    seen, dupes = set(), 0
    for e in accepted:
        key = _norm(e["g"]["name"]) + "|" + _norm(e["g"]["location"])
        if key in seen:
            dupes += 1
        seen.add(key)
    dup_rate = dupes / n_acc if n_acc else 0.0

    # ── evidence coverage + explanation quality + faithfulness ──
    ev_ok = expl_ok = faithful = 0
    for e in accepted:
        expl = lead_explanation.explain(e["rec"])
        e["explanation"] = expl
        if expl.get("why_buyer"):
            ev_ok += 1
        if lead_explanation.is_quality(expl):
            expl_ok += 1
        # faithfulness (RAGAS pattern): every 'why_buyer' reason must trace back
        # to a real input field / qualification evidence — no invented claims.
        blob = (json.dumps(e["rec"]["metadata"], ensure_ascii=False)
                + " " + json.dumps(e["result"].as_dict(), ensure_ascii=False)).lower()
        reasons = expl.get("why_buyer", [])
        ok = all(any(w in blob for w in re.findall(r"[a-z]{4,}", r.lower())) for r in reasons) if reasons else True
        if ok:
            faithful += 1
    ev_cov = ev_ok / n_acc if n_acc else 0.0
    expl_q = expl_ok / n_acc if n_acc else 0.0
    faith = faithful / n_acc if n_acc else 0.0

    # ── competitor isolation: no competitor in accepted ──
    comp_in_acc = [e for e in accepted if e["g"]["type"] == "competitor"]

    # ── end-to-end export contamination: run the actual export layer over ALL
    # golden records and assert zero non-buyers reach the CRM export ──
    from core import lead_export
    wrapped = []
    for g in records:
        rec = _to_record(g); rec["metadata"]["_service"] = service
        res = qe.qualify(rec, service=service)
        ticket_segmentation.enrich_record(rec)
        rec["metadata"]["qualification"] = res.as_dict()
        if res.qualified:
            rec["metadata"]["explanation"] = lead_explanation.explain(rec)
        wrapped.append({"original_data": rec, "_type": g["type"], "_is_buyer": g["is_buyer"]})
    exported = lead_export.rows(wrapped)
    exported_names = {r["name"] for r in exported}
    export_non_buyers = [g for g in records
                         if not g["is_buyer"] and g["name"] in exported_names]
    export_contam = len(export_non_buyers) / len(exported) if exported else 0.0

    # pre-crawl discoverability (reported, not gated)
    web_cov = sum(1 for e in accepted if e["g"].get("website")) / n_acc if n_acc else 0.0
    phone_cov = sum(1 for e in accepted if e["g"].get("phone")) / n_acc if n_acc else 0.0

    gates = [
        ("seller_contamination < 1%", contamination, contamination < 0.01, f"{contamination:.2%}"),
        ("buyer_precision > 95%", precision, precision > 0.95, f"{precision:.2%}"),
        ("duplicate_rate < 1%", dup_rate, dup_rate < 0.01, f"{dup_rate:.2%}"),
        ("evidence_coverage > 90%", ev_cov, ev_cov > 0.90, f"{ev_cov:.2%}"),
        ("explanation_quality > 90%", expl_q, expl_q > 0.90, f"{expl_q:.2%}"),
        ("faithfulness = 100%", faith, faith >= 1.0, f"{faith:.2%}"),
        ("competitor_isolation (0 in leads)", len(comp_in_acc), len(comp_in_acc) == 0, str(len(comp_in_acc))),
        ("export_contamination < 1%", export_contam, export_contam < 0.01, f"{export_contam:.2%}"),
    ]

    print("=" * 70)
    print("RELEASE GATES — Golden Dataset Validation")
    print("=" * 70)
    print(f"records={len(records)}  accepted(leads)={n_acc}  rejected/isolated={len(rejected)}")
    print(f"buyer_recall (informational) = {recall:.2%}")
    print("-" * 70)
    all_pass = True
    for name, _, ok, disp in gates:
        all_pass &= ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:38} = {disp}")
    print("-" * 70)
    print(f"  (report) pre-crawl website discoverability = {web_cov:.2%}")
    print(f"  (report) pre-crawl phone discoverability   = {phone_cov:.2%}")
    if non_buyers_acc:
        print("  CONTAMINATION LEAKS:")
        for e in non_buyers_acc:
            print(f"    - {e['g']['name']} ({e['g']['type']}) decision={e['result'].decision}")
    print("=" * 70)
    print("RELEASE:", "ALL GATES PASS ✅" if all_pass else "GATES FAILED ❌")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(run())
