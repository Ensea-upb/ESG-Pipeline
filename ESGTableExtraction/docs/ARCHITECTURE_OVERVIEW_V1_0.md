# ESGTableExtraction v1.0 - Architecture Overview

```text
ESGInformationExtraction table outputs
  -> loader
  -> reconstructor
  -> structure detector
  -> row classifier
  -> candidate extractor
  -> typed CSV exporter
  -> audit and contract validation
```

The module is separate from `ESGInformationExtraction`, `ESGCSVExtraction`, and `ESGVisualExtraction`.
