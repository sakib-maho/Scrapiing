import json
from pathlib import Path
from subprocess import run
import unittest

from scraping_playground.parser import extract_cards


class ParserTests(unittest.TestCase):
    def test_extract_cards(self) -> None:
        html = Path("tests/fixtures/sample_listings.html").read_text(encoding="utf-8")
        rows = extract_cards(html)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["title"], "Lake View Apartment")

    def test_cli(self) -> None:
        json_out = Path("tests/fixtures/output.json")
        csv_out = Path("tests/fixtures/output.csv")
        for path in (json_out, csv_out):
            if path.exists():
                path.unlink()
        run(
            [
                "python3",
                "cli.py",
                "--input",
                "tests/fixtures/sample_listings.html",
                "--json-out",
                str(json_out),
                "--csv-out",
                str(csv_out),
            ],
            check=True,
        )
        payload = json.loads(json_out.read_text(encoding="utf-8"))
        self.assertEqual(len(payload), 2)
        for path in (json_out, csv_out):
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
