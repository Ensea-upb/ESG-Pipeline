# Requirements Notes

Python version used during this hygiene pass: Python 3.13.12 on Windows.

The project keeps lightweight requirement ranges rather than a strict lockfile.
Ranges are intentionally broad enough to avoid breaking the current local
environment while reducing accidental major-version drift.

## Runtime Ranges

- `pydantic>=2.0,<3.0`
- `pdfplumber>=0.10,<1.0`
- `pyyaml>=6.0,<7.0`
- `pandas>=2.0,<3.0`
- `requests>=2.31,<3.0`
- `beautifulsoup4>=4.12,<5.0`
- `lxml>=5.0,<7.0`
- `ddgs>=6.0,<10.0`
- `streamlit>=1.30,<2.0`

## Development Ranges

- `pytest>=8.0,<10.0`

`pytest<10` is used because this machine already runs pytest 9.0.3. If a CI
runner standardizes on pytest 8.x, this range can be narrowed later.

## Python 3.13 Note

Python 3.13 support can lag in PDF and data-processing libraries. If dependency
installation becomes unstable, pin a tested lockfile from a clean CI run rather
than widening ranges.
