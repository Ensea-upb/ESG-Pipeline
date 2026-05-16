# ESG-Pipeline

**ESG data extraction and analysis pipeline** — Transforming PDF corpus into validated ESG indicators database

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📋 Overview

**ESG-Pipeline** is a comprehensive system for automatically extracting Environmental, Social, and Governance indicators from corporate documents (annual reports, sustainability reports, AGM documents, etc.). The pipeline performs:

1. **Document Retrieval** — Automatically downloads official PDFs from company websites and regulatory sources
2. **Information Extraction** — Extracts ESG-relevant information using document parsing and targeted extraction
3. **Quality Validation** — Validates extracted data against schema and scoring rules
4. **Indicator Preparation** — Standardizes values and maps to 31 official ESG variables
5. **Final Output** — Generates validated CSV datasets with full lineage tracking

**Output**: Two master CSV files
- `esg_values.csv` — Wide format (1 row per company/year, 31 ESG variable columns)
- `esg_lineage.csv` — Complete audit trail (source PDF, page, quote, reviewer decision, confidence score)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT RETRIEVAL LAYER                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │AnnualReportRetv. │  │AGMRetriever      │  │AssuranceReportR. │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │SustainabilityRpt.│  │ClimateReportRtrv.│  │GovernanceReportR│  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │SBTiRetriever     │  │CDPResponseRetv.  │  │+ 6 more retrievers  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
                    ESGCorpus (PDF storage)
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│              DOCUMENT POST-PROCESSING & EXTRACTION                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  DocumentPostProcessing → ESGTableExtraction, ESGVisualExtraction  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│           TARGETED ESG INFORMATION EXTRACTION LAYER                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ESGInformationExtraction + ESGVariableTargetedExtractionV2        │
│                                                                     │
│  Extracts: CO₂ emissions, water, waste, diversity, governance...   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│            VALIDATION & INDICATOR PREPARATION LAYER                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ESGIndicatorValidation → ESGVariableDatasetBuilder                │
│                                                                     │
│  • Schema validation (type, unit, range)                           │
│  • Confidence scoring                                              │
│  • Final indicator flagging                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│              ORCHESTRATION & QUALITY CONTROL                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ESGExtractionOrchestrator → ESGOrchestrator                       │
│  ESGProductionControlCenter → ESGManualReview (audit layer)        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│             MASTER DATASET CONSTRUCTION & OUTPUT                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  build_master_esg_dataset.py                                       │
│                                                                     │
│  Generates:                                                         │
│  • esg_values.csv (31 variables per company/year)                  │
│  • esg_lineage.csv (full audit trail with lineage)                 │
│  • build_summary.json (completion metrics)                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Modules & Retrievers

### Document Retrievers (15+ modules)
Each retriever automatically searches for and downloads specific document types:

| Module | Document Type | Scoring Strategy |
|--------|---------------|------------------|
| **AnnualReportRetriever** | Annual/financial reports | Company name + official domain + keywords |
| **AGMRetriever** | Annual General Meeting docs | Strong AGM keywords (proxy, resolutions) |
| **AssuranceReportRetriever** | ISAE 3000/3410 assurance statements | Assurance keywords (ISAE, AA1000) |
| **SustainabilityReportRetriever** | Standalone ESG/sustainability reports | ESG keywords + official domain |
| **ClimateReportRetriever** | Climate strategy & TCFD disclosures | Climate + TCFD keywords |
| **SBTiRetriever** | Science-Based Targets initiative | SBTi membership validation |
| **CDPResponseRetriever** | CDP Climate & Water responses | CDP disclosure platform |
| **GovernanceReportRetriever** | Board composition, remuneration | Governance + board keywords |
| **EarningsCallRetriever** | Earnings call transcripts | Quarterly/earnings calls |
| **InvestorPresentationRetriever** | Investor day presentations | Investor + presentation keywords |
| **HalfYearReportRetriever** | H1 interim reports | H1/interim keywords |
| **RemunerationReportRetriever** | Pay/remuneration policies | Remuneration + executive pay |
| **CorporatePolicyRetriever** | Corporate policies (environmental, HR) | Policy type + official domain |
| **VigilancePlanRetriever** | French vigilance plans (Loi Sapin 2) | Vigilance plan keywords |

### Core Extraction Modules

| Module | Purpose |
|--------|---------|
| **DocumentPostProcessing** | PDF parsing, quality audit, indexed storage |
| **ESGTableExtraction** | Tabular data extraction from documents |
| **ESGVisualExtraction** | Chart/visual data extraction |
| **ESGInformationExtraction** | NLP-based text extraction of ESG claims |
| **ESGVariableTargetedExtractionV2** | Targeted extraction for specific ESG variables |

### Validation & Output Modules

| Module | Purpose |
|--------|---------|
| **ESGIndicatorValidation** | Schema validation, confidence scoring |
| **ESGVariableDatasetBuilder** | Standardization to 31 official variables |
| **ESGCSVExtraction** | CSV parsing and harmonization |
| **ESGManualReview** | Human reviewer interface for validation |
| **ESGProductionControlCenter** | Production QA and monitoring |

---

## 📊 The 31 ESG Variables

The pipeline standardizes to 31 official variables:

**Environmental (10):**
- `co2_emissions`, `carbon_intensity`, `energy_consumption`, `water_consumption`
- `waste`, `biodiversity`, `fossil_exposure`, `pollution`, `renewable_energy`, `supply_chain_env`

**Social (9):**
- `diversity`, `work_accidents`, `human_capital`, `supply_chain`, `human_rights`
- `board_independence`, `shareholder_rights`, `social_controversies`, `labor_practices`

**Governance (12):**
- `ceo_chairman_separation`, `remuneration`, `transparency`, `esg_scandals`
- `fraud`, `corruption`, `lawsuits`, `market_cap`, `volatility`, `leverage`, `roa`, `roe`, `liquidity`, `stock_returns`

See: `ESGVariableDatasetBuilder/contracts/esg_variables_dataset_contract_v0.json`

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- pip or conda

### Installation

```bash
# Clone the repository
git clone https://github.com/Ensea-upb/ESG-Pipeline.git
cd ESG-Pipeline

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements_all.txt
pip install -e .  # Install as editable package (optional)
```

**Dependencies** (see `requirements_all.txt`):
- `beautifulsoup4` — HTML parsing
- `ddgs` — DuckDuckGo search integration
- `lxml` — XML/PDF processing
- `pandas` — Data manipulation
- `pdfplumber` — PDF text extraction
- `pydantic` — Schema validation
- `pyyaml` — Config files
- `requests` — HTTP requests
- `streamlit` — UI dashboards

### Basic Usage

#### 1. Download Documents (Single Company)

```bash
cd AnnualReportRetriever
python scripts/run_download_all.py \
  --company-name "Apple Inc." \
  --fiscal-year 2024 \
  --official-domain apple.com
```

Outputs to: `data/dossier_ingestion_0/annual_reports/apple_inc/candidates/`

#### 2. Run Benchmark (Evaluate Retriever)

```bash
cd AssuranceReportRetriever
python scripts/run_benchmark.py --fiscal-year 2024
```

#### 3. Extract ESG Data

```bash
# Navigate to extraction module
cd ESGInformationExtraction
python -m extraction.main --company-slug apple_inc --fiscal-year 2024
```

#### 4. Build Master Dataset (Final Output)

```bash
# From project root
python build_master_esg_dataset.py --output-dir ./MASTER_ESG_OUTPUT

# Inspect results
cat MASTER_ESG_OUTPUT/build_summary.json
head -5 MASTER_ESG_OUTPUT/esg_values.csv
```

**Output files:**
- `MASTER_ESG_OUTPUT/esg_values.csv` — All 31 ESG variables (wide format)
- `MASTER_ESG_OUTPUT/esg_lineage.csv` — Full audit trail with sources
- `MASTER_ESG_OUTPUT/build_summary.json` — Build metrics & completion %

---

## 📁 Project Structure

```
ESG-Pipeline/
├── README.md                          # This file
├── requirements_all.txt               # Python dependencies
├── pytest.ini                         # Test configuration
│
├── [Document Retrievers] ──────────── Automated PDF downloads
│   ├── AnnualReportRetriever/
│   ├── AGMRetriever/
│   ├── AssuranceReportRetriever/
│   ├── SustainabilityReportRetriever/
│   ├── ClimateReportRetriever/
│   ├── ... (12+ more)
│
├── [Core Extraction] ──────────────── Document processing
│   ├── DocumentPostProcessing/
│   ├── ESGTableExtraction/
│   ├── ESGVisualExtraction/
│   ├── ESGInformationExtraction/
│   └── ESGVariableTargetedExtractionV2/
│
├── [Validation & Output] ──────────── Standardization & QA
│   ├── ESGIndicatorValidation/
│   ├── ESGVariableDatasetBuilder/
│   ├── ESGCSVExtraction/
│   ├── ESGManualReview/
│   └── ESGProductionControlCenter/
│
├── [Orchestration] ────────────────── Pipeline control
│   ├── ESGOrchestrator/
│   ├── ESGExtractionOrchestrator/
│   └── ESGCorpusTaxonomy/
│
├── [Build & Master Output] ────────── Final dataset construction
│   ├── MASTER_ESG_OUTPUT/            # Generated: esg_values.csv, esg_lineage.csv
│   ├── EXTERNAL_AUDIT_RUNS/          # Individual run outputs
│   ├── build_master_esg_dataset.py   # Master build script
│   └── ESGIndicatorDatabase/
│
├── [Supporting] ───────────────────── Tools & utilities
│   ├── scripts/                      # Command-line scripts
│   ├── tools/                        # Utilities & helpers
│   ├── docs/                         # Extended documentation
│   └── tests/                        # Test suite
│
└── [Monitoring] ───────────────────── Audit outputs
    ├── audit_e2e_v4/, audit_e2e_v5/
    ├── project_validation_summary.json
    └── METADATA_PROPAGATION_RISK_REGISTER.csv
```

---

## 🔬 Testing

Run the test suite:

```bash
# All tests
pytest

# Specific module
pytest tests/test_extraction.py -v

# With coverage
pytest --cov=. tests/
```

End-to-end tests: See `audit_e2e_v5/` and `E2E_TEST_METADATA_FIX/`

---

## 📊 Output Format Reference

### esg_values.csv
Wide format dataset (1 row per company/fiscal year):

```csv
company_name,company_slug,fiscal_year,co2_emissions,carbon_intensity,...,stock_returns
Apple Inc.,apple_inc,2024,1200000,45.2,...,18.5
Tesla Inc.,tesla_inc,2024,450000,12.1,...,42.3
```

### esg_lineage.csv
Full audit trail (1 row per extracted value):

```csv
company_slug,company_name,fiscal_year,variable,value,unit,reference_year,value_raw,unit_raw,source_page,source_quote,reviewer,decision_reason,reviewer_notes,source_pdf,canonical_id,run_id,source_engine,schema_confidence
apple_inc,Apple Inc.,2024,co2_emissions,1200000,Mt CO2e,2024,1200000,metric tons,42,"Apple achieved carbon neutrality...",john_doe,is_final_indicator=True,High confidence from annual report,/path/to/AAPL_10-K_2024.pdf,doc_123,run_2024_04,ESGInformationExtraction,0.95
```

---

## 🔧 Configuration

Configuration files by module:

- `{Module}/config/` — Per-module configs (YAML or JSON)
- `{Module}/contracts/` — Data schema validation contracts (Pydantic)
- Environment variables — Document retrieval credentials

Example: Setting up Company list

```bash
export COMPANIES_LIST="data/companies.csv"
export FISCAL_YEARS="2022,2023,2024"
```

---

## 📈 Monitoring & Quality Audit

The pipeline includes built-in quality monitoring:

1. **Metadata Propagation Register** — `METADATA_PROPAGATION_RISK_REGISTER.csv`
   - Tracks potential data quality issues across modules
   - Risk levels: HIGH, MEDIUM, LOW

2. **Validation Summary** — `project_validation_summary.json`
   - Extraction completeness per company & variable
   - Schema violation reports
   - Confidence score distributions

3. **Manual Review** — `ESGManualReview/`
   - Interface for human validation of high-risk extractions
   - Decision audit trail stored in lineage

Run quality audit:

```bash
python ESGProductionControlCenter/run_quality_audit.py
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

**Contribution Areas:**
- New document retriever types
- Improved extraction models
- Validation schema enhancements
- Documentation & examples

See `CONTRIBUTING.md` for detailed guidelines.

---

## 📄 License

MIT License — See `LICENSE` file

---

## 👥 Authors & Contact

- **Ensea-upb** — ESG Pipeline Maintainers
- Questions? Open an issue on GitHub

---

## 🔗 References & Standards

- **GRI Standards** — Global Reporting Initiative (sustainability disclosure)
- **SASB** — Sustainability Accounting Standards Board
- **TCFD** — Task Force on Climate-related Financial Disclosures
- **CSRD** — Corporate Sustainability Reporting Directive (EU)
- **ISAE 3000/3410** — Assurance standards for ESG/sustainability data
- **Science Based Targets** (SBTi) — Climate commitment framework
- **CDP** — Environmental disclosure platform

---

## 📚 Documentation

Extended documentation available in `docs/`:
- `docs/ARCHITECTURE.md` — Detailed system architecture
- `docs/EXTRACTION_LOGIC.md` — Information extraction methodology
- `docs/VALIDATION_RULES.md` — Schema & scoring rules
- `docs/LINEAGE_TRACKING.md` — Data provenance & audit trail
- `docs/MODULE_REFERENCE.md` — Per-module API reference

---

## ⚠️ Known Issues & Limitations

See `METADATA_PROPAGATION_RISK_REGISTER.csv` for current known issues.

Key limitations:
- PDF extraction quality varies by document format & quality
- OCR required for scanned documents (not yet implemented)
- Multi-language support limited to EN/FR
- Real-time data updates require full pipeline re-run

---

## 🗺️ Roadmap

- [ ] Implement OCR layer for scanned PDFs
- [ ] Add real-time incremental updates
- [ ] Expand language support (ES, DE, IT)
- [ ] ML-based confidence scoring improvements
- [ ] GraphQL API for data access
- [ ] Web dashboard for data exploration
- [ ] Integration with commercial ESG data providers

---

**Last Updated:** 2026-05-16  
**Version:** 1.0.0
