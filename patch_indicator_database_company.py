import csv
from pathlib import Path

folder = Path(r"EXTERNAL_AUDIT_RUNS\totalenergies_2024_e2e_test\06_indicator_database_patched\totalenergies_2024_urd")
path = folder / "indicator_preparation_database.csv"

with path.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    fieldnames = reader.fieldnames

for row in rows:
    row["company"] = "TotalEnergies"
    row["fiscal_year"] = "2024"

with path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("patched rows:", len(rows))
