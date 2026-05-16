# Indicator Database Contract v0

`ESGIndicatorDatabase v1.0` builds a preparation-only database from human-accepted candidates.

Hard invariants:

- `indicator_database_status=preparation_only`
- `is_final_indicator=False`
- `score_produced=False`
- accepted candidates are not final validated ESG indicators
- raw and prepared values are stored separately
- evidence links and lineage are produced
