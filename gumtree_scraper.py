"""
Gumtree Scraper using Scrapfly API
"""

import re
import time
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from scrapfly_client import ScrapflyClient
from phone_extractor import PhoneExtractor
from config import get_config


class GumtreeScraper:
    """Main scraper class for Gumtree"""

    def __init__(self):
        self.config = get_config()
        self.client = ScrapflyClient()
        self.phone_extractor = PhoneExtractor(self.client)
        self.gumtree_config = self.config["gumtree"]

        self.session_cookies = {}
        self.logged_in = False
        self.is_australian = False

    def login(self) -> bool:
        """
        Optional login method (can be skipped).
        Keeping for compatibility; this project currently does not require login.
        """
        print("ℹ login() called, but login is currently not required. Skipping.")
        self.logged_in = True
        return True

    # -------------------------
    # Helpers
    # -------------------------
    @staticmethod
    def _robust_ad_id_from_url(url: str) -> Optional[str]:
        m = re.search(r"/(\d+)(?:\?|$)", url or "")
        return m.group(1) if m else None

    @staticmethod
    def _page_base_url(page_url: str) -> str:
        if "gumtree.com.au" in (page_url or "").lower():
            return "https://www.gumtree.com.au"
        return "https://www.gumtree.com"

    def _make_absolute(self, href: str, page_url: str) -> str:
        if not href:
            return ""
        if href.startswith("http"):
            return href
        base = self._page_base_url(page_url)
        if href.startswith("/"):
            return base + href
        return base + "/" + href

    # -------------------------
    # Search listings
    # -------------------------
    def search_listings(
        self,
        query: str,
        location: str = "",
        max_pages: int = 5,
        get_details: bool = True,
    ) -> List[Dict[str, Any]]:
        listings: List[Dict[str, Any]] = []
        base_search_url = f"{self.gumtree_config['base_url']}/search"

        for page in range(1, max_pages + 1):
            search_url = f"{base_search_url}?q={query.replace(' ', '+')}"
            if location:
                search_url += f"&location={location.replace(' ', '+')}"
            if page > 1:
                search_url += f"&page={page}"

            self.is_australian = "gumtree.com.au" in search_url.lower()

            print(f"Scraping page {page}: {search_url}")
            result = self.client.scrape_with_headers(search_url, headers=self.config["headers"])

            if not result.get("success"):
                print(f"Failed to scrape page {page}: {result.get('error')}")
                continue

            page_listings = self._parse_listings_page(result.get("html", ""), search_url)

            if get_details:
                print(f"  Fetching details for {len(page_listings)} listings...")
                for i, listing in enumerate(page_listings, 1):
                    if listing.get("url"):
                        print(f"    [{i}/{len(page_listings)}] Fetching: {listing.get('url', '')[:60]}...")
                        details = self.get_listing_details(listing["url"])
                        if details.get("success"):
                            listing.update(details)
                        time.sleep(self.config["scraping"]["delay"] * 0.5)

            listings.extend(page_listings)

            if not page_listings:
                break

            time.sleep(self.config["scraping"]["delay"])

        return listings

    # -------------------------
    # Parse list page
    # -------------------------
    def _parse_listings_page(self, html: str, url: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        listings: List[Dict[str, Any]] = []

        # AU uses /s-ad/, UK often uses /p/
        link_pat = r"/s-ad/" if ("gumtree.com.au" in url.lower()) else r"/p/"

        listing_links = soup.find_all("a", href=re.compile(link_pat))
        for link in listing_links:
            href = link.get("href", "")
            abs_url = self._make_absolute(href, url)
            if not abs_url:
                continue

            job_id = self._robust_ad_id_from_url(abs_url)
            title = link.get_text(strip=True) or ""

            listings.append(
                {
                    "job_id": job_id,
                    "title": title,
                    "url": abs_url,
                    "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

        # De-dup by URL
        uniq: Dict[str, Dict[str, Any]] = {}
        for item in listings:
            if item.get("url"):
                uniq[item["url"]] = item
        return list(uniq.values())

    # -------------------------
    # Details page
    # -------------------------
    def get_listing_details(self, listing_url: str, debug_phone: bool = False) -> Dict[str, Any]:
        """
        debug_phone=True:
          - tells Scrapfly to include debug payload (often richer network structures)
          - tells PhoneExtractor to print debug logs
        """
        self.is_australian = "gumtree.com.au" in (listing_url or "").lower()

        result = self.client.scrape_with_headers(
            listing_url,
            headers=self.config["headers"],
            debug=bool(debug_phone),  # IMPORTANT: enable Scrapfly debug when investigating phone
        )

        if not result.get("success"):
            return {
                "url": listing_url,
                "error": result.get("error"),
                "success": False,
            }

        soup = BeautifulSoup(result.get("html", ""), "lxml")
        details = self._parse_listing_details(
            soup,
            listing_url,
            scrape_result=result,
            debug_phone=debug_phone,
        )
        details["success"] = True
        return details

    def _parse_listing_details(
        self,
        soup: BeautifulSoup,
        url: str,
        scrape_result: Optional[Dict[str, Any]] = None,
        debug_phone: bool = False,
    ) -> Dict[str, Any]:
        details: Dict[str, Any] = {
            "url": url,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Robust ad id extraction
        details["job_id"] = self._robust_ad_id_from_url(url)

        # Title
        title_elem = soup.find("h1") or soup.find(["h1", "h2"], attrs={"class": re.compile(r"title", re.I)})
        if title_elem:
            details["title"] = title_elem.get_text(strip=True)
        else:
            meta_title = soup.find("meta", property="og:title") or soup.find("meta", {"name": "title"})
            if meta_title:
                details["title"] = meta_title.get("content", "")

        # Description (keep it, but PhoneExtractor will not trust it for phones unless valid AU format)
        desc_elem = soup.find(["div", "section", "article"], attrs={"class": re.compile(r"description|content|body", re.I)})
        details["description"] = desc_elem.get_text(" ", strip=True) if desc_elem else None

        # Location (best effort)
        location = None
        location_elem = soup.find(["span", "div", "p"], attrs={"class": re.compile(r"location|area|suburb|address", re.I)})
        if location_elem:
            location = location_elem.get_text(" ", strip=True)
        else:
            if "gumtree.com.au" in url.lower() and "/s-ad/" in url:
                parts = url.split("/s-ad/")[1].split("/")
                if parts and parts[0]:
                    location = parts[0].replace("-", " ").title()
        details["location"] = location

        # ✅ Phone: pass scrape_result + debug flag exactly as PhoneExtractor expects
        job_id = details.get("job_id") or ""
        phone = self.phone_extractor.extract_phone(
            soup,
            url,
            job_id,
            scrape_result=scrape_result,
            debug=bool(debug_phone),
        )
        details["phone"] = phone

        if not phone:
            print("    ⚠ Phone number not found (guest-accessible sources had no phone OR endpoint blocked)")
        else:
            print(f"    ✓ Phone number extracted: {phone}")

        return details

    def close(self):
        self.client.close()
