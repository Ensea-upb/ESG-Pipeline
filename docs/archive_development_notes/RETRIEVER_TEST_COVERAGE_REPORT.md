# Retriever Test Coverage Report

ProjectHygiene v0.7 adds non-network tests for the shared retriever pattern via
`AnnualReportRetriever`.

Covered behaviors:

- candidate scoring for a strong official annual-report PDF;
- rejection of a wrong-year press-release style candidate;
- URL deduplication;
- no-result behavior without network calls;
- non-PDF download response rejection with a mocked HTTP session;
- manifest and registry writing on a temporary fixture.

The other `*Retriever` modules share the same broad structure but are not all
expanded with full bespoke tests in this hygiene pass. They should receive
document-type-specific scoring tests later, especially for AGM, CDP, SBTi,
remuneration, vigilance-plan, and governance terminology.

No real network call is used by the added retriever tests.
