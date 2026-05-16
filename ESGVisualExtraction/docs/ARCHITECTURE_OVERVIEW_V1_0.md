# ESGVisualExtraction v1.0 - Architecture Overview

`ESGVisualExtraction` complements `ESGCSVExtraction`. It focuses only on images, figures, charts, scanned tables, diagrams, maps, and page-level visuals already detected by `ESGInformationExtraction`.

```text
ESGInformationExtraction figure outputs
  -> visual loader
  -> cropper
  -> optional OCR
  -> visual classifier
  -> visual candidate extractor
  -> audit and contract validation
```

The module remains separate from `ESGInformationExtraction` and `ESGCSVExtraction`. It does not parse PDFs as a primary extraction engine, does not validate ESG values, and does not score companies.
