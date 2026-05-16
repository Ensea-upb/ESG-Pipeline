# ESGExtractionOrchestrator v1.0 - Architecture Overview

```text
ESGInformationExtraction output
  -> ESGCSVExtraction
  -> ESGVisualExtraction
  -> ESGTableExtraction
  -> consolidated candidates
  -> consolidated audit
```

The orchestrator coordinates existing modules and does not replace them.
