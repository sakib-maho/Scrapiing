# Scraping Playground

Lightweight Python scraping toolkit for parsing listing-card style HTML and exporting structured outputs.

## Features

- Parses `.listing-card` blocks from HTML
- Extracts `title`, `price`, and `location`
- Exports both JSON and CSV
- Includes fixture-based tests and CLI coverage

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 cli.py --input tests/fixtures/sample_listings.html --json-out output/listings.json --csv-out output/listings.csv
```

## Tests

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

## License

MIT License. See `LICENSE`.
