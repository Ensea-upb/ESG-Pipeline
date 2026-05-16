import csv
from pathlib import Path
from datetime import date

workspace = Path(r"EXTERNAL_AUDIT_RUNS\totalenergies_2024_e2e_test\04_manual_review_workspace\totalenergies_2024_urd")
template = workspace / "review_decisions_template.csv"
out = workspace / "review_decisions_filled.csv"

today = date.today().isoformat()

decisions = {
    "review_item_000020": {
        "proposed_decision": "accept_candidate",
        "reviewer": "external_audit_pilot",
        "review_date": today,
        "decision_reason": "Quote clearly reports 102,887 employees for 2024; accepted as human capital / workforce headcount evidence.",
        "corrected_value": "102887",
        "corrected_unit": "employees",
        "corrected_year": "2024",
        "corrected_indicator_family": "workforce",
        "corrected_indicator_key": "human_capital",
        "reviewer_notes": "Accepted for E2E pilot only; not a final ESG indicator.",
    },
    "review_item_000022": {
        "proposed_decision": "accept_candidate",
        "reviewer": "external_audit_pilot",
        "review_date": today,
        "decision_reason": "Quote clearly states Fresh water withdrawal: 92 Mm3; original family/unit were misclassified and corrected manually.",
        "corrected_value": "92",
        "corrected_unit": "Mm3",
        "corrected_year": "2024",
        "corrected_indicator_family": "water",
        "corrected_indicator_key": "water_consumption",
        "reviewer_notes": "Accepted for E2E pilot only; correction based directly on quote.",
    },
}

for rid in ["review_item_001095", "review_item_001096", "review_item_001097", "review_item_001098", "review_item_001099"]:
    decisions[rid] = {
        "proposed_decision": "reject_candidate",
        "reviewer": "external_audit_pilot",
        "review_date": today,
        "decision_reason": "Candidate is a footnote/reference artifact, not a usable ESG variable value.",
        "reviewer_notes": "Rejected during E2E pilot.",
    }

with template.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    fieldnames = reader.fieldnames

for row in rows:
    rid = row.get("review_item_id")
    if rid in decisions:
        row.update(decisions[rid])

with out.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("Wrote:", out)
print("Decisions written:", sum(1 for r in rows if r.get("proposed_decision")))
