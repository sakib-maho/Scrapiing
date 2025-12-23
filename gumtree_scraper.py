"""
Gumtree Scraper using Scrapfly API
"""
import re
import json
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
        Login to Gumtree account using Scrapfly authenticated session
        
        Returns:
            True if login successful, False otherwise
        """
        try:
            print("Attempting to login to Gumtree...")
            
            # Determine login URL based on site
            if self.is_australian:
                login_url = "https://www.gumtree.com.au/login.html"
            else:
                login_url = self.gumtree_config["login_url"]
            
            # Use Scrapfly with authentication to handle login
            # Scrapfly can maintain session cookies across requests
            login_page = self.client.scrape_with_headers(
                login_url,
                headers=self.config["headers"]
            )
            
            if not login_page["success"]:
                print(f"Failed to load login page: {login_page.get('error')}")
                return False
            
            # Parse the login page to find form fields
            soup = BeautifulSoup(login_page["html"], "lxml")
            
            # Extract CSRF token or other required fields
            csrf_token = self._extract_csrf_token(soup)
            
            # Note: Scrapfly handles authentication via its session management
            # For full login, you may need to:
            # 1. Use Scrapfly's authenticated scraping with cookies
            # 2. Or implement Selenium-based login for complex flows
            
            # Store cookies if available
            cookies = self.client.get_cookies(login_page["url"])
            if cookies:
                self.session_cookies.update(cookies)
            
            # Mark as logged in (Scrapfly will maintain session)
            self.logged_in = True
            print("✓ Login session established (Scrapfly maintains authentication)")
            return True
            
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False
    
    def _extract_csrf_token(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract CSRF token from page"""
        # Look for CSRF token in various places
        csrf_input = soup.find("input", {"name": re.compile(r"csrf|token", re.I)})
        if csrf_input:
            return csrf_input.get("value")
        
        # Check meta tags
        csrf_meta = soup.find("meta", {"name": re.compile(r"csrf", re.I)})
        if csrf_meta:
            return csrf_meta.get("content")
        
        return None
    
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
            # Construct search URL
            search_url = f"{base_search_url}?q={query.replace(' ', '+')}"
            if location:
                search_url += f"&location={location.replace(' ', '+')}"
            if page > 1:
                search_url += f"&page={page}"
            
            print(f"Scraping page {page}: {search_url}")
            
            result = self.client.scrape_with_headers(
                search_url,
                headers=self.config["headers"]
            )
            
            if not result["success"]:
                print(f"Failed to scrape page {page}: {result.get('error')}")
                continue
            
            page_listings = self._parse_listings_page(result["html"], search_url)
            
            # Get detailed information for each listing if requested
            if get_details:
                print(f"  Fetching details for {len(page_listings)} listings...")
                for i, listing in enumerate(page_listings, 1):
                    if listing.get("url"):
                        print(f"    [{i}/{len(page_listings)}] Fetching: {listing.get('url', '')[:60]}...")
                        details = self.get_listing_details(listing["url"])
                        if details.get("success"):
                            # Merge details with listing data
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
            # Look for links - UK uses /p/, Australian uses /s-ad/
            if self.is_australian or "gumtree.com.au" in url:
                listing_links = soup.find_all("a", href=re.compile(r"/s-ad/"))
            else:
                listing_links = soup.find_all("a", href=re.compile(r"/p/"))
            
            for link in listing_links:
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
            # Check for both UK (/p/) and Australian (/s-ad/) patterns
            if not href or ("/p/" not in href and "/s-ad/" not in href):
                return None
            
            # Determine base URL based on pattern
            if "/s-ad/" in href:
                base_url = "https://www.gumtree.com.au"
            else:
                base_url = self.gumtree_config["base_url"]
            
            # Make absolute URL
            if href.startswith("/"):
                url = base_url + href
            elif href.startswith("http"):
                url = href
            else:
                url = base_url + "/" + href
            
            # Extract job_id from URL (the number at the end)
            job_id = None
            id_match = re.search(r'/(\d+)$', url)
            if id_match:
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
            # Check parent element and siblings for date
            parent = link.parent
            if parent:
                parent_text = parent.get_text()
                # Look for date patterns like "4 hours ago", "2 days ago", "20/12/2025"
                date_patterns = [
                    r'(\d+\s+(hour|hours)\s+ago)',
                    r'(\d+\s+(day|days)\s+ago)',
                    r'(\d+\s+(week|weeks)\s+ago)',
                    r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                ]
                for pattern in date_patterns:
                    match = re.search(pattern, parent_text, re.I)
                    if match:
                        creation_date = match.group(0).strip()
                        break
            
            # If not found in parent, check nearby elements
            if not creation_date:
                # Check next sibling elements
                next_elem = link.find_next_sibling()
                if next_elem:
                    next_text = next_elem.get_text()
                    date_match = re.search(r'(\d+\s+(hour|hours|day|days|week|weeks)\s+ago|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', next_text, re.I)
                    if date_match:
                        creation_date = date_match.group(0).strip()
            
            return {
                "job_id": job_id,
                "title": title,
                "url": url,
                "location": location,
                "categoryName": category_name,
                "creationDate": creation_date,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            print(f"Error extracting listing from link: {str(e)}")
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
                if href.startswith("/"):
                    url = self.gumtree_config["base_url"] + href
                else:
                    url = href
            
            # Extract price
            price_elem = element.find(["span", "div"], class_=re.compile(r"price", re.I))
            price = None
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r"£[\d,]+", price_text)
                if price_match:
                    price = price_match.group()
            
            # Extract location
            location_elem = element.find(["span", "div"], class_=re.compile(r"location", re.I))
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Extract description snippet
            desc_elem = element.find(["p", "div"], class_=re.compile(r"description|snippet", re.I))
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            if not title and not url:
                return None
            
            return {
                "title": title,
                "url": url,
                "price": price,
                "location": location,
                "description": description,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            print(f"Error extracting listing data: {str(e)}")
            return None
    
    def get_listing_details(self, listing_url: str) -> Dict:
        """
        Get detailed information for a specific listing
        
        Args:
            listing_url: URL of the listing
        
        Returns:
            Dictionary with detailed listing information
        """
        # IMPORTANT: keep the Scrapfly session across calls.
        # Phone reveal often relies on browser/session context.
        result = self.client.scrape_with_headers(
            listing_url,
            headers=self.config["headers"]
        )
        
        if not result["success"]:
            return {
                "url": listing_url,
                "error": result.get("error"),
                "success": False,
            }
        
        soup = BeautifulSoup(result["html"], "lxml")
        details = self._parse_listing_details(soup, listing_url, scrape_result=result)
        details["success"] = True
        
        return details
    
    def _parse_listing_details(self, soup: BeautifulSoup, url: str, scrape_result: Optional[Dict] = None) -> Dict:
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
        
        # Extract description - try multiple locations
        description = None
        desc_elem = soup.find(["div", "section", "article"], class_=re.compile(r"description|content|body", re.I))
        if desc_elem:
            description = desc_elem.get_text(strip=True)
        else:
            # Try meta description
            meta_desc = soup.find("meta", property="og:description") or soup.find("meta", {"name": "description"})
            if meta_desc:
                description = meta_desc.get("content", "")
            else:
                # Try to find main content area
                main_content = soup.find("main") or soup.find("article")
                if main_content:
                    # Get text but exclude navigation and footer
                    for nav in main_content.find_all(["nav", "header", "footer"]):
                        nav.decompose()
                    description = main_content.get_text(strip=True)
        
        details["description"] = description
        
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
        
        # Extract phone number using PhoneExtractor (handles login wall and API endpoints)
        job_id = details.get("job_id", "")
        phone = self.phone_extractor.extract_phone(soup, url, job_id, scrape_result=scrape_result)
        details["phone"] = phone
        
        # Log if phone was found or not
        if not phone:
            print(f"    ⚠ Phone number not found (no phone on ad OR reveal endpoint blocked)")
        else:
            print(f"    ✓ Phone number extracted: {phone[:10]}...")
        
        # Extract creationDate/posted date
        creation_date = None
        text = soup.get_text()
        
        # Look for date elements with datetime attributes (most reliable)
        date_elem = soup.find(["time"], datetime=True)
        if date_elem:
            creation_date = date_elem.get("datetime", "")
            # If datetime is ISO format, extract just the date part
            if creation_date and "T" in creation_date:
                creation_date = creation_date.split("T")[0]
        
        # Look for date elements by class
        if not creation_date:
            date_elem = soup.find(["time", "span", "div", "p"], class_=re.compile(r"date|time|posted|created|published|ago", re.I))
            if date_elem:
                creation_date = date_elem.get_text(strip=True)
                # Check for datetime attribute
                datetime_attr = date_elem.get("datetime") or date_elem.get("data-date") or date_elem.get("data-time")
                if datetime_attr:
                    creation_date = datetime_attr
                    if "T" in creation_date:
                        creation_date = creation_date.split("T")[0]
        
        # Try to find in text patterns like "X hours ago", "X days ago", dates
        if not creation_date:
            date_patterns = [
                r'(\d+\s+(hour|hours)\s+ago)',
                r'(\d+\s+(day|days)\s+ago)',
                r'(\d+\s+(week|weeks)\s+ago)',
                r'(\d+\s+(month|months)\s+ago)',
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # Date format like 20/12/2025
                r'(Today|Yesterday)',
                r'(\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',  # Full date
            ]
            for pattern in date_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    creation_date = match.group(0).strip()
                    break
        
        # If still not found, check meta tags
        if not creation_date:
            meta_date = soup.find("meta", {"property": "article:published_time"}) or soup.find("meta", {"name": re.compile(r"date|published", re.I)})
            if meta_date:
                creation_date = meta_date.get("content", "")
                if "T" in creation_date:
                    creation_date = creation_date.split("T")[0]
        
        details["creationDate"] = creation_date
        
        # Extract categoryName
        category_name = None
        # From URL
        if "gumtree.com.au" in url and "/s-ad/" in url:
            parts = url.split("/s-ad/")[1].split("/")
            if len(parts) >= 2:
                category_name = parts[1].replace("-", " ").title()
        elif "/p/" in url:
            parts = url.split("/p/")[1].split("/")
            if len(parts) > 0:
                category_name = parts[0].replace("-", " ").title()
        
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
    
    def scrape_category(self, category: str, location: str = "", max_pages: int = 5, get_details: bool = True) -> List[Dict]:
        """
        Scrape listings from a specific category
        
        Args:
            category: Category name or URL path
            location: Location filter
            max_pages: Maximum number of pages to scrape
        
        Returns:
            List of listing dictionaries
        """
        # Detect if this is an Australian URL
        if category.startswith("http"):
            category_url = category
            if "gumtree.com.au" in category_url:
                self.is_australian = True
                # Update Scrapfly country setting for Australian site
                self.client.api_key = self.config["scrapfly"]["api_key"]
        else:
            category_url = f"{self.gumtree_config['base_url']}/{category}"
        
        listings = []
        
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
            
            if not result["success"]:
                print(f"Failed to scrape page {page}: {result.get('error')}")
                continue
            
            page_listings = self._parse_listings_page(result["html"], url)
            
            # Get detailed information for each listing if requested
            if get_details:
                print(f"  Fetching details for {len(page_listings)} listings...")
                for i, listing in enumerate(page_listings, 1):
                    if listing.get("url"):
                        print(f"    [{i}/{len(page_listings)}] Fetching: {listing.get('url', '')[:60]}...")
                        details = self.get_listing_details(listing["url"])
                        if details.get("success"):
                            # Merge details with listing data
                            listing.update(details)
                        time.sleep(self.config["scraping"]["delay"] * 0.5)  # Shorter delay for details
            
            listings.extend(page_listings)
            
            if not page_listings:
                break
            
            time.sleep(self.config["scraping"]["delay"])
        
        return listings
    
    def close(self):
        """Close the scraper and clean up resources"""
        self.client.close()
