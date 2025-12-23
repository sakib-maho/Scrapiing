"""
Gumtree Scraper using Scrapfly API
"""
import re
import time
from typing import Dict, List, Optional, Any
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
        self.is_australian = False  # Track if we're scraping Australian site

    def login(self) -> bool:
        """
        Optional login method (can be skipped).
        Keeping for compatibility; Gumtree phone reveal often does NOT require login.
        """
        print("ℹ login() called, but login is currently not required. Skipping.")
        self.logged_in = True
        return True

    # -------------------------
    # Search listings
    # -------------------------
    def search_listings(self, query: str, location: str = "", max_pages: int = 5, get_details: bool = True) -> List[Dict]:
        listings: List[Dict] = []
        base_search_url = f"{self.gumtree_config['base_url']}/search"

        for page in range(1, max_pages + 1):
            search_url = f"{base_search_url}?q={query.replace(' ', '+')}"
            if location:
                search_url += f"&location={location.replace(' ', '+')}"
            if page > 1:
                search_url += f"&page={page}"

            # IMPORTANT: keep AU flag consistent
            self.is_australian = "gumtree.com.au" in search_url

            print(f"Scraping page {page}: {search_url}")

            result = self.client.scrape_with_headers(
                search_url,
                headers=self.config["headers"]
            )

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
    def _parse_listings_page(self, html: str, url: str) -> List[Dict]:
        soup = BeautifulSoup(html, "lxml")
        listings: List[Dict] = []

        listing_selectors = [
            "article[class*='listing']",
            "div[class*='listing']",
            "li[class*='listing']",
            ".listing-item",
            ".ad-listing",
        ]

        listing_elements = []
        for selector in listing_selectors:
            elements = soup.select(selector)
            if elements:
                listing_elements = elements
                break

        if not listing_elements:
            # AU uses /s-ad/, UK often uses /p/
            if self.is_australian or "gumtree.com.au" in url:
                listing_links = soup.find_all("a", href=re.compile(r"/s-ad/"))
            else:
                listing_links = soup.find_all("a", href=re.compile(r"/p/"))

            for link in listing_links:
                listing_data = self._extract_listing_from_link(link)
                if listing_data:
                    listings.append(listing_data)
        else:
            for element in listing_elements:
                listing_data = self._extract_listing_data(element)
                if listing_data:
                    listings.append(listing_data)

        return listings

    def _extract_listing_from_link(self, link) -> Optional[Dict]:
        try:
            href = link.get("href", "")
            if not href or ("/p/" not in href and "/s-ad/" not in href):
                return None

            base_url = "https://www.gumtree.com.au" if "/s-ad/" in href else self.gumtree_config["base_url"]

            if href.startswith("/"):
                url = base_url + href
            elif href.startswith("http"):
                url = href
            else:
                url = base_url + "/" + href

            # FIXED: robust id extraction (handles ?query or end)
            job_id = None
            id_match = re.search(r"/(\d+)(?:\?|$)", url)
            if id_match:
                job_id = id_match.group(1)

            title = link.get_text(strip=True) or ""

            return {
                "job_id": job_id,
                "title": title,
                "url": url,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            print(f"Error extracting listing from link: {str(e)}")
            return None

    def _extract_listing_data(self, element) -> Optional[Dict]:
        try:
            title_elem = element.find(["h2", "h3", "a"], class_=re.compile(r"title|heading", re.I))
            title = title_elem.get_text(strip=True) if title_elem else ""

            link = element.find("a", href=True)
            url = ""
            if link:
                href = link.get("href", "")
                if href.startswith("/"):
                    url = self.gumtree_config["base_url"] + href
                else:
                    url = href

            if not title and not url:
                return None

            return {
                "title": title,
                "url": url,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            print(f"Error extracting listing data: {str(e)}")
            return None

    # -------------------------
    # Details page
    # -------------------------
    def get_listing_details(self, listing_url: str, debug_phone: bool = False) -> Dict:
        # IMPORTANT: keep AU flag consistent
        self.is_australian = "gumtree.com.au" in listing_url

        result = self.client.scrape_with_headers(
            listing_url,
            headers=self.config["headers"]
        )

        if not result.get("success"):
            return {
                "url": listing_url,
                "error": result.get("error"),
                "success": False,
            }

        soup = BeautifulSoup(result.get("html", ""), "lxml")
        details = self._parse_listing_details(soup, listing_url, scrape_result=result, debug_phone=debug_phone)
        details["success"] = True
        return details

    def _parse_listing_details(
        self,
        soup: BeautifulSoup,
        url: str,
        scrape_result: Optional[Dict[str, Any]] = None,
        debug_phone: bool = False
    ) -> Dict:
        details: Dict[str, Any] = {
            "url": url,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # FIXED: robust id extraction
        id_match = re.search(r"/(\d+)(?:\?|$)", url)
        if id_match:
            details["job_id"] = id_match.group(1)

        # Title
        title_elem = soup.find("h1") or soup.find(["h1", "h2"], class_=re.compile(r"title", re.I))
        if title_elem:
            details["title"] = title_elem.get_text(strip=True)
        else:
            meta_title = soup.find("meta", property="og:title") or soup.find("meta", {"name": "title"})
            if meta_title:
                details["title"] = meta_title.get("content", "")

        # Description (keep it, but don't parse phones from it)
        desc_elem = soup.find(["div", "section", "article"], class_=re.compile(r"description|content|body", re.I))
        details["description"] = desc_elem.get_text(strip=True) if desc_elem else None

        # Location (best-effort)
        location = None
        location_elem = soup.find(["span", "div", "p"], class_=re.compile(r"location|area|suburb|address", re.I))
        if location_elem:
            location = location_elem.get_text(strip=True)
        else:
            if "gumtree.com.au" in url and "/s-ad/" in url:
                parts = url.split("/s-ad/")[1].split("/")
                if len(parts) > 0:
                    location = parts[0].replace("-", " ").title()
        details["location"] = location

        # ✅ Phone via extractor WITH scrape_result
        job_id = details.get("job_id", "") or ""
        phone = self.phone_extractor.extract_phone(
            soup,
            url,
            job_id,
            scrape_result=scrape_result,
            debug=debug_phone
        )
        details["phone"] = phone

        if not phone:
            print("    ⚠ Phone number not found (no phone on ad OR reveal endpoint blocked)")
        else:
            print(f"    ✓ Phone number extracted: {phone[:10]}...")

        return details

    # -------------------------
    # Category scrape
    # -------------------------
    def scrape_category(self, category: str, location: str = "", max_pages: int = 5, get_details: bool = True) -> List[Dict]:
        if category.startswith("http"):
            category_url = category
        else:
            category_url = f"{self.gumtree_config['base_url']}/{category}"

        # IMPORTANT: keep AU flag consistent
        self.is_australian = "gumtree.com.au" in category_url

        listings: List[Dict] = []

        for page in range(1, max_pages + 1):
            url = category_url
            if page > 1:
                url += f"?page={page}"
            if location:
                separator = "&" if "?" in url else "?"
                url += f"{separator}location={location.replace(' ', '+')}"

            print(f"Scraping category page {page}: {url}")

            result = self.client.scrape_with_headers(
                url,
                headers=self.config["headers"]
            )

            if not result.get("success"):
                print(f"Failed to scrape page {page}: {result.get('error')}")
                continue

            page_listings = self._parse_listings_page(result.get("html", ""), url)

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

    def close(self):
        self.client.close()
