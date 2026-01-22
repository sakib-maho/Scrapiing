"""
Gumtree Scraper using Scrapfly API
"""
import os
import re
import json
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
import pytz
import requests
from bs4 import BeautifulSoup
from scrapfly_client import ScrapflyClient
from config import get_config

# Australian timezone
AUSTRALIA_TZ = pytz.timezone('Australia/Sydney')

# Debug mode: Set to True to save HTML pages for inspection
DEBUG_SAVE_HTML = False
DEBUG_HTML_DIR = "debug_html"


class GumtreeScraper:
    """Main scraper class for Gumtree"""
    
    def __init__(self):
        self.config = get_config()
        self.client = ScrapflyClient()
        self.gumtree_config = self.config["gumtree"]
        self.is_australian = True  # Always Australian site
        # Detail fetch concurrency (defaults to 1 for stability)
        self.detail_concurrency = int(os.environ.get("SCRAPE_CONCURRENCY", "1"))

    def _canonicalize_url_for_dedupe(self, url: str) -> str:
        """
        Canonicalize a Gumtree listing URL for dedupe purposes.
        Strips query/fragment and normalizes scheme/host casing.
        """
        if not url:
            return ""
        try:
            p = urlparse(url)
            # If someone passed a relative URL, just return as-is (caller should normalize first).
            if not p.scheme or not p.netloc:
                return url
            # Drop query + fragment; keep path
            clean = p._replace(query="", fragment="")
            # Lowercase scheme/netloc for stable keys
            clean = clean._replace(scheme=clean.scheme.lower(), netloc=clean.netloc.lower())
            return urlunparse(clean).rstrip("/")
        except Exception:
            return url.rstrip("/")

    def _listing_dedupe_key(self, item: Dict) -> str:
        """
        Build a stable dedupe key.
        Prefer numeric job_id; fall back to extracting it from URL; last resort is canonicalized URL.
        """
        if not isinstance(item, dict):
            return ""
        job_id = item.get("job_id")
        if job_id:
            return f"id:{job_id}"
        url = item.get("url") or ""
        m = re.search(r"/(\d+)$", url)
        if m:
            return f"id:{m.group(1)}"
        cu = self._canonicalize_url_for_dedupe(url)
        return f"url:{cu}" if cu else ""

    def _dedupe_listings(self, listings: List[Dict]) -> List[Dict]:
        """
        Deduplicate listings by numeric ad id (preferred) or canonicalized URL.
        Preserves first-seen order.
        """
        seen: set[str] = set()
        out: List[Dict] = []
        for item in listings or []:
            if not isinstance(item, dict):
                continue
            key = self._listing_dedupe_key(item)
            if not key:
                continue
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out
    
    def _normalize_url(self, href: str, base_url: str = None) -> str:
        """
        Normalize relative/absolute URLs to full URLs
        
        Args:
            href: URL (relative or absolute)
            base_url: Base URL to use if href is relative
        
        Returns:
            Normalized absolute URL
        """
        if not href:
            return ""
        
        if href.startswith("http://") or href.startswith("https://"):
            return href
        
        base = base_url or self.gumtree_config["base_url"]
        if href.startswith("/"):
            return base + href
        
        return f"{base}/{href}"
    
    def _convert_to_exact_date(self, date_str: str) -> Optional[str]:
        """
        Convert relative dates to exact dates (YYYY-MM-DD format)
        
        Args:
            date_str: Date string (e.g., "2 days ago", "Today", "Yesterday", "20/12/2025")
        
        Returns:
            Exact date in YYYY-MM-DD format, or None if conversion fails
        """
        if not date_str:
            return None
        
        date_str = date_str.strip()
        today = datetime.now()
        
        # Handle "Today"
        if re.match(r'^Today$', date_str, re.I):
            return today.strftime("%Y-%m-%d")
        
        # Handle "Yesterday"
        if re.match(r'^Yesterday$', date_str, re.I):
            yesterday = today - timedelta(days=1)
            return yesterday.strftime("%Y-%m-%d")
        
        # Handle "X hours ago"
        hours_match = re.search(r'(\d+)\s+(hour|hours)\s+ago', date_str, re.I)
        if hours_match:
            hours = int(hours_match.group(1))
            exact_date = today - timedelta(hours=hours)
            return exact_date.strftime("%Y-%m-%d")
        
        # Handle "X days ago"
        days_match = re.search(r'(\d+)\s+(day|days)\s+ago', date_str, re.I)
        if days_match:
            days = int(days_match.group(1))
            exact_date = today - timedelta(days=days)
            return exact_date.strftime("%Y-%m-%d")
        
        # Handle "X weeks ago"
        weeks_match = re.search(r'(\d+)\s+(week|weeks)\s+ago', date_str, re.I)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            exact_date = today - timedelta(weeks=weeks)
            return exact_date.strftime("%Y-%m-%d")
        
        # Handle "X months ago" (approximate - using 30 days per month)
        months_match = re.search(r'(\d+)\s+(month|months)\s+ago', date_str, re.I)
        if months_match:
            months = int(months_match.group(1))
            exact_date = today - timedelta(days=months * 30)
            return exact_date.strftime("%Y-%m-%d")
        
        # Handle ISO format dates (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        iso_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
        if iso_match:
            return iso_match.group(1)
        
        # Handle DD/MM/YYYY or DD-MM-YYYY format
        date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', date_str)
        if date_match:
            day, month, year = date_match.groups()
            if len(year) == 2:
                year = f"20{year}"  # Convert YY to YYYY
            try:
                exact_date = datetime(int(year), int(month), int(day))
                return exact_date.strftime("%Y-%m-%d")
            except ValueError:
                pass
        
        # Handle "DD Mon YYYY" format (e.g., "20 Jan 2025")
        full_date_match = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})', date_str, re.I)
        if full_date_match:
            day, month_name, year = full_date_match.groups()
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            month = month_map.get(month_name.lower()[:3])
            if month:
                try:
                    exact_date = datetime(int(year), month, int(day))
                    return exact_date.strftime("%Y-%m-%d")
                except ValueError:
                    pass
        
        # If no pattern matches, return None
        return None
    
    def _extract_phone_from_text(self, text: str, job_id: str = None) -> Optional[str]:
        """
        Extract phone number from text/description
        
        Args:
            text: Text to search for phone number
            job_id: Optional job_id to exclude from phone extraction
        
        Returns:
            Phone number string if found, None otherwise
        """
        if not text:
            return None
        
        # Remove job_id from text if provided (to prevent it from being matched as phone)
        if job_id:
            # Remove job_id from end of text (common pattern: "...1339381402")
            text = re.sub(r'\b' + re.escape(job_id) + r'\b', '', text)
        
        # Handle multiple phone numbers separated by / (e.g., "0429094776/02.66544222")
        # We'll extract all and return the first valid one
        
        # Australian phone number patterns (more comprehensive)
        # IMPORTANT: Job IDs are typically 10 digits starting with 1, so we exclude those
        phone_patterns = [
            # International mobile: +61 4XX XXX XXX (check first to avoid confusion)
            r'\+61[\s\.\-]?4\d{2}[\s\.\-]?\d{3}[\s\.\-]?\d{3}',  # +61 420 338 760, +61 493 526 714
            # International landline: +61 X XXXX XXXX
            r'\+61[\s\.\-]?[2-9]\d{1}[\s\.\-]?\d{4}[\s\.\-]?\d{4}',  # +61 2 XXXX XXXX
            # Mobile numbers: 04XX XXX XXX (with various separators - spaces, dots, dashes, or none)
            r'04\d{2}[\s\.\-/]?\d{3}[\s\.\-/]?\d{3}',  # 0417 496 989, 0428520505, 04XX.XXX.XXX, 04XX/XXX/XXX
            # Mobile numbers: 10 digits starting with 04 (no separators)
            r'(?<![\d/])04\d{8}(?![\d/])',  # 0429094776, 0428520505, 0493907008 (not part of longer number)
            # Landline: 0X XXXX XXXX (with various separators - spaces, dots, dashes, or none)
            r'0[2-9]\d{1}[\s\.\-/]?\d{4}[\s\.\-/]?\d{4}',  # 02 6654 4222, 02.66544222, 03-XXXX-XXXX, 02/XXXX/XXXX
            # Landline with parentheses: (0X) XXXX XXXX
            r'\(0[2-9]\d{1}\)[\s\.\-/]?\d{4}[\s\.\-/]?\d{4}',  # (02) XXXX XXXX
            # 10 digits starting with 0 (catch-all for Australian format, but exclude if starts with 1)
            # This should be last as it's the most general
            r'(?<![\d/])0[2-9]\d{8}(?![\d/])',  # Any 10-digit number starting with 0[2-9] (not part of longer number)
        ]
        
        found_phones = []
        
        for pattern in phone_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                phone = match.group(0).strip()
                # Clean the phone number for comparison (remove all non-digits except +)
                phone_clean = re.sub(r'[^\d\+]', '', phone)
                # If it starts with +61, convert to 0 format for comparison
                if phone_clean.startswith('+61'):
                    phone_clean = '0' + phone_clean[3:]
                
                # Must be 10 digits after cleaning (Australian phone numbers are 10 digits)
                if len(phone_clean) != 10:
                    continue
                
                # Exclude if it matches the job_id (exact match)
                if job_id and phone_clean == job_id:
                    continue
                
                # Exclude if it's approximately the same as job_id (within 1-2 digits difference)
                if job_id and len(phone_clean) == len(job_id):
                    # Check if they differ by only 1-2 digits (likely same number)
                    diff_count = sum(c1 != c2 for c1, c2 in zip(phone_clean, job_id))
                    if diff_count <= 2:
                        continue
                
                # Exclude if it's 10 digits starting with 1 (job_id pattern - Gumtree job IDs are 10 digits starting with 1)
                if phone_clean.startswith('1'):
                    continue
                
                # Must start with 0 (Australian phone numbers start with 0)
                if not phone_clean.startswith('0'):
                    continue
                
                # Valid Australian phone number formats:
                # - Mobile: 04XX XXXXXX (04 followed by 8 more digits)
                # - Landline: 0[2-9]X XXXXXX (0 followed by area code 2-9, then 8 more digits)
                if not (phone_clean.startswith('04') or (phone_clean[0] == '0' and phone_clean[1] in '23456789')):
                    continue
                
                # Clean up the phone number for output (normalize separators)
                phone = re.sub(r'[\s\.\-]+', ' ', phone)  # Replace dots/dashes with single space
                phone = phone.strip()
                
                # Avoid duplicates
                if phone not in found_phones:
                    found_phones.append(phone)
        
        # Return the first valid phone number found
        if found_phones:
            return found_phones[0]
        
        return None
    
    def _check_phone_number_exists(self, soup: BeautifulSoup) -> bool:
        """
        Check if phone number exists or is available on the listing page
        by looking for "Show number" text or similar indicators
        
        Args:
            soup: BeautifulSoup object of the listing page
        
        Returns:
            True if "Show number" text is found, False otherwise
        """
        # Get all text content from the page
        page_text = soup.get_text()
        
        # Check for "Show number" text (case insensitive)
        # Look for variations: "Show number", "Show Number", "show number", etc.
        show_number_patterns = [
            r'show\s+number',
            r'reveal\s+phone',
            r'view\s+phone',
            r'display\s+phone',
            r'see\s+phone',
        ]
        
        for pattern in show_number_patterns:
            if re.search(pattern, page_text, re.I):
                return True
        
        # Also check in button/link text specifically
        # Find all buttons and links that might contain "Show number"
        buttons = soup.find_all("button")
        links = soup.find_all("a")
        
        for element in buttons + links:
            element_text = element.get_text(strip=True)
            if element_text:
                for pattern in show_number_patterns:
                    if re.search(pattern, element_text, re.I):
                        return True
        
        # Check for "Show number" in element attributes (aria-label, title, etc.)
        all_elements = soup.find_all(True)  # Find all elements
        for element in all_elements:
            # Check common attributes that might contain "Show number"
            attrs_to_check = ['aria-label', 'title', 'data-label', 'data-text', 'alt']
            for attr in attrs_to_check:
                attr_value = element.get(attr, '')
                if attr_value:
                    for pattern in show_number_patterns:
                        if re.search(pattern, str(attr_value), re.I):
                            return True
        
        return False
    
    def search_listings(self, query: str, location: str = "", max_pages: int = 5, get_details: bool = True) -> List[Dict]:
        """
        Search for listings on Gumtree
        
        Args:
            query: Search query
            location: Location filter
            max_pages: Maximum number of pages to scrape
            get_details: Whether to fetch detailed information for each listing
        
        Returns:
            List of listing dictionaries
        """
        listings = []
        base_search_url = f"{self.gumtree_config['base_url']}/search"
        
        for page in range(1, max_pages + 1):
            # Construct search URL with proper encoding
            params = {"q": query}
            if location:
                params["location"] = location
            if page > 1:
                params["page"] = str(page)
            
            query_string = urlencode(params, doseq=True)
            search_url = f"{base_search_url}?{query_string}"
            
            print(f"Scraping page {page}: {search_url}")
            
            result = self.client.scrape_with_headers(
                search_url,
                headers=self.config["headers"]
            )
            
            if not result["success"]:
                error_msg = result.get('error', 'Unknown error')
                print(f"Failed to scrape page {page}: {error_msg}")
                continue
            
            page_listings = self._parse_listings_page(result["html"], search_url)
            
            # Get detailed information for each listing if requested
            if get_details:
                print(f"  Fetching details for {len(page_listings)} listings...")
                for i, listing in enumerate(page_listings, 1):
                    if listing.get("url"):
                        # Skip visiting page if phone already found in description
                        if listing.get("phoneNumberExists") and listing.get("phone"):
                            print(f"    [{i}/{len(page_listings)}] Phone found in description, skipping page visit: {listing.get('url', '')[:60]}...")
                        else:
                            print(f"    [{i}/{len(page_listings)}] Fetching: {listing.get('url', '')[:60]}...")
                            details = self.get_listing_details(listing["url"])
                            if details.get("success"):
                                # Merge details with listing data (phone from description takes priority)
                                if listing.get("phone"):
                                    details["phone"] = listing.get("phone")
                                    details["phoneNumberExists"] = True
                                    # Add phone reveal URL if we have job_id
                                    job_id = listing.get("job_id") or details.get("job_id")
                                    if job_id:
                                        details["phoneRevealUrl"] = f"https://gt-api.gumtree.com.au/web/vip/reveal-phone-number?adId={job_id}"
                                # Preserve creationDate from search results if detail page doesn't have it
                                if listing.get("creationDate") and not details.get("creationDate"):
                                    details["creationDate"] = listing.get("creationDate")
                                listing.update(details)
                            time.sleep(self.config["scraping"]["delay"] * 0.5)  # Shorter delay for details
            
            listings.extend(page_listings)
            
            # If no listings found, stop pagination
            if not page_listings:
                break
            
            time.sleep(self.config["scraping"]["delay"])
        
        return listings
    
    def _parse_listings_page(self, html: str, url: str) -> List[Dict]:
        """Parse listings from a search results page"""
        soup = BeautifulSoup(html, "lxml")
        listings = []
        
        # Prefer the main results collection (more reliable than generic selectors and reduces noise).
        # Gumtree AU jobs pages commonly have:
        #   <section class="search-results-page__user-ad-collection"> ... <a href="/s-ad/.../123"> ... </a>
        results_root = soup.select_one("section.search-results-page__user-ad-collection")
        if results_root:
            listing_links = results_root.find_all("a", href=re.compile(r"/s-ad/"))
            for link in listing_links:
                href = link.get("href", "")
                if "p-post-ad" in href or "post-ad" in href.lower() or "login" in href.lower():
                    continue
                listing_data = self._extract_listing_from_link(link, soup)
                if listing_data:
                    listings.append(listing_data)
            return listings

        # Find listing containers (Gumtree structure may vary)
        # Common selectors for listings
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
        
        # If no specific selector works, try to find links to listings
        if not listing_elements:
            # Look for links - Australian uses /s-ad/
            listing_links = soup.find_all("a", href=re.compile(r"/s-ad/"))
            
            for link in listing_links:
                href = link.get("href", "")
                # Skip post-ad and login pages
                if "p-post-ad" in href or "post-ad" in href.lower() or "login" in href.lower():
                    continue
                listing_data = self._extract_listing_from_link(link, soup)
                if listing_data:
                    listings.append(listing_data)
        else:
            for element in listing_elements:
                listing_data = self._extract_listing_data(element)
                if listing_data:
                    listings.append(listing_data)
        
        return listings
    
    def _extract_listing_from_link(self, link, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract listing data from a link element"""
        try:
            href = link.get("href", "")
            # Check for Australian (/s-ad/) pattern
            if not href or "/s-ad/" not in href:
                return None
            
            # Exclude "Post Ad" and other non-listing pages
            if "p-post-ad" in href or "post-ad" in href.lower() or "login" in href.lower():
                return None
            
            # Use Australian base URL from config
            base_url = self.gumtree_config["base_url"]
            
            # Normalize URL
            url = self._normalize_url(href, base_url)
            
            # Validate URL - must have a numeric ID at the end (job_id)
            id_match = re.search(r'/(\d+)$', url)
            if not id_match:
                # Not a valid listing URL (no ID at the end)
                return None
            
            job_id = id_match.group(1)
            
            # Try to find title
            title = link.get_text(strip=True)
            if not title:
                title_elem = link.find(["h2", "h3", "span", "div"], class_=re.compile(r"title|heading", re.I))
                if title_elem:
                    title = title_elem.get_text(strip=True)
            
            # Try to find location from nearby elements
            location = None
            location_elem = link.find_next(["span", "div"], class_=re.compile(r"location|area|suburb", re.I))
            if location_elem:
                location = location_elem.get_text(strip=True)
            
            # Try to find category from URL
            category_name = None
            if "/s-ad/" in href:
                # Australian format: /s-ad/location/category/title/id
                parts = href.split("/")
                if len(parts) >= 4:
                    category_name = parts[3].replace("-", " ").title()
            
            # Extract creation date from search results page
            creation_date = None
            
            # Find the listing container (parent or grandparent of the link)
            listing_container = link.find_parent(["article", "div", "li", "section"])
            if not listing_container:
                listing_container = link.parent
            
            # First, try to find the specific Gumtree class: user-ad-row-new-design__age
            # Search within the listing container first
            if listing_container:
                age_elem = listing_container.find("p", class_=re.compile(r"user-ad-row-new-design__age|age", re.I))
                if age_elem:
                    creation_date = age_elem.get_text(strip=True)
            
            # If not found, search in the entire soup but near the link
            if not creation_date:
                # Find all age elements and check which one is closest to our link
                all_age_elems = soup.find_all("p", class_=re.compile(r"user-ad-row-new-design__age|age", re.I))
                for age_elem in all_age_elems:
                    # Check if this age element is in the same listing container as our link
                    age_container = age_elem.find_parent(["article", "div", "li", "section"])
                    if age_container == listing_container or (listing_container and age_elem in listing_container.find_all()):
                        creation_date = age_elem.get_text(strip=True)
                        break
            
            # If not found, check parent element and siblings for date
            if not creation_date and listing_container:
                container_text = listing_container.get_text()
                # Look for date patterns like "4 hours ago", "2 days ago", "20/12/2025", "Today", "Yesterday"
                date_patterns = [
                    r'(\d+\s+(hour|hours)\s+ago)',
                    r'(\d+\s+(day|days)\s+ago)',
                    r'(\d+\s+(week|weeks)\s+ago)',
                    r'(\d+\s+(month|months)\s+ago)',
                    r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                    r'(Today|Yesterday)',
                ]
                for pattern in date_patterns:
                    match = re.search(pattern, container_text, re.I)
                    if match:
                        creation_date = match.group(0).strip()
                        break
            
            # If not found in container, check nearby elements relative to the link
            if not creation_date:
                # Check next sibling elements
                next_elem = link.find_next_sibling()
                if next_elem:
                    next_text = next_elem.get_text()
                    date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', next_text, re.I)
                    if date_match:
                        creation_date = date_match.group(0).strip()
            
                # Also check for the age class in nearby elements (within same container)
                if not creation_date and listing_container:
                    nearby_age = listing_container.find("p", class_=re.compile(r"user-ad-row-new-design__age|age", re.I))
                    if nearby_age:
                        creation_date = nearby_age.get_text(strip=True)
                
                # Check all siblings of the link's parent
                if not creation_date:
                    parent = link.parent
                    if parent:
                        for sibling in parent.find_next_siblings():
                            sibling_text = sibling.get_text(strip=True)
                            if len(sibling_text) < 100:  # Dates are usually short
                                date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', sibling_text, re.I)
                                if date_match:
                                    creation_date = date_match.group(0).strip()
                                    break
            
            # Convert relative date to exact date
            exact_date = None
            if creation_date:
                exact_date = self._convert_to_exact_date(creation_date)
            
            # Try to find description snippet from nearby elements
            description = None
            desc_elem = link.find_next(["p", "div", "span"], class_=re.compile(r"description|snippet|summary", re.I))
            if desc_elem:
                description = desc_elem.get_text(strip=True)
            
            # Check if phone number is in description
            phone = None
            phone_exists = False
            if description:
                phone = self._extract_phone_from_text(description, job_id)
                if phone:
                    phone_exists = True
            
            result = {
                "job_id": job_id,
                "title": title,
                "url": url,
                "location": location,
                "categoryName": category_name,
                "creationDate": exact_date if exact_date else creation_date,
                "description": description,
                "phone": phone,
                "phoneNumberExists": phone_exists,
                "scraped_at": datetime.now(AUSTRALIA_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            }
            
            # Add phone reveal URL if phone number exists
            if phone_exists and job_id:
                result["phoneRevealUrl"] = f"https://gt-api.gumtree.com.au/web/vip/reveal-phone-number?adId={job_id}"
            
            return result
        except (AttributeError, KeyError, ValueError) as e:
            print(f"Error extracting listing from link: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error extracting listing from link: {str(e)}")
            return None
    
    def _extract_listing_data(self, element) -> Optional[Dict]:
        """Extract data from a listing element"""
        try:
            # Extract title
            title_elem = element.find(["h2", "h3", "a"], class_=re.compile(r"title|heading", re.I))
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Extract URL
            link = element.find("a", href=True)
            url = ""
            if link:
                href = link.get("href", "")
                url = self._normalize_url(href)
            
            # Extract location
            location_elem = element.find(["span", "div"], class_=re.compile(r"location", re.I))
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Extract description snippet
            desc_elem = element.find(["p", "div"], class_=re.compile(r"description|snippet", re.I))
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Check if phone number is in description
            phone = None
            phone_exists = False
            if description:
                # Extract job_id from URL if available
                job_id_from_url = None
                if url:
                    id_match = re.search(r'/(\d+)$', url)
                    if id_match:
                        job_id_from_url = id_match.group(1)
                phone = self._extract_phone_from_text(description, job_id_from_url)
                if phone:
                    phone_exists = True
            
            if not title and not url:
                return None
            
            result = {
                "title": title,
                "url": url,
                "location": location,
                "description": description,
                "phone": phone,
                "phoneNumberExists": phone_exists,
                "scraped_at": datetime.now(AUSTRALIA_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            }
            
            # Add phone reveal URL if phone number exists and we have job_id
            if phone_exists and job_id_from_url:
                result["phoneRevealUrl"] = f"https://gt-api.gumtree.com.au/web/vip/reveal-phone-number?adId={job_id_from_url}"
            
            return result
        except (AttributeError, KeyError, ValueError) as e:
            print(f"Error extracting listing data: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error extracting listing data: {str(e)}")
            return None
    
    def get_listing_details(self, listing_url: str) -> Dict:
        """
        Get detailed information for a specific listing
        
        Args:
            listing_url: URL of the listing
        
        Returns:
            Dictionary with detailed listing information
        """
        # Validate URL
        if not listing_url or not (listing_url.startswith("http://") or listing_url.startswith("https://")):
            return {
                "url": listing_url,
                "error": "Invalid URL format",
                "success": False,
            }
        
        try:
            result = self.client.scrape_with_headers(
                listing_url,
                headers=self.config["headers"]
            )
        except requests.exceptions.RequestException as e:
            return {
                "url": listing_url,
                "error": f"Network error: {str(e)}",
                "success": False,
            }
        except Exception as e:
            return {
                "url": listing_url,
                "error": f"Unexpected error: {str(e)}",
                "success": False,
            }
        
        if not result["success"]:
            return {
                "url": listing_url,
                "error": result.get("error"),
                "success": False,
            }
        
        # Save HTML for debugging if enabled
        if DEBUG_SAVE_HTML:
            self._save_html_for_debug(result["html"], listing_url)
        
        try:
            soup = BeautifulSoup(result["html"], "lxml")
            details = self._parse_listing_details(soup, listing_url)
            details["success"] = True
            return details
        except Exception as e:
            # Catch any parsing errors (regex, attribute errors, etc.)
            error_msg = str(e)
            import traceback
            print(f"    ⚠️  Error parsing listing details: {error_msg[:200]}")
            return {
                "url": listing_url,
                "error": f"Parsing error: {error_msg}",
                "success": False,
            }
    
    def _parse_listing_details(self, soup: BeautifulSoup, url: str) -> Dict:
        """Parse detailed listing information"""
        details = {
            "url": url,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        # Extract job_id from URL
        id_match = re.search(r'/(\d+)$', url)
        if id_match:
            details["job_id"] = id_match.group(1)
        
        # Extract title
        title_elem = soup.find("h1") or soup.find(["h1", "h2"], class_=re.compile(r"title", re.I))
        if title_elem:
            details["title"] = title_elem.get_text(strip=True)
        else:
            # Try to find title in meta tags
            meta_title = soup.find("meta", property="og:title") or soup.find("meta", {"name": "title"})
            if meta_title:
                details["title"] = meta_title.get("content", "")
        
        # Extract description - try multiple locations (get FULL description, not snippet)
        description = None
        
        # First, try to find description in common Gumtree locations
        # Look for elements with description-related classes or IDs
        desc_selectors = [
            soup.find("div", id=re.compile(r"description|content|body|ad-content|listing-content", re.I)),
            soup.find("section", id=re.compile(r"description|content|body|ad-content|listing-content", re.I)),
            soup.find("article", id=re.compile(r"description|content|body|ad-content|listing-content", re.I)),
            soup.find(["div", "section", "article"], class_=re.compile(r"description|content|body|ad-content|listing-content|ad-description", re.I)),
            soup.find("div", attrs={"data-testid": re.compile(r"description|content", re.I)}),
        ]
        
        for desc_elem in desc_selectors:
            if desc_elem:
                # Get full text, preserving line breaks
                description = desc_elem.get_text(separator="\n", strip=True)
                # Remove excessive whitespace but keep structure
                description = re.sub(r'\n{3,}', '\n\n', description)
                if description and len(description) > 50:  # Make sure we got substantial content
                    break
        
        # If not found, try to find main content area
        if not description or len(description) < 50:
            main_content = soup.find("main") or soup.find("article") or soup.find("div", role="main")
            if main_content:
                # Remove navigation, header, footer, and other non-content elements
                for elem in main_content.find_all(["nav", "header", "footer", "aside", "script", "style"]):
                    elem.decompose()
                # Also remove common Gumtree UI elements
                for elem in main_content.find_all(class_=re.compile(r"header|footer|nav|sidebar|ad-header|ad-footer|breadcrumb", re.I)):
                    elem.decompose()
                description = main_content.get_text(separator="\n", strip=True)
                description = re.sub(r'\n{3,}', '\n\n', description)
        
        # If still not found, try meta description (but this is usually a snippet)
        if not description or len(description) < 50:
            meta_desc = soup.find("meta", property="og:description") or soup.find("meta", {"name": "description"})
            if meta_desc:
                description = meta_desc.get("content", "")
        
        # Clean up description - remove job_id if it appears at the end
        job_id_for_cleanup = details.get("job_id")
        if description and job_id_for_cleanup:
            # Remove job_id from end of description (common pattern)
            description = re.sub(r'\s*' + re.escape(job_id_for_cleanup) + r'\s*$', '', description)
            description = description.strip()
        
        # Extract only text between "Description" and stop markers (case insensitive)
        if description:
            text = description  # your full string
            # Try multiple patterns for different variations
            # Use more flexible patterns that handle newlines and whitespace
            patterns = [
                r'Description\s*\n?\s*(.*?)\s*\n?\s*Show\s+full\s+description',  # "Show full description"
                r'Description\s*\n?\s*(.*?)\s*\n?\s*Show\s+all\s+description',     # "Show all description"
                r'Description\s*\n?\s*(.*?)\s*\n?\s*ADVERTISEMENT',              # "ADVERTISEMENT" (common stop)
                r'Description\s*\n?\s*(.*?)\s*\n?\s*Apply\s+with\s+confidence',   # "Apply with confidence"
                r'Description\s*\n?\s*(.*?)\s*\n?\s*Get\s+in\s+touch',          # "Get in touch"
            ]
            
            result = None
            for pattern in patterns:
                match = re.search(pattern, text, re.S | re.I)  # re.S for dotall (matches newlines), re.I for case insensitive
                if match:
                    result = match.group(1).strip()
                    # Additional cleanup: remove any remaining leading/trailing newlines
                    result = re.sub(r'^\n+|\n+$', '', result)
                    break
            
            if result:
                description = result
        
        details["description"] = description
        
        # Check if phone number is in description
        phone = None
        phone_exists = False
        if description:
            # Use job_id from details if available
            job_id_for_phone = details.get("job_id")
            phone = self._extract_phone_from_text(description, job_id_for_phone)
            if phone:
                phone_exists = True
        
        # If phone not found in description, search the entire page text
        # (phone numbers might be in other sections like contact info, sidebar, etc.)
        if not phone:
            # Get all text from the page (excluding scripts and styles)
            page_text = soup.get_text(separator=" ", strip=True)
            # Remove excessive whitespace
            page_text = re.sub(r'\s+', ' ', page_text)
            if page_text and len(page_text) > len(description or ""):
                job_id_for_phone = details.get("job_id")
                phone = self._extract_phone_from_text(page_text, job_id_for_phone)
                if phone:
                    phone_exists = True
        
        # Always check for "Show number" text on the page (since we're already visiting it)
        # This ensures we catch cases where phone exists but wasn't in description
        show_number_exists = self._check_phone_number_exists(soup)
        
        # phoneNumberExists is true if either:
        # 1. We found a phone number in description or page text, OR
        # 2. "Show number" text exists on the page
        phone_exists = phone_exists or show_number_exists
        
        details["phone"] = phone
        details["phoneNumberExists"] = phone_exists
        
        # Add phone reveal URL if phone number exists
        if phone_exists and details.get("job_id"):
            details["phoneRevealUrl"] = f"https://gt-api.gumtree.com.au/web/vip/reveal-phone-number?adId={details['job_id']}"
        
        # Extract location - try multiple methods
        location = None
        location_elem = soup.find(["span", "div", "p"], class_=re.compile(r"location|area|suburb|address", re.I))
        if location_elem:
            location = location_elem.get_text(strip=True)
        else:
            # Try to extract from URL for Australian site
            if "gumtree.com.au" in url and "/s-ad/" in url:
                parts = url.split("/s-ad/")[1].split("/")
                if len(parts) > 0:
                    location = parts[0].replace("-", " ").title()
            # Check meta tags
            meta_loc = soup.find("meta", {"name": re.compile(r"location|area", re.I)})
            if meta_loc:
                location = meta_loc.get("content", "")
        
        details["location"] = location
        
        # Extract creationDate/posted date
        creation_date = None
        text = soup.get_text()
        
        # FIRST: Try to get dates from Gumtree API (most reliable)
        # API: https://gt-api.gumtree.com.au/web/vip/snapshot-tabs/{listing_id}
        job_id = details.get("job_id")
        if job_id:
            try:
                api_url = f"https://gt-api.gumtree.com.au/web/vip/snapshot-tabs/{job_id}"
                api_response = requests.get(
                    api_url,
                    headers=self.config["headers"],
                    timeout=10
                )
                if api_response.status_code == 200:
                    api_data = api_response.json()
                    # Look for "Date Listed" and "Last Edited" in listingInfo array
                    listing_info = api_data.get("listingInfo", [])
                    for info_item in listing_info:
                        name = info_item.get("name", "")
                        value = info_item.get("value", "")
                        if name == "Date Listed" and value:
                            # Convert to exact date format (e.g., "20 Dec 2025" -> "2025-12-20")
                            creation_date = value
                        elif name == "Last Edited" and value:
                            # Store lastEdited separately (will be processed later)
                            # Convert to exact date format
                            details["_lastEdited_from_api"] = value
            except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError, ValueError) as e:
                # API call failed, continue with HTML parsing
                pass
        
        # If API didn't provide creationDate, try to extract from __NEXT_DATA__ JSON (Next.js stores data here)
        if not creation_date:
            next_data_script = soup.find("script", id="__NEXT_DATA__")
            if next_data_script and next_data_script.string:
                try:
                    next_data = json.loads(next_data_script.string)
                    # Navigate through the JSON structure to find date
                    # Common paths: pageProps.ad.postedDate, pageProps.ad.createdAt, etc.
                    ad_data = next_data.get("props", {}).get("pageProps", {}).get("ad", {})
                    if ad_data:
                        # Try various date field names
                        for date_field in ["postedDate", "createdAt", "datePosted", "dateCreated", "postedAt", "createdDate", "listingDate"]:
                            if date_field in ad_data:
                                date_value = ad_data[date_field]
                                if date_value:
                                    # Convert Unix timestamp to date string if needed
                                    if isinstance(date_value, (int, float)) and date_value > 1000000000:
                                        creation_date = datetime.fromtimestamp(date_value).strftime("%Y-%m-%d")
                                    elif isinstance(date_value, str):
                                        creation_date = date_value
                                    break
                except (json.JSONDecodeError, KeyError, ValueError, OSError):
                    pass
        
        # Try to extract from dataLayer JavaScript (Google Tag Manager)
        if not creation_date:
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and ("dataLayer" in script.string or "lpdt" in script.string or "cdt" in script.string):
                    script_text = script.string
                    # Look for Unix timestamps: lpdt:1766817165 or cdt:1766817165
                    timestamp_match = re.search(r'(?:lpdt|cdt|postedDate|createdAt|datePosted)[":\s]*(\d{10,13})', script_text)
                    if timestamp_match:
                        timestamp = int(timestamp_match.group(1))
                        # Convert Unix timestamp to date
                        if timestamp > 1000000000:  # Valid Unix timestamp
                            try:
                                creation_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                            except (ValueError, OSError):
                                pass
                        if creation_date:
                            break
                if creation_date:
                    break
        
        # First, look for "About this listing" section or "Listing Info" tab content
        # This is where "Date Listed" appears in the popup
        about_section = soup.find(string=re.compile(r"About\s+this\s+listing|Listing\s+Info", re.I))
        if about_section:
            # Find the parent container
            container = about_section.find_parent(["div", "section", "article", "dialog"])
            if container:
                # Look for "Date Listed" in this container
                date_listed_elem = container.find(string=re.compile(r"Date\s+Listed", re.I))
                if date_listed_elem:
                    # Find the value - could be in next sibling, next element, or same parent
                    parent = date_listed_elem.find_parent()
                    if parent:
                        # Check next sibling
                        next_sib = parent.find_next_sibling()
                        if next_sib:
                            next_text = next_sib.get_text(strip=True)
                            date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', next_text, re.I)
                            if date_match:
                                creation_date = date_match.group(0).strip()
                        # Check parent's text for "Date Listed: [date]"
                        if not creation_date:
                            parent_text = parent.get_text()
                            date_match = re.search(r'Date\s+Listed[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', parent_text, re.I)
                            if date_match:
                                creation_date = date_match.group(1).strip()
                        # Check all siblings
                        if not creation_date:
                            for sibling in parent.find_next_siblings():
                                sibling_text = sibling.get_text(strip=True)
                                if sibling_text and len(sibling_text) < 100:
                                    date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', sibling_text, re.I)
                                    if date_match:
                                        creation_date = date_match.group(0).strip()
                                        break
                        # Check next element (not just sibling)
                        if not creation_date:
                            next_elem = parent.find_next()
                            if next_elem and next_elem != parent:
                                next_text = next_elem.get_text(strip=True)
                                date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', next_text, re.I)
                                if date_match:
                                    creation_date = date_match.group(0).strip()
                # Also search entire container for date patterns
                if not creation_date:
                    container_text = container.get_text()
                    date_match = re.search(r'Date\s+Listed[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', container_text, re.I)
                    if date_match:
                        creation_date = date_match.group(1).strip()
        
        # Also search for "Date Listed" anywhere in the page (even in hidden popup content)
        if not creation_date:
            # Find all instances of "Date Listed" text
            all_date_listed = soup.find_all(string=re.compile(r"Date\s+Listed", re.I))
            for date_listed_text in all_date_listed:
                parent = date_listed_text.find_parent()
                if parent:
                    # First, check the immediate parent's text
                    parent_text = parent.get_text()
                    date_match = re.search(r'Date\s+Listed[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', parent_text, re.I)
                    if date_match:
                        creation_date = date_match.group(1).strip()
                        break
                    
                    # Check next sibling of parent
                    next_sib = parent.find_next_sibling()
                    if next_sib:
                        next_text = next_sib.get_text(strip=True)
                        if len(next_text) < 100:  # Dates are usually short
                            date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', next_text, re.I)
                            if date_match:
                                creation_date = date_match.group(0).strip()
                                break
                    
                    # Get all text from parent container and its siblings
                    parent_container = parent.find_parent(["div", "section", "article", "dialog", "li", "tr", "dl"])
                    if parent_container:
                        container_text = parent_container.get_text()
                        # Look for "Date Listed" followed by date in the same container
                        date_match = re.search(r'Date\s+Listed[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', container_text, re.I)
                        if date_match:
                            creation_date = date_match.group(1).strip()
                            break
                    
                    # Also check the row/container structure (common in listing info)
                    row = parent.find_parent(["div", "li", "tr", "dl", "dt"])
                    if row:
                        row_text = row.get_text()
                        # Extract date that appears after "Date Listed" in the same row
                        date_match = re.search(r'Date\s+Listed[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', row_text, re.I)
                        if date_match:
                            creation_date = date_match.group(1).strip()
                            break
                    
                    # Check all children of parent for date-like text
                    for child in parent.find_all(["span", "div", "p", "dd", "td"]):
                        child_text = child.get_text(strip=True)
                        if child_text and len(child_text) < 100:
                            date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', child_text, re.I)
                            if date_match:
                                creation_date = date_match.group(0).strip()
                                break
                    if creation_date:
                        break
                if creation_date:
                    break
        
        # Look for date elements with datetime attributes (most reliable)
        if not creation_date:
            date_elem = soup.find(["time"], datetime=True)
            if date_elem:
                creation_date = date_elem.get("datetime", "")
                # If datetime is ISO format, extract just the date part
            if creation_date and "T" in creation_date:
                creation_date = creation_date.split("T")[0]
        
        # Look for date elements by class (more specific selectors)
        if not creation_date:
            # First, try to find "Date Listed" label and get the date from nearby elements
            date_listed_label = soup.find(string=re.compile(r"Date\s+Listed", re.I))
            if date_listed_label:
                # Find the parent element
                parent = date_listed_label.parent
                if parent:
                    # Look for date in next sibling or parent's next sibling
                    next_sibling = parent.find_next_sibling()
                    if next_sibling:
                        next_text = next_sibling.get_text(strip=True)
                        date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', next_text, re.I)
                        if date_match:
                            creation_date = date_match.group(0).strip()
                    # Also check parent's parent for date
                    if not creation_date and parent.parent:
                        parent_text = parent.parent.get_text()
                        date_match = re.search(r'Date\s+Listed[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', parent_text, re.I)
                        if date_match:
                            creation_date = date_match.group(1).strip()
                    # Check all siblings after "Date Listed"
                    if not creation_date:
                        for sibling in parent.find_next_siblings():
                            sibling_text = sibling.get_text(strip=True)
                            if sibling_text and len(sibling_text) < 100:  # Dates are usually short
                                date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', sibling_text, re.I)
                                if date_match:
                                    creation_date = date_match.group(0).strip()
                                    break
            
            # Try multiple class patterns and data attributes
            if not creation_date:
                date_selectors = [
                    # Gumtree-specific class: user-ad-row-new-design__age (most common)
                    soup.find("p", class_=re.compile(r"user-ad-row-new-design__age|age", re.I)),
                    # Gumtree CSS-in-JS classes (css-*)
                    soup.find(["p", "span", "div"], class_=re.compile(r"css-.*", re.I)),
                    soup.find(["span", "div", "p"], class_=re.compile(r"date|time|posted|created|published|ago", re.I)),
                    soup.find(["span", "div"], attrs={"data-date": True}),
                    soup.find(["span", "div"], attrs={"data-time": True}),
                    soup.find(["span", "div"], attrs={"data-posted": True}),
                    # Gumtree-specific selectors
                    soup.find(["span", "div", "p"], class_=re.compile(r"ad-posted|listing-date|post-date|ad-date|date-posted", re.I)),
                    soup.find(["span", "div"], attrs={"data-ad-posted": True}),
                    soup.find(["span", "div"], attrs={"data-listing-date": True}),
                ]
                for date_elem in date_selectors:
                    if date_elem:
                        elem_text = date_elem.get_text(strip=True)
                        # Skip if it's just "Date Listed" label
                        if elem_text and elem_text.lower() not in ["date listed", "date", "listed"]:
                            creation_date = elem_text
                        # Check for datetime attribute
                        datetime_attr = date_elem.get("datetime") or date_elem.get("data-date") or date_elem.get("data-time") or date_elem.get("data-posted") or date_elem.get("data-ad-posted") or date_elem.get("data-listing-date")
                        if datetime_attr:
                            creation_date = datetime_attr
                            if "T" in creation_date:
                                creation_date = creation_date.split("T")[0]
                            # Verify it looks like a date
                            if creation_date and re.search(r'\d|Today|Yesterday|ago', creation_date, re.I):
                                break
                            else:
                                creation_date = None
        
        # Try to find date in dialog/modal structures (common in Gumtree)
        if not creation_date:
            dialog = soup.find(["dialog", "div"], class_=re.compile(r"dialog|modal|popup", re.I))
            if dialog:
                dialog_text = dialog.get_text()
                # Look for "Date Listed" followed by date
                date_match = re.search(r'Date\s+Listed[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', dialog_text, re.I)
                if date_match:
                    creation_date = date_match.group(1).strip()
                # Also search for any date pattern in dialog
                if not creation_date:
                    date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', dialog_text, re.I)
                    if date_match:
                        creation_date = date_match.group(0).strip()
        
        # Try to find date in specific Gumtree sections (header, sidebar, etc.)
        if not creation_date:
            # Look in common Gumtree page sections
            header = soup.find(["header", "div"], class_=re.compile(r"header|ad-header|listing-header", re.I))
            if header:
                header_text = header.get_text()
                date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', header_text, re.I)
                if date_match:
                    creation_date = date_match.group(0).strip()
            
            # Look in sidebar or info sections
            if not creation_date:
                sidebar = soup.find(["aside", "div"], class_=re.compile(r"sidebar|info|details|meta", re.I))
                if sidebar:
                    sidebar_text = sidebar.get_text()
                    date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', sidebar_text, re.I)
                    if date_match:
                        creation_date = date_match.group(0).strip()
        
        # Try to find in text patterns like "X hours ago", "X days ago", dates
        if not creation_date:
            # More comprehensive date patterns
            date_patterns = [
                r'(\d+\s+(hour|hours)\s+ago)',
                r'(\d+\s+(day|days)\s+ago)',
                r'(\d+\s+(week|weeks)\s+ago)',
                r'(\d+\s+(month|months)\s+ago)',
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # Date format like 20/12/2025
                r'(Today|Yesterday)',
                r'(\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',  # Full date
                r'(Posted|Listed|Created|Published).*?(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago)',  # "Posted 2 days ago"
                r'(Posted|Listed|Created|Published).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # "Posted 20/12/2025"
                r'(Ad\s+posted|Listed|Created).*?(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago)',  # "Ad posted 2 days ago"
                r'(Ad\s+posted|Listed|Created).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # "Ad posted 20/12/2025"
                r'(\d{1,2}\s+(hour|hours|day|days|week|weeks|month|months)\s+ago)',  # Just "2 days ago" without prefix
            ]
            for pattern in date_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    # Extract the date part (usually the last group)
                    groups = match.groups()
                    if groups and groups[-1]:
                        creation_date = groups[-1].strip()
                    else:
                        creation_date = match.group(0).strip()
                    # If it's just a word like "hour" or "day", get the full match
                    if len(creation_date) < 5 and groups:
                        creation_date = match.group(0).strip()
                    if creation_date:
                        break
        
        # If still not found, check meta tags
        if not creation_date:
            meta_date = soup.find("meta", {"property": "article:published_time"}) or \
                       soup.find("meta", {"property": "article:published"}) or \
                       soup.find("meta", {"name": re.compile(r"date|published|created", re.I)})
            if meta_date:
                creation_date = meta_date.get("content", "")
                if "T" in creation_date:
                    creation_date = creation_date.split("T")[0]
        
        # Try to find date in structured data (JSON-LD)
        if not creation_date:
            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                try:
                    json_data = json.loads(script.string)
                    if isinstance(json_data, dict):
                        # Check for datePublished or dateCreated
                        date_published = json_data.get("datePublished") or json_data.get("dateCreated")
                        if date_published:
                            creation_date = date_published
                            if "T" in creation_date:
                                creation_date = creation_date.split("T")[0]
                            break
                except:
                    pass
        
        # Try to find date in JavaScript variables or data attributes
        if not creation_date:
            # Look for script tags that might contain date data
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string:
                    script_text = script.string
                    # Look for common date variable patterns
                    date_var_patterns = [
                        r'datePublished["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                        r'dateCreated["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                        r'postedDate["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                        r'createdAt["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    ]
                    for pattern in date_var_patterns:
                        match = re.search(pattern, script_text, re.I)
                        if match:
                            creation_date = match.group(1).strip()
                            if "T" in creation_date:
                                creation_date = creation_date.split("T")[0]
                            break
                    if creation_date:
                        break
        
        # Last resort: search all elements for date-like text
        if not creation_date:
            # Find all elements and check their text for date patterns
            all_elements = soup.find_all(["span", "div", "p", "time", "small", "em", "strong"])
            for elem in all_elements:
                elem_text = elem.get_text(strip=True)
                if elem_text and len(elem_text) < 50:  # Only check short text (dates are usually short)
                    # Check if it looks like a date
                    date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', elem_text, re.I)
                    if date_match:
                        creation_date = date_match.group(0).strip()
                        break
                if creation_date:
                    break
        
        # Convert relative date to exact date
        if creation_date:
            exact_date = self._convert_to_exact_date(creation_date)
            details["creationDate"] = exact_date if exact_date else creation_date
        else:
            details["creationDate"] = None
        
        # Extract lastEdited date
        last_edited = None
        
        # FIRST: Check if we got lastEdited from the API
        if "_lastEdited_from_api" in details:
            last_edited = details.pop("_lastEdited_from_api")
        
        # If API didn't provide lastEdited, try to extract from __NEXT_DATA__ JSON (same as creationDate)
        if not last_edited:
            next_data_script = soup.find("script", id="__NEXT_DATA__")
            if next_data_script and next_data_script.string:
                try:
                    next_data = json.loads(next_data_script.string)
                    ad_data = next_data.get("props", {}).get("pageProps", {}).get("ad", {})
                    if ad_data:
                        # Try various last edited field names
                        for date_field in ["lastEdited", "lastEditedDate", "updatedAt", "modifiedAt", "dateModified", "dateUpdated"]:
                            if date_field in ad_data:
                                date_value = ad_data[date_field]
                                if date_value:
                                    # Convert Unix timestamp to date string if needed
                                    if isinstance(date_value, (int, float)) and date_value > 1000000000:
                                        last_edited = datetime.fromtimestamp(date_value).strftime("%Y-%m-%d")
                                    elif isinstance(date_value, str):
                                        last_edited = date_value
                                        if "T" in last_edited:
                                            last_edited = last_edited.split("T")[0]
                                    break
                except (json.JSONDecodeError, KeyError, ValueError, OSError):
                    pass
        
        # Try to extract from dataLayer JavaScript (same as creationDate)
        if not last_edited:
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string:
                    script_text = script.string
                    # Look for "lastEdited" or "updatedAt" in dataLayer
                    if "dataLayer" in script_text and ("lastEdited" in script_text or "updatedAt" in script_text):
                        # Look for Unix timestamps in dataLayer
                        timestamp_match = re.search(r'(?:lastEdited|updatedAt|modifiedAt|dateModified|lastEditedDate)[":\s]*(\d{10,13})', script_text)
                        if timestamp_match:
                            timestamp = int(timestamp_match.group(1))
                            if timestamp > 1000000000:  # Valid Unix timestamp
                                try:
                                    last_edited = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                                except (ValueError, OSError):
                                    pass
                        if last_edited:
                            break
                if last_edited:
                    break
        
        # Also search for "Last Edited" anywhere in the page (even in hidden popup content) - SAME as creationDate
        # FIRST: Specifically target dialog elements (based on XPath: /html/body/div[15]/div/dialog/.../div[4]/p[2])
        if not last_edited:
            # Find all dialog elements
            dialogs = soup.find_all("dialog")
            for dialog in dialogs:
                # Find "Last Edited" text within this dialog
                last_edited_text = dialog.find(string=re.compile(r"Last\s+Edited", re.I))
                if last_edited_text:
                    # Find the parent <p> element containing "Last Edited"
                    parent_p = last_edited_text.find_parent("p")
                    if parent_p:
                        # Find the parent <div> that contains this <p>
                        parent_div = parent_p.find_parent("div")
                        if parent_div:
                            # Get all <p> elements in this div
                            all_ps = parent_div.find_all("p")
                            # Find the index of the "Last Edited" <p>
                            for idx, p_elem in enumerate(all_ps):
                                if p_elem == parent_p:
                                    # Check the next <p> element (p[2] in XPath)
                                    if idx + 1 < len(all_ps):
                                        next_p = all_ps[idx + 1]
                                        next_p_text = next_p.get_text(strip=True)
                                        # Check if it looks like a date
                                        if next_p_text and re.search(r'\d|ago|Today|Yesterday|hours|days|weeks|months|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec', next_p_text, re.I):
                                            date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', next_p_text, re.I)
                                            if date_match:
                                                last_edited = date_match.group(0).strip() if date_match.group(0) else date_match.group(1).strip() if date_match.groups() else next_p_text
                                                break
                                    # Also check all other <p> elements in the same div
                                    for other_p in all_ps:
                                        if other_p != parent_p:
                                            other_p_text = other_p.get_text(strip=True)
                                            if other_p_text and re.search(r'\d|ago|Today|Yesterday|hours|days|weeks|months|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec', other_p_text, re.I):
                                                date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', other_p_text, re.I)
                                                if date_match:
                                                    last_edited = date_match.group(0).strip() if date_match.group(0) else date_match.group(1).strip() if date_match.groups() else other_p_text
                                                    break
                                    if last_edited:
                                        break
                        # Also check next sibling <p> directly
                        if not last_edited:
                            next_sibling_p = parent_p.find_next_sibling("p")
                            if next_sibling_p:
                                next_text = next_sibling_p.get_text(strip=True)
                                if next_text and re.search(r'\d|ago|Today|Yesterday|hours|days|weeks|months|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec', next_text, re.I):
                                    date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', next_text, re.I)
                                    if date_match:
                                        last_edited = date_match.group(0).strip() if date_match.group(0) else date_match.group(1).strip() if date_match.groups() else next_text
                    if last_edited:
                        break
        
        # Then do the general search for "Last Edited" anywhere in the page
        if not last_edited:
            # Find all instances of "Last Edited" text
            all_last_edited = soup.find_all(string=re.compile(r"Last\s+Edited", re.I))
            for last_edited_text in all_last_edited:
                parent = last_edited_text.find_parent()
                if parent:
                    # First, check the immediate parent's text
                    parent_text = parent.get_text()
                    date_match = re.search(r'Last\s+Edited[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', parent_text, re.I)
                    if date_match:
                        last_edited = date_match.group(1).strip()
                        break
                    
                    # Check next sibling of parent
                    next_sib = parent.find_next_sibling()
                    if next_sib:
                        next_text = next_sib.get_text(strip=True)
                        if len(next_text) < 100:  # Dates are usually short
                            date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', next_text, re.I)
                            if date_match:
                                last_edited = date_match.group(0).strip()
                                break
                    
                    # Get all text from parent container and its siblings
                    parent_container = parent.find_parent(["div", "section", "article", "dialog", "li", "tr", "dl"])
                    if parent_container:
                        container_text = parent_container.get_text()
                        # Look for "Last Edited" followed by date in the same container
                        date_match = re.search(r'Last\s+Edited[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', container_text, re.I)
                        if date_match:
                            last_edited = date_match.group(1).strip()
                            break
                    
                    # Also check the row/container structure (common in listing info)
                    row = parent.find_parent(["div", "li", "tr", "dl", "dt"])
                    if row:
                        row_text = row.get_text()
                        # Extract date that appears after "Last Edited" in the same row
                        date_match = re.search(r'Last\s+Edited[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', row_text, re.I)
                        if date_match:
                            last_edited = date_match.group(1).strip()
                            break
                    
                    # Check all children of parent for date-like text
                    for child in parent.find_all(["span", "div", "p", "dd", "td"]):
                        child_text = child.get_text(strip=True)
                        if child_text and len(child_text) < 100:
                            date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', child_text, re.I)
                            if date_match:
                                last_edited = date_match.group(0).strip()
                                break
                    if last_edited:
                        break
                if last_edited:
                    break
        
        # Look for date elements by class (same as creationDate)
        # FIRST: Try the specific Gumtree pattern: <p class="css-1k2npbq-Box e102c3rk0">Last Edited</p>
        # followed by <p class="css-67o0w5-Box e102c3rk0">3 hours ago</p>
        # Both are inside a <div class="css-j523hi-Box e102c3rk0"> container
        if not last_edited:
            # Find "Last Edited" text anywhere in the page
            last_edited_label = soup.find(string=re.compile(r"Last\s+Edited", re.I))
            if last_edited_label:
                # Find the parent <p> element
                parent_p = last_edited_label.find_parent("p")
                if parent_p:
                    # Find the parent container (div with css-* class)
                    container = parent_p.find_parent("div")
                    if container:
                        # Look for the next <p> element within the same container
                        # First try next sibling <p>
                        next_sibling_p = parent_p.find_next_sibling("p")
                        if next_sibling_p:
                            date_text = next_sibling_p.get_text(strip=True)
                            # Check if it looks like a date
                            if date_text and re.search(r'\d|ago|Today|Yesterday|hours|days|weeks|months', date_text, re.I):
                                last_edited = date_text
                        # If not found, search for any <p> element after "Last Edited" in the container
                        if not last_edited:
                            # Get all <p> elements in the container
                            all_ps = container.find_all("p")
                            found_label = False
                            for p_elem in all_ps:
                                if found_label:
                                    # This is the <p> after "Last Edited"
                                    p_text = p_elem.get_text(strip=True)
                                    if p_text and re.search(r'\d|ago|Today|Yesterday|hours|days|weeks|months', p_text, re.I):
                                        last_edited = p_text
                                        break
                                if p_elem == parent_p:
                                    found_label = True
                        # If still not found, try next element (not just sibling)
                        if not last_edited:
                            next_elem = parent_p.find_next(["p", "div", "span"])
                            if next_elem and next_elem != parent_p:
                                next_text = next_elem.get_text(strip=True)
                                if next_text and len(next_text) < 100:
                                    date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', next_text, re.I)
                                    if date_match:
                                        last_edited = date_match.group(0).strip()
                        # Also check parent container's text
                        if not last_edited and container:
                            container_text = container.get_text()
                            date_match = re.search(r'Last\s+Edited[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', container_text, re.I)
                            if date_match:
                                last_edited = date_match.group(1).strip()
                        # Check all siblings after "Last Edited"
                        if not last_edited:
                            for sibling in parent_p.find_next_siblings():
                                sibling_text = sibling.get_text(strip=True)
                                if sibling_text and len(sibling_text) < 100:  # Dates are usually short
                                    date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', sibling_text, re.I)
                                    if date_match:
                                        last_edited = date_match.group(0).strip()
                                        break
        
        # Also search in tabpanel elements (since "Last Edited" is in a "Listing Info" tabpanel)
        if not last_edited:
            # Find tabpanel elements (role="tabpanel")
            tabpanels = soup.find_all(attrs={"role": "tabpanel"})
            for tabpanel in tabpanels:
                # Check if "Last Edited" is in this tabpanel
                if "Last Edited" in tabpanel.get_text():
                    # Find "Last Edited" within this tabpanel
                    last_edited_elem = tabpanel.find(string=re.compile(r"Last\s+Edited", re.I))
                    if last_edited_elem:
                        parent_p = last_edited_elem.find_parent("p")
                        if parent_p:
                            # Find next <p> in the same container
                            container = parent_p.find_parent("div")
                            if container:
                                next_sibling_p = parent_p.find_next_sibling("p")
                                if next_sibling_p:
                                    date_text = next_sibling_p.get_text(strip=True)
                                    if date_text and re.search(r'\d|ago|Today|Yesterday|hours|days|weeks|months', date_text, re.I):
                                        last_edited = date_text
                                        break
                                # If not found, search all <p> elements in container
                                if not last_edited:
                                    all_ps = container.find_all("p")
                                    found_label = False
                                    for p_elem in all_ps:
                                        if found_label:
                                            p_text = p_elem.get_text(strip=True)
                                            if p_text and re.search(r'\d|ago|Today|Yesterday|hours|days|weeks|months', p_text, re.I):
                                                last_edited = p_text
                                                break
                                        if p_elem == parent_p:
                                            found_label = True
                if last_edited:
                    break
        
        # Try to find date in dialog/modal structures (same as creationDate)
        # IMPORTANT: Also check hidden/closed popup elements (data-state="closed")
        # since "Last Edited" is in a popup that might be closed by default
        if not last_edited:
            # Find all dialog/modal elements, including hidden ones
            dialogs = soup.find_all(["dialog", "div"], class_=re.compile(r"dialog|modal|popup", re.I))
            # Also find elements with data-state="closed" (closed popups)
            closed_elements = soup.find_all(attrs={"data-state": "closed"})
            # Also find hidden elements
            hidden_elements = soup.find_all(attrs={"hidden": True}) + \
                            soup.find_all(style=re.compile(r"display\s*:\s*none", re.I))
            
            all_popup_elements = dialogs + closed_elements + hidden_elements
            
            for dialog in all_popup_elements:
                dialog_text = dialog.get_text()
                # Look for "Last Edited" followed by date
                date_match = re.search(r'Last\s+Edited[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', dialog_text, re.I)
                if date_match:
                    last_edited = date_match.group(1).strip()
                    break
                # Also search for "Last Edited" text and find date nearby
                if "Last Edited" in dialog_text:
                    # Find "Last Edited" element and get date from nearby
                    last_edited_elem = dialog.find(string=re.compile(r"Last\s+Edited", re.I))
                    if last_edited_elem:
                        parent = last_edited_elem.find_parent()
                        if parent:
                            # Check next sibling
                            next_sib = parent.find_next_sibling()
                            if next_sib:
                                next_text = next_sib.get_text(strip=True)
                                date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', next_text, re.I)
                                if date_match:
                                    last_edited = date_match.group(0).strip()
                                    break
                            # Check next element
                            if not last_edited:
                                next_elem = parent.find_next(["p", "div", "span"])
                                if next_elem:
                                    next_text = next_elem.get_text(strip=True)
                                    date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', next_text, re.I)
                                    if date_match:
                                        last_edited = date_match.group(0).strip()
                                        break
                if last_edited:
                    break
        
        # Try to find date in specific Gumtree sections (same as creationDate)
        if not last_edited:
            # Look in common Gumtree page sections
            header = soup.find(["header", "div"], class_=re.compile(r"header|ad-header|listing-header", re.I))
            if header:
                header_text = header.get_text()
                date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', header_text, re.I)
                if date_match:
                    last_edited = date_match.group(0).strip()
            
            # Look in sidebar or info sections
            if not last_edited:
                sidebar = soup.find(["aside", "div"], class_=re.compile(r"sidebar|info|details|meta", re.I))
                if sidebar:
                    sidebar_text = sidebar.get_text()
                    date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', sidebar_text, re.I)
                    if date_match:
                        last_edited = date_match.group(0).strip()
        
        # Try to find in text patterns (same as creationDate)
        if not last_edited:
            # More comprehensive date patterns
            date_patterns = [
                r'(\d+\s+(hour|hours)\s+ago)',
                r'(\d+\s+(day|days)\s+ago)',
                r'(\d+\s+(week|weeks)\s+ago)',
                r'(\d+\s+(month|months)\s+ago)',
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # Date format like 20/12/2025
                r'(Today|Yesterday)',
                r'(\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',  # Full date
                r'(Last\s+Edited|Updated|Modified).*?(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago)',  # "Last Edited 2 days ago"
                r'(Last\s+Edited|Updated|Modified).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # "Last Edited 20/12/2025"
                r'(\d{1,2}\s+(hour|hours|day|days|week|weeks|month|months)\s+ago)',  # Just "2 days ago" without prefix
            ]
            for pattern in date_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    # Extract the date part (usually the last group)
                    groups = match.groups()
                    if groups and groups[-1]:
                        last_edited = groups[-1].strip()
                    else:
                        last_edited = match.group(0).strip()
                    # If it's just a word like "hour" or "day", get the full match
                    if len(last_edited) < 5 and groups:
                        last_edited = match.group(0).strip()
                    if last_edited:
                        break
        
        # If still not found, check meta tags (same as creationDate)
        if not last_edited:
            meta_date = soup.find("meta", {"property": "article:modified_time"}) or \
                       soup.find("meta", {"property": "article:updated"}) or \
                       soup.find("meta", {"name": re.compile(r"date.*modified|updated|last.*edit", re.I)})
            if meta_date:
                last_edited = meta_date.get("content", "")
                if "T" in last_edited:
                    last_edited = last_edited.split("T")[0]
        
        # Try to find date in structured data (JSON-LD) (same as creationDate)
        if not last_edited:
            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                try:
                    json_data = json.loads(script.string)
                    if isinstance(json_data, dict):
                        # Check for dateModified or dateUpdated
                        date_modified = json_data.get("dateModified") or json_data.get("dateUpdated")
                        if date_modified:
                            last_edited = date_modified
                            if "T" in last_edited:
                                last_edited = last_edited.split("T")[0]
                            break
                except:
                    pass
        
        # Try to find date in JavaScript variables (same as creationDate)
        if not last_edited:
            # Look for script tags that might contain date data
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string:
                    script_text = script.string
                    # Look for common date variable patterns
                    date_var_patterns = [
                        r'lastEdited["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                        r'updatedAt["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                        r'modifiedAt["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                        r'dateModified["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    ]
                    for pattern in date_var_patterns:
                        match = re.search(pattern, script_text, re.I)
                        if match:
                            last_edited = match.group(1).strip()
                            if "T" in last_edited:
                                last_edited = last_edited.split("T")[0]
                            break
                    if last_edited:
                        break
        
        # Last resort: search all elements for date-like text (same as creationDate)
        # IMPORTANT: Search ALL elements including hidden ones, since "Last Edited" might be in a closed popup
        if not last_edited:
            # First, try searching the entire page text for "Last Edited" followed by a date
            # Use a more aggressive pattern that captures anything after "Last Edited"
            page_text = soup.get_text()
            # Try multiple patterns - be very permissive
            patterns = [
                r'Last\s+Edited[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago)',
                r'Last\s+Edited[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'Last\s+Edited[:\s]*(Today|Yesterday)',
                r'Last\s+Edited[:\s]*(\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
                r'Last\s+Edited[:\s]*([^\n]{0,50})',  # Very permissive - capture up to 50 chars after "Last Edited"
            ]
            for pattern in patterns:
                date_match = re.search(pattern, page_text, re.I)
                if date_match:
                    potential_date = date_match.group(1).strip()
                    # Verify it looks like a date
                    if re.search(r'\d|ago|Today|Yesterday|hours|days|weeks|months|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec', potential_date, re.I):
                        last_edited = potential_date
                        break
            
            # If that didn't work, try to find "Last Edited" text anywhere in the page (including hidden elements)
            if not last_edited:
                all_last_edited_text = soup.find_all(string=re.compile(r"Last\s+Edited", re.I))
                for last_edited_text in all_last_edited_text:
                    parent = last_edited_text.find_parent()
                    if parent:
                        # Check next sibling
                        next_sib = parent.find_next_sibling()
                        if next_sib:
                            next_text = next_sib.get_text(strip=True)
                            if len(next_text) < 100:
                                date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', next_text, re.I)
                                if date_match:
                                    last_edited = date_match.group(0).strip()
                                    break
                        # Check next element
                        if not last_edited:
                            next_elem = parent.find_next(["p", "div", "span"])
                            if next_elem:
                                next_text = next_elem.get_text(strip=True)
                                if len(next_text) < 100:
                                    date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', next_text, re.I)
                                    if date_match:
                                        last_edited = date_match.group(0).strip()
                                        break
                        # Check parent's text
                        if not last_edited:
                            parent_text = parent.get_text()
                            date_match = re.search(r'Last\s+Edited[:\s]*(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday|\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', parent_text, re.I)
                            if date_match:
                                last_edited = date_match.group(1).strip()
                                break
                    if last_edited:
                        break
            
            # If still not found, search all elements for date patterns (including hidden ones)
            if not last_edited:
                all_elements = soup.find_all(["span", "div", "p", "time", "small", "em", "strong"])
                for elem in all_elements:
                    elem_text = elem.get_text(strip=True)
                    if elem_text and len(elem_text) < 50:  # Only check short text (dates are usually short)
                        # Check if it looks like a date
                        date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Today|Yesterday)', elem_text, re.I)
                        if date_match:
                            last_edited = date_match.group(0).strip()
                            break
                    if last_edited:
                        break
        
        # Convert relative date to exact date
        if last_edited:
            exact_edited_date = self._convert_to_exact_date(last_edited)
            details["lastEdited"] = exact_edited_date if exact_edited_date else last_edited
        else:
            details["lastEdited"] = None
        
        # Extract categoryName
        category_name = None
        # From URL (Australian format: /s-ad/location/category/...)
        if "/s-ad/" in url:
            parts = url.split("/s-ad/")[1].split("/")
            if len(parts) >= 2:
                category_name = parts[1].replace("-", " ").title()
        
        # From meta tags
        if not category_name:
            meta_cat = soup.find("meta", {"name": re.compile(r"category|WT\.cg", re.I)})
            if meta_cat:
                category_name = meta_cat.get("content", "")
        
        # From breadcrumbs
        if not category_name:
            breadcrumb = soup.find(["nav", "ol", "ul"], class_=re.compile(r"breadcrumb", re.I))
            if breadcrumb:
                links = breadcrumb.find_all("a")
                if links:
                    category_name = links[-1].get_text(strip=True)
        
        details["categoryName"] = category_name
        
        return details
    
    def scrape_category(self, category: str, location: str = "", max_pages: int = 5, get_details: bool = True, max_listings: int = None) -> List[Dict]:
        """
        Scrape listings from a specific category
        
        Args:
            category: Category name or URL path
            location: Location filter
            max_pages: Maximum number of pages to scrape
            get_details: Whether to fetch detailed information for each listing
            max_listings: Maximum number of listings to scrape (None = scrape all)
        
        Returns:
            List of listing dictionaries
        """
        # Handle category URL (always Australian)
        if category.startswith("http"):
            category_url = category
        else:
            category_url = f"{self.gumtree_config['base_url']}/{category}"
        
        # Split path vs query so we can preserve incoming query params (e.g. ?sort=date)
        parsed_url = urlparse(category_url)
        base_path = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
        base_query_params = parse_qs(parsed_url.query, keep_blank_values=True)
        
        listings = []
        # Global dedupe across pagination within a single job run.
        seen_global: set[str] = set()
        
        for page in range(1, max_pages + 1):
            # Stop if we've reached the max_listings limit
            if max_listings and len(listings) >= max_listings:
                print(f"Reached maximum listings limit ({max_listings}), stopping...")
                break
            
            # Build URL with proper pagination format: /page-{page number}/ before category ID
            # Format: https://www.gumtree.com.au/s-hospitality-tourism/sydney/page-2/c18342l3003435
            if page > 1:
                # Find the category ID pattern (starts with /c followed by alphanumeric)
                # Insert /page-{page}/ before the category ID
                category_id_pattern = re.search(r'(/c[a-z0-9]+)', base_path)
                if category_id_pattern:
                    # Insert page number before category ID
                    category_id_start = category_id_pattern.start()
                    url = base_path[:category_id_start] + f"/page-{page}" + base_path[category_id_start:]
                else:
                    # Fallback: if no category ID pattern found, append /page-{page}/
                    url = f"{base_path.rstrip('/')}/page-{page}/"
            else:
                # Page 1: use URL as-is (no page number in path)
                url = base_path
            
            # Preserve any incoming query params (e.g. sort=date) and merge location if provided
            params = dict(base_query_params)  # values are lists (parse_qs contract)
            if location:
                # Handle None, null, or string "None"
                if location is None or location == "None" or location == "null":
                    location = ""
                else:
                    location = location.strip().strip('"').strip("'")
                    if not location or location.lower() == "none":
                        location = ""
                
                # Only add to params if location is not empty
                if location:
                    params["location"] = [location]
            
            if params:
                query_string = urlencode(params, doseq=True)
                url = f"{url}?{query_string}"
            
            print(f"Scraping category page {page}: {url}")

            # Retry logic for category page: if we get 0 listings (blocked/empty), retry with backoff.
            # Policy: keep render_js=false for the first N-1 attempts, and enable render_js=true only on the last attempt.
            # Default is 4 attempts -> first 3 JS=false, last JS=true.
            max_cat_retries = int(os.environ.get("CATEGORY_RETRIES", "4"))
            backoffs = [5, 10, 20, 40]
            last_error = None
            page_listings = []
            result = None

            attempt = 0
            while attempt < max_cat_retries:
                # Escalation strategy
                kwargs = {}
                if attempt == max_cat_retries - 1:
                    kwargs["render_js"] = True
                else:
                    kwargs["render_js"] = False

                attempt_started = time.time()
                result = self.client.scrape_with_headers(
                    url,
                    headers=self.config["headers"],
                    **kwargs,
                )

                # If Scrapfly itself is having transient issues (5xx), do a couple quick retries
                # even when CATEGORY_RETRIES=1 (otherwise the job fails immediately).
                try:
                    status_code = int(result.get("status_code") or 0)
                except Exception:
                    status_code = 0
                if not result.get("success") and status_code in (502, 503, 504):
                    max_5xx_retries = int(os.environ.get("CATEGORY_5XX_RETRIES", "2"))
                    backoff_s = float(os.environ.get("CATEGORY_5XX_RETRY_BACKOFF_S", "2"))
                    for r in range(max_5xx_retries):
                        # Small linear backoff (keep it short; category fetches are expensive)
                        time.sleep(backoff_s * (r + 1))
                        # Try to refresh session/caches on the last retry
                        extra = {}
                        if r == max_5xx_retries - 1:
                            extra = {"cache": False, "cache_clear": True}
                            try:
                                self.client.session_id = None
                            except Exception:
                                pass
                        attempt_started_5xx = time.time()
                        result = self.client.scrape_with_headers(
                            url,
                            headers=self.config["headers"],
                            **kwargs,
                            **extra,
                        )
                        print(
                            f"  [category_retry 5xx {r + 1}/{max_5xx_retries}] "
                            f"render_js={kwargs.get('render_js')} status_code={status_code} "
                            f"success={bool(result.get('success'))} elapsed={time.time() - attempt_started_5xx:.2f}s"
                        )
                        try:
                            status_code = int(result.get("status_code") or 0)
                        except Exception:
                            status_code = 0
                        if result.get("success"):
                            break

                if not result.get("success"):
                    last_error = result.get("error", "Unknown error")
                    print(
                        f"  [category_retry {attempt + 1}/{max_cat_retries}] "
                        f"render_js={kwargs.get('render_js')} success=false "
                        f"elapsed={time.time() - attempt_started:.2f}s error={str(last_error)[:160]}"
                    )
                    # Wait and retry
                    if attempt < max_cat_retries - 1:
                        time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
                        attempt += 1
                        continue
                    break

                html = result.get("html") or ""
                html_len = len(html)
                ad_link_count = html.count("/s-ad/")
                try:
                    _soup = BeautifulSoup(html, "lxml")
                    page_title = (_soup.title.get_text(strip=True) if _soup.title else "")[:120]
                    canonical = ""
                    canon = _soup.find("link", rel="canonical")
                    if canon and canon.get("href"):
                        canonical = str(canon.get("href"))[:200]
                except Exception:
                    page_title = ""
                    canonical = ""
                print(
                    f"  [category_retry {attempt + 1}/{max_cat_retries}] "
                    f"render_js={kwargs.get('render_js')} success=true "
                    f"elapsed={time.time() - attempt_started:.2f}s html_len={html_len} "
                    f"s_ad_links={ad_link_count} title={page_title!r} canonical={canonical!r}"
                )

                # Heuristic: if non-JS fetch returns an "empty shell" (no title and no listing links),
                # skip remaining non-JS attempts and jump directly to the final JS attempt.
                if (
                    not kwargs.get("render_js")
                    and ad_link_count == 0
                    and not page_title
                    and html_len < int(os.environ.get("CATEGORY_EMPTY_SHELL_MAX_HTML_LEN", "80000"))
                    and attempt < max_cat_retries - 1
                ):
                    print(
                        f"  [category_retry] Detected empty-shell HTML (html_len={html_len}, title empty, s_ad_links=0). "
                        f"Jumping directly to JS attempt {max_cat_retries}/{max_cat_retries}."
                    )
                    # Avoid carrying a potentially "poisoned" session into JS mode.
                    try:
                        self.client.session_id = None
                    except Exception:
                        pass
                    attempt = max_cat_retries - 1
                    continue

                # If we are in JS mode but still got no listing links and a suspicious title (homepage/redirect),
                # retry once with cache_clear and a fresh session.
                if (
                    kwargs.get("render_js")
                    and ad_link_count == 0
                    and attempt == max_cat_retries - 1
                    and page_title in ("www.gumtree.com.au", "Gumtree", "")
                    and not kwargs.get("_js_retry_once")
                ):
                    print(
                        "  [category_retry] JS mode returned 0 listing links with suspicious title; "
                        "retrying once with cache_clear and fresh session."
                    )
                    # Keep the original (non-empty) HTML around for debug if cache_clear returns empty.
                    _best_html = html
                    try:
                        self.client.session_id = None
                    except Exception:
                        pass
                    js_empty_retries = int(os.environ.get("CATEGORY_JS_EMPTY_RETRIES", "2"))
                    js_retry_backoff_s = float(os.environ.get("CATEGORY_JS_EMPTY_RETRY_BACKOFF_S", "2"))
                    for js_try in range(js_empty_retries):
                        attempt_started = time.time()
                        result = self.client.scrape_with_headers(
                            url,
                            headers=self.config["headers"],
                            render_js=True,
                            cache=False,
                            cache_clear=True,
                            _js_retry_once=True,
                        )
                        html = result.get("html") or ""
                        html_len = len(html)
                        ad_link_count = html.count("/s-ad/")
                        try:
                            _soup = BeautifulSoup(html, "lxml")
                            page_title = (_soup.title.get_text(strip=True) if _soup.title else "")[:120]
                            canonical = ""
                            canon = _soup.find("link", rel="canonical")
                            if canon and canon.get("href"):
                                canonical = str(canon.get("href"))[:200]
                        except Exception:
                            page_title = ""
                            canonical = ""
                        print(
                            f"  [category_retry js_cache_clear {js_try + 1}/{js_empty_retries}] render_js=True success={bool(result.get('success'))} "
                            f"elapsed={time.time() - attempt_started:.2f}s html_len={html_len} "
                            f"s_ad_links={ad_link_count} title={page_title!r} canonical={canonical!r}"
                        )
                        # Track last non-empty HTML seen (even if it's not parseable) for debugging.
                        if html.strip():
                            _best_html = html
                        # If we got non-empty HTML, proceed with normal parsing.
                        if html.strip():
                            break
                        # Otherwise wait briefly and retry (transient Scrapfly empty content)
                        if js_try < js_empty_retries - 1:
                            time.sleep(js_retry_backoff_s)

                    # If cache_clear retries returned empty HTML, fall back to best HTML we saw
                    # so we can at least save it for debug rather than ending with an empty blob.
                    if not html.strip() and _best_html and _best_html.strip():
                        html = _best_html
                        html_len = len(html)
                        ad_link_count = html.count("/s-ad/")

                    # Optional extra fallback: try a non-JS fetch once if JS returns empty/redirect-y content.
                    # This sometimes succeeds when Scrapfly JS/CDP is flaky.
                    if (
                        ad_link_count == 0
                        and page_title in ("www.gumtree.com.au", "Gumtree", "")
                        and int(os.environ.get("CATEGORY_REDIRECT_FALLBACK_NONJS", "1")) == 1
                    ):
                        print("  [category_retry] Fallback: trying non-JS fetch once after JS redirect/empty.")
                        try:
                            self.client.session_id = None
                        except Exception:
                            pass
                        r2_started = time.time()
                        r2 = self.client.scrape_with_headers(
                            url,
                            headers=self.config["headers"],
                            render_js=False,
                            cache=False,
                            cache_clear=True,
                            _js_retry_once=True,
                        )
                        html2 = r2.get("html") or ""
                        if html2.strip():
                            html = html2
                            html_len = len(html)
                            ad_link_count = html.count("/s-ad/")
                            try:
                                _soup = BeautifulSoup(html, "lxml")
                                page_title = (_soup.title.get_text(strip=True) if _soup.title else "")[:120]
                                canonical = ""
                                canon = _soup.find("link", rel="canonical")
                                if canon and canon.get("href"):
                                    canonical = str(canon.get("href"))[:200]
                            except Exception:
                                page_title = ""
                                canonical = ""
                        print(
                            f"  [category_retry fallback_nonjs] success={bool(r2.get('success'))} "
                            f"elapsed={time.time() - r2_started:.2f}s html_len={len(html2)} s_ad_links={html2.count('/s-ad/')} "
                            f"title={page_title!r} canonical={canonical!r}"
                        )

                # If html is empty, treat like failure and retry
                if not html.strip():
                    last_error = "empty_html"
                    if attempt < max_cat_retries - 1:
                        time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
                        attempt += 1
                        continue
                    break

                page_listings = self._parse_listings_page(html, url)
                if page_listings:
                    break

                last_error = "parsed_0_listings"
                # Save final HTML for debugging when we cannot parse listings
                if attempt == max_cat_retries - 1:
                    self._save_html_for_debug(html, url)
                if attempt < max_cat_retries - 1:
                    time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
                    attempt += 1
                    continue
                break

            if not page_listings:
                # Preserve old behavior: print failure and move on (or break below if needed)
                if result and not result.get("success"):
                    error_msg = result.get("error", "Unknown error")
                else:
                    error_msg = (last_error or "No listings found") + f" (attempts={max_cat_retries})"
                print(f"Failed to scrape page {page}: {error_msg}")
                continue
            
            # Limit page_listings if max_listings is set
            if max_listings:
                remaining = max_listings - len(listings)
                if remaining <= 0:
                    break
                page_listings = page_listings[:remaining]

            # Dedupe within the page and across pages before fetching details.
            before_page = len(page_listings)
            page_listings = self._dedupe_listings(page_listings)
            # Cross-page filtering (prevents duplicate detail fetches for "Top" ads repeated on page 1/2, etc.)
            filtered: List[Dict] = []
            for it in page_listings:
                k = self._listing_dedupe_key(it)
                if not k:
                    continue
                if k in seen_global:
                    continue
                seen_global.add(k)
                filtered.append(it)
            page_listings = filtered
            after_page = len(page_listings)
            if after_page != before_page:
                print(f"  Dedupe: {before_page} -> {after_page} unique listings on page {page}")
            
            # Get detailed information for each listing if requested
            if get_details:
                print(f"  Fetching details for {len(page_listings)} listings...")
                quota_exceeded = False
                # Hard caps to avoid very long runs when Scrapfly has intermittent gateway timeouts.
                # - MAX_JOB_DURATION_S: max seconds to spend on detail fetching for this page/job (default 600s).
                # - MAX_DETAIL_FAILURES: stop fetching further details after too many transient failures (default 8).
                started_details = time.time()
                max_job_duration_s = int(os.environ.get("MAX_JOB_DURATION_S", "600"))
                max_detail_failures = int(os.environ.get("MAX_DETAIL_FAILURES", "8"))
                detail_failures = 0
                def _should_stop_details() -> bool:
                    if max_job_duration_s > 0 and (time.time() - started_details) > max_job_duration_s:
                        print(
                            f"⚠️  Stopping detail fetch early due to time budget: "
                            f"elapsed={time.time() - started_details:.1f}s > MAX_JOB_DURATION_S={max_job_duration_s}. "
                            f"Returning listings with partial details."
                        )
                        return True
                    if max_detail_failures > 0 and detail_failures >= max_detail_failures:
                        print(
                            f"⚠️  Stopping detail fetch early due to failures: "
                            f"detail_failures={detail_failures} >= MAX_DETAIL_FAILURES={max_detail_failures}. "
                            f"Returning listings with partial details."
                        )
                        return True
                    return False

                def _handle_details_result(listing: Dict, idx1: int, details: Dict):
                    nonlocal detail_failures, quota_exceeded
                    if details.get("success"):
                        # Merge details with listing data (phone from description takes priority)
                        if listing.get("phone"):
                            details["phone"] = listing.get("phone")
                            details["phoneNumberExists"] = True
                            # Add phone reveal URL if we have job_id
                            job_id = listing.get("job_id") or details.get("job_id")
                            if job_id:
                                details["phoneRevealUrl"] = f"https://gt-api.gumtree.com.au/web/vip/reveal-phone-number?adId={job_id}"
                        # Preserve creationDate from search results if detail page doesn't have it
                        if listing.get("creationDate") and not details.get("creationDate"):
                            details["creationDate"] = listing.get("creationDate")
                        listing.update(details)
                        return

                    detail_failures += 1
                    error_msg = details.get("error", "Unknown error")
                    status_code = details.get("status_code", 0)

                    if status_code == 429:
                        print(f"    ⚠️  [{idx1}/{len(page_listings)}] Rate limit (429) - continuing with basic data")
                    elif status_code == 403:
                        print(f"    ❌ [{idx1}/{len(page_listings)}] Scrapfly quota exceeded (403) - stopping scraping")
                        print(f"    Error: {error_msg}")
                        quota_exceeded = True
                    elif status_code == 0 or "timeout" in str(error_msg).lower():
                        print(f"    ⚠️  [{idx1}/{len(page_listings)}] Request failed/timeout - continuing with basic data: {str(error_msg)[:100]}")
                    elif status_code == 504 or "gateway timeout" in str(error_msg).lower():
                        print(f"    ⚠️  [{idx1}/{len(page_listings)}] Scrapfly gateway timeout (504) - continuing with basic data: {str(error_msg)[:100]}")
                    else:
                        print(f"    ⚠️  [{idx1}/{len(page_listings)}] Failed to fetch details - continuing with basic data: {str(error_msg)[:100]}")

                # Controlled parallel detail fetching
                if self.detail_concurrency <= 1:
                    for i, listing in enumerate(page_listings, 1):
                        if _should_stop_details() or quota_exceeded:
                            break
                        if listing.get("url"):
                            if listing.get("phoneNumberExists") and listing.get("phone"):
                                print(f"    [{i}/{len(page_listings)}] Phone found in description, skipping page visit: {listing.get('url', '')[:60]}...")
                                continue
                            print(f"    [{i}/{len(page_listings)}] Fetching: {listing.get('url', '')[:60]}...")
                            details = self.get_listing_details(listing["url"])
                            _handle_details_result(listing, i, details)
                            if quota_exceeded:
                                break
                            time.sleep(self.config["scraping"]["delay"] * 0.5)
                else:
                    to_fetch = []
                    for idx0, listing in enumerate(page_listings):
                        if not listing.get("url"):
                            continue
                        if listing.get("phoneNumberExists") and listing.get("phone"):
                            print(f"    [{idx0 + 1}/{len(page_listings)}] Phone found in description, skipping page visit: {listing.get('url', '')[:60]}...")
                            continue
                        to_fetch.append(idx0)

                    if to_fetch:
                        workers = max(1, min(self.detail_concurrency, 5))
                        with ThreadPoolExecutor(max_workers=workers) as executor:
                            futures = {}
                            cursor = 0

                            def _submit_one(idx0: int):
                                listing = page_listings[idx0]
                                idx1 = idx0 + 1
                                print(f"    [{idx1}/{len(page_listings)}] Fetching: {listing.get('url', '')[:60]}...")
                                fut = executor.submit(self.get_listing_details, listing["url"])
                                futures[fut] = idx0

                            # Prime executor
                            while cursor < len(to_fetch) and len(futures) < workers and not _should_stop_details() and not quota_exceeded:
                                _submit_one(to_fetch[cursor])
                                cursor += 1

                            while futures:
                                if _should_stop_details() or quota_exceeded:
                                    # Cancel pending futures if possible
                                    for fut in list(futures.keys()):
                                        fut.cancel()
                                    break

                                done, _ = wait(set(futures.keys()), timeout=1, return_when=FIRST_COMPLETED)
                                if not done:
                                    continue

                                for fut in done:
                                    idx0 = futures.pop(fut)
                                    listing = page_listings[idx0]
                                    idx1 = idx0 + 1
                                    try:
                                        details = fut.result()
                                    except Exception as exc:
                                        details = {"success": False, "error": str(exc), "status_code": 0}
                                    _handle_details_result(listing, idx1, details)

                                    # Fill the gap
                                    while cursor < len(to_fetch) and len(futures) < workers and not _should_stop_details() and not quota_exceeded:
                                        _submit_one(to_fetch[cursor])
                                        cursor += 1
                
                # Stop scraping if quota exceeded
                if quota_exceeded:
                    print("⚠️  Stopping scraping due to Scrapfly quota exceeded")
                    break
            
            listings.extend(page_listings)
            
            # Stop if we've reached the max_listings limit
            if max_listings and len(listings) >= max_listings:
                listings = listings[:max_listings]
                break
            
            if not page_listings:
                break
            
            time.sleep(self.config["scraping"]["delay"])
        
        # Final global dedupe (extra safety)
        return self._dedupe_listings(listings)
    
    def _save_html_for_debug(self, html: str, url: str):
        """
        Save HTML content to file for debugging purposes
        
        Args:
            html: HTML content to save
            url: URL of the page
        """
        try:
            # Create debug directory if it doesn't exist
            if not os.path.exists(DEBUG_HTML_DIR):
                os.makedirs(DEBUG_HTML_DIR)
            
            # Extract job_id from URL for filename
            job_id = None
            id_match = re.search(r'/(\d+)$', url)
            if id_match:
                job_id = id_match.group(1)
            
            # Create filename with timestamp and job_id
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if job_id:
                filename = f"{DEBUG_HTML_DIR}/listing_{job_id}_{timestamp}.html"
            else:
                # Fallback if no job_id
                url_safe = re.sub(r'[^\w\-_\.]', '_', url)[:100]
                filename = f"{DEBUG_HTML_DIR}/listing_{url_safe}_{timestamp}.html"
            
            # Save HTML to file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            
            print(f"      [DEBUG] Saved HTML to: {filename}")
        except Exception as e:
            # Don't fail the scraping if debug save fails
            print(f"      [DEBUG] Failed to save HTML: {str(e)}")
    
    def close(self):
        """Close the scraper and clean up resources"""
        self.client.close()
