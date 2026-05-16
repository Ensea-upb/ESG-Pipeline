#!/usr/bin/env python
"""Build text block diagnostics from existing PDF extraction outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ESGInformationExtraction.run_pdf_extraction import (  # noqa: E402
    build_text_block_statistics_from_files,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit text_blocks.jsonl and page_index.jsonl without reading source PDFs."
    )
    parser.add_argument("--text-blocks-path", required=True)
    parser.add_argument("--page-index-path", required=True)
    parser.add_argument("--output-path", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    text_blocks_path = Path(args.text_blocks_path).expanduser().resolve()
    page_index_path = Path(args.page_index_path).expanduser().resolve()
    output_path = Path(args.output_path).expanduser().resolve()

    if not text_blocks_path.exists():
        print(f"text_blocks file not found: {text_blocks_path}", file=sys.stderr)
        return 2
    if not page_index_path.exists():
        print(f"page_index file not found: {page_index_path}", file=sys.stderr)
        return 2

    statistics = build_text_block_statistics_from_files(
        text_blocks_path=text_blocks_path,
        page_index_path=page_index_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(statistics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Text block statistics written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
