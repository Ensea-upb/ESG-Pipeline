# ESGManualReview v1.0 - Architecture Overview

Pipeline:

1. Loader reads `ESGIndicatorValidation` outputs.
2. Workspace builder creates CSV/JSONL/Markdown review files.
3. Decision template lets humans provide explicit choices.
4. Decision applier joins decisions to workspace rows.
5. Audit checks decision quality and traceability.
6. Contract validator enforces non-final, non-score outputs.

The next module may consume accepted candidates, but this module itself does not build a final indicator database.
