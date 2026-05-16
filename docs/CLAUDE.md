# ESG Document Ingestion Project

## 1. Project Objective

This project builds a document ingestion system for ESG risk analysis.

The global goal is to automatically collect heterogeneous ESG-related corporate documents, store them in a structured local corpus, and prepare them for downstream deduplication, validation, parsing, information extraction, and ESG risk scoring.

The project is not a toy hackathon project. It is intended to become a professional prototype for a real business need.

The ingestion system must support several document categories:

1. Annual Reports / Universal Registration Documents
2. Sustainability Reports / ESG Reports / CSR Reports / RSE Reports
3. Climate Reports / TCFD Reports / Transition Plans
4. Governance Reports
5. Remuneration Reports
6. Board Reports
7. Vigilance Plans / Duty of Vigilance documents
8. Other ESG-related regulatory or corporate documents

The ingestion system does not validate the final content. Its role is to build a traceable corpus of candidate documents.

---

## 2. Existing Implemented Modules

Two retrievers are already implemented and should be used as reference examples.

### 2.1 AnnualReportRetriever

Location:

```text
AnnualReportRetriever/

Purpose:
Given a company and a target year, retrieve candidate annual reports / URD / DEU / integrated reports.

current version
AnnualReportRetriever v0.2

main capability
- Tavily search
- candidate scoring
- multi-candidate download
- HTML-to-PDF link resolution
- temporal filtering
- PDF download with robust HTTP strategies
- local storage in candidates/
- manifest JSON generation
- benchmark script

