"""CLI entrypoint for scraping playground."""

from __future__ import annotations

import argparse
from pathlib import Path

from scraping_playground.parser import extract_cards
from scraping_playground.storage import save_csv, save_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scraping-playground",
        description="Extract listing cards from local HTML files.",
    )
    parser.add_argument("--input", type=Path, required=True, help="HTML input path")
    parser.add_argument("--json-out", type=Path, required=True, help="Output JSON path")
    parser.add_argument("--csv-out", type=Path, required=True, help="Output CSV path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    html = args.input.read_text(encoding="utf-8")
    rows = extract_cards(html)
    save_json(args.json_out, rows)
    save_csv(args.csv_out, rows)
    print(f"Extracted {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
