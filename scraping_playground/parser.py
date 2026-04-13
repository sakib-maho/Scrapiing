"""HTML parsing helpers for demo scraping workflows."""

from __future__ import annotations

from bs4 import BeautifulSoup


def extract_cards(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, str]] = []
    for card in soup.select(".listing-card"):
        title = card.select_one(".listing-title")
        price = card.select_one(".listing-price")
        location = card.select_one(".listing-location")
        items.append(
            {
                "title": title.get_text(strip=True) if title else "",
                "price": price.get_text(strip=True) if price else "",
                "location": location.get_text(strip=True) if location else "",
            }
        )
    return items
