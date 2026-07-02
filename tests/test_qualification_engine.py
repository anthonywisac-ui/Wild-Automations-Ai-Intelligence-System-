"""
M1.5 validation — Qualification Engine.
Run: python -m tests.test_qualification_engine

Verifies:
  - every business gets 9 independent dimensions (score/confidence/evidence/explanation)
  - service-specific profiles work via config
  - competitors/marketplaces/directories/gov/software are rejected with structured reasons
  - good buyers qualify with tiered enrichment depth
  - overall is hierarchical (one weak dim can't hide a hard reject)
"""
from __future__ import annotations
import sys
from core import qualification_engine as qe

DIMS = ["buyer", "service", "business", "digital", "marketing", "commercial",
        "geographic", "contact", "risk"]


def _rec(title, category="", location="Dubai", rating=None, review_count=None,
         website=None, phone=None, post_text=""):
    return {"title": title, "description": "",
            "metadata": {"type": "lead", "category": category, "location": location,
                         "rating": rating, "review_count": review_count,
                         "website": website, "phone": phone, "post_text": post_text}}


def run() -> int:
    passed = failed = 0
    fails = []

    def check(name, cond):
        nonlocal passed, failed
        if cond:
            passed += 1
        else:
            failed += 1
            fails.append(name)

    SVC = "social media marketing agency"

    # 1. structure: every business gets all 9 dimensions with all 4 fields
    r = qe.qualify(_rec("Bright Smile Dental Clinic", "dental clinic",
                        rating=4.2, review_count=623, website="x.com", phone="123"), SVC)
    check("has all 9 dimensions", set(r.dimensions.keys()) == set(DIMS))
    for d in DIMS:
        cell = r.dimensions[d]
        check(f"{d} has score/confidence/evidence/explanation",
              all(k in cell for k in ("score", "confidence", "evidence", "explanation")))

    # 2. good buyer (dental clinic) qualifies for a marketing agency
    check("dental clinic qualifies", r.qualified)
    check("dental clinic full/standard enrichment",
          r.decision in (qe.DECISION_FULL, qe.DECISION_STANDARD))
    check("service fit high", r.dimensions["service"]["score"] >= 90)

    # 3. service-specific: SAME clinic is NOT a target for immigration consultant
    #    (default profile: no target industries -> neutral, not a perfect fit)
    r_imm = qe.qualify(_rec("Bright Smile Dental Clinic", "dental clinic",
                            review_count=623, website="x.com", phone="1"), "immigration consultant")
    check("different service -> different profile handling",
          r_imm.dimensions["service"]["score"] < r.dimensions["service"]["score"])

    # 4. competitor rejected with structured reason
    rc = qe.qualify(_rec("Peak Digital Marketing Agency", "marketing agency"), SVC)
    check("competitor rejected", not rc.qualified)
    check("competitor reason present", qe.REJECT_COMPETITOR in rc.rejection_reasons)
    check("competitor risk high", rc.dimensions["risk"]["score"] >= 90)

    # 5. marketplace / directory / government / software rejected
    for title, cat, code in [
        ("Dubizzle Listings", "marketplace", qe.REJECT_MARKETPLACE),
        ("Yellow Pages UAE", "directory", qe.REJECT_DIRECTORY),
        ("Ministry of Health", "government authority", qe.REJECT_GOVERNMENT),
        ("Acme IT Solutions software", "software company", qe.REJECT_SOFTWARE_VENDOR),
    ]:
        res = qe.qualify(_rec(title, cat), SVC)
        check(f"{code} rejected", not res.qualified and code in res.rejection_reasons)

    # 6. hierarchy: a competitor with an otherwise-strong footprint still rejects
    strong_comp = qe.qualify(_rec("Elite SEO Agency", "seo agency",
                                  rating=4.9, review_count=2000, website="x", phone="1"), SVC)
    check("strong-footprint competitor still rejected (no hiding)", not strong_comp.qualified)

    # 7. tiered depth mapping is coherent
    check("depth maps to decision", qe.DECISION_DEPTH[r.decision] == r.depth)

    # 8. blacklist band exists for worst cases
    check("competitor overall below reject threshold", rc.overall < 40)

    total = passed + failed
    print("=" * 66)
    print("M1.5 VALIDATION REPORT — Qualification Engine")
    print("=" * 66)
    print(f"checks passed : {passed}/{total}  ({passed/total:.1%})")
    for f in fails:
        print("  FAIL:", f)
    print("-" * 66)
    print("sample audit — Bright Smile Dental Clinic (service: marketing agency):")
    print(f"  overall={r.overall}  decision={r.decision}  profile={r.profile_used}")
    for d in DIMS:
        c = r.dimensions[d]
        print(f"  {d:11}: {c['score']:5.1f}  ({c['explanation']})")
    print("-" * 66)
    print("sample reject — Peak Digital Marketing Agency:")
    print(f"  overall={rc.overall}  decision={rc.decision}  reasons={rc.rejection_reasons}")
    print("=" * 66)
    ok = failed == 0
    print("RESULT:", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
