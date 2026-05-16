# Production Pipeline Plan

No ESG score or final validated indicator is produced.

- step_01 - Full extraction consolidation: `ESGExtractionOrchestrator`
- step_02 - Indicator pre-validation: `ESGIndicatorValidation`
- step_03 - Build manual review workspace: `ESGManualReview`
- step_04 - Apply human review decisions: `ESGManualReviewApply`
- step_05 - Build preparation-only indicator database: `ESGIndicatorDatabase`
