"""M1 validation — Ticket Segmentation Engine. Run: python -m tests.test_ticket_segmentation"""
from __future__ import annotations
import sys
from core import ticket_segmentation as ts

# (category, expected_tier)
CASES = [
    # High
    ("Hospital", "High"), ("Real Estate Developer", "High"), ("Large Law Firm", "High"),
    ("Enterprise SaaS", "High"), ("Manufacturing company", "High"), ("University", "High"),
    ("Airline", "High"), ("5-star Hotel", "High"), ("Luxury brand", "High"),
    ("Construction company", "High"), ("Automotive group", "High"),
    # Mid
    ("Dental Clinic", "Mid"), ("Gym", "Mid"), ("Restaurant", "Mid"),
    ("Accounting Firm", "Mid"), ("Travel Agency", "Mid"), ("Furniture Store", "Mid"),
    ("Education Institute", "Mid"), ("Retail chain", "Mid"), ("Medical center", "Mid"),
    # Low
    ("Salon", "Low"), ("Cafe", "Low"), ("Local shop", "Low"), ("Repair shop", "Low"),
    ("Small ecommerce store", "Low"), ("Home service", "Low"), ("Barber shop", "Low"),
]


def run() -> int:
    passed = failed = 0
    failures = []
    for category, expected in CASES:
        p = ts.segment(category)
        ok = p.ticket == expected
        passed += ok
        if not ok:
            failed += 1
            failures.append(f"{category!r}: got {p.ticket}, expected {expected} (matched={p.matched_category!r})")

    # signal overrides
    checks = [
        ("employees override", ts.segment("Cafe", employees=500).ticket == "High"),
        ("revenue override", ts.segment("Salon", revenue=20_000_000).ticket == "High"),
        ("low employees override", ts.segment("Hospital", employees=3).ticket == "Low"),
        ("review volume nudge", ts.segment("Salon", review_count=5000).ticket == "Mid"),
        ("unknown → Mid conservative", ts.segment("zorbthe flimwidget").ticket == "Mid"),
        ("profile completeness", all(getattr(ts.segment("Dental Clinic"), f)
            for f in ("expected_budget", "decision_maker", "outreach", "sales_cycle"))),
    ]
    for name, ok in checks:
        passed += ok
        if not ok:
            failed += 1
            failures.append(f"signal check failed: {name}")

    total = passed + failed
    acc = passed / total if total else 0.0
    print("=" * 64)
    print("M1 VALIDATION REPORT — Ticket Segmentation Engine")
    print("=" * 64)
    print(f"category cases : {len(CASES)}")
    print(f"signal checks  : {len(checks)}")
    print(f"passed         : {passed}/{total}  ({acc:.1%})")
    for f in failures:
        print("  FAIL:", f)
    # sample full profile
    p = ts.segment("Dental Clinic")
    print("-" * 64)
    print("sample profile — Dental Clinic:")
    for k, v in p.as_dict().items():
        print(f"  {k:16}: {v}")
    print("=" * 64)
    ok = failed == 0
    print("RESULT:", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
