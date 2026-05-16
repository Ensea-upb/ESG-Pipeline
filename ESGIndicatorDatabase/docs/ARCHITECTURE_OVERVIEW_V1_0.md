# ESGIndicatorDatabase v1.0 - Architecture Overview

Pipeline:

1. Load `accepted_candidate_inputs.csv` from `ESGManualReview`.
2. Build preparation records.
3. Map preparation schema.
4. Link evidence.
5. Build lineage.
6. Audit and validate the outputs.

This module stops before final ESG indicator governance.
