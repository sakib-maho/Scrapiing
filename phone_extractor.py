"""
Phone number extraction with authentication support
Handles phone numbers that may be behind login wall or require secondary API calls
"""
import re
import json
from typing import Optional, Dict
from bs4 import BeautifulSoup
from scrapfly_client import ScrapflyClient


class PhoneExtractor:
    """Extract phone numbers with authentication support"""
    
    def __init__(self, client: ScrapflyClient):
        self.client = client
    
    def extract_phone(self, soup: BeautifulSoup, url: str, job_id: str = None) -> Optional[str]:
        """
        Extract phone number from listing page
        
        Args:
            soup: BeautifulSoup object of the listing page
            url: Listing URL
            job_id: Job ID to exclude from phone patterns
        
        Returns:
            Phone number if found, None otherwise
        """
        # Step 1: Check if phone is directly visible in HTML (after login)
        phone = self._extract_phone_from_html(soup, job_id)
        if phone:
            return phone
        
        # Step 2: Check for "Show phone" or "Reveal phone" buttons
        reveal_button = self._find_reveal_phone_button(soup)
        if reveal_button:
            # Phone might be in data attributes
            phone = self._extract_phone_from_data_attributes(reveal_button)
            if phone:
                return phone
            
            # Phone might require API call
            api_endpoint = self._find_phone_api_endpoint(soup, url, job_id)
            if api_endpoint:
                phone = self._fetch_phone_from_api(api_endpoint, url, job_id)
                if phone:
                    return phone
        
        # Step 3: Check JavaScript for phone reveal endpoints
        api_endpoint = self._extract_phone_endpoint_from_js(soup, url, job_id)
        if api_endpoint:
            phone = self._fetch_phone_from_api(api_endpoint, url, job_id)
            if phone:
                return phone
        
        # Step 4: Always try API endpoint construction (even without reveal button)
        # Some listings might have phone behind API without visible button
        if job_id:
            api_endpoint = self._find_phone_api_endpoint(soup, url, job_id)
            if api_endpoint:
                phone = self._fetch_phone_from_api(api_endpoint, url, job_id)
                if phone:
                    return phone
        
        return None
    
    def _extract_phone_from_html(self, soup: BeautifulSoup, job_id: str = None) -> Optional[str]:
        """Extract phone number directly from HTML (if visible after login)"""
        # First check for tel: links (most reliable)
        tel_link = soup.find("a", href=re.compile(r"tel:"))
        if tel_link:
            phone_href = tel_link.get("href", "")
            phone_match = re.search(r"tel:([^\s]+)", phone_href)
            if phone_match:
                phone = phone_match.group(1).replace("tel:", "").replace("%20", "").replace("-", "")
                # Validate it's a real phone number
                if self._is_valid_phone(phone, job_id):
                    return phone
        
        # Check for data-phone attributes
        phone_elem = soup.find(attrs={"data-phone": True})
        if phone_elem:
            phone = phone_elem.get("data-phone", "").strip()
            if self._is_valid_phone(phone, job_id):
                return phone
        
        # Check text content for phone patterns (only if we're authenticated)
        text = soup.get_text()
        phone_patterns = [
            r'(\+?61\s?[2-9]\d{1}\s?\d{4}\s?\d{4})',  # Landline with country code
            r'(\+?61\s?4\d{2}\s?\d{3}\s?\d{3})',  # Mobile with country code
            r'(0[2-9]\d{1}\s?\d{4}\s?\d{4})',  # Landline
            r'(04\d{2}\s?\d{3}\s?\d{3})',  # Mobile
            r'\(0\d{2}\)\s?\d{4}\s?\d{4}',  # Formatted with area code
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                phone_candidate = match if isinstance(match, str) else ''.join(match)
                phone_candidate = phone_candidate.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                if self._is_valid_phone(phone_candidate, job_id):
                    return match.strip()
        
        return None
    
    def _find_reveal_phone_button(self, soup: BeautifulSoup):
        """Find button or link that reveals phone number"""
        # Look for buttons/links with text like "Show phone", "Show number", "Reveal phone", etc.
        reveal_texts = [
            r'show.*phone',
            r'show.*number',  # Added: "Show number" (common on Gumtree)
            r'reveal.*phone',
            r'reveal.*number',
            r'view.*phone',
            r'contact.*phone',
            r'phone.*number',
            r'display.*phone',
        ]
        
        for pattern in reveal_texts:
            # Check by text content (more flexible)
            elements = soup.find_all(
                ["button", "a", "span", "div"],
                string=re.compile(pattern, re.I)
            )
            if elements:
                return elements[0]
            
            # Check by text content in child elements
            elements = soup.find_all(
                ["button", "a", "span", "div"],
                string=lambda text: text and re.search(pattern, text, re.I)
            )
            if elements:
                return elements[0]
            
            # Also check by class/id
            elements = soup.find_all(
                ["button", "a"],
                class_=re.compile(pattern, re.I)
            )
            if elements:
                return elements[0]
        
        # Also check for links with phone icon or specific attributes
        phone_links = soup.find_all("a", href=re.compile(r'phone|contact|reveal|show', re.I))
        for link in phone_links:
            link_text = link.get_text(strip=True).lower()
            if any(word in link_text for word in ['show', 'reveal', 'view', 'phone', 'number']):
                return link
        
        return None
    
    def _extract_phone_from_data_attributes(self, element) -> Optional[str]:
        """Extract phone from data attributes of reveal button"""
        data_attrs = [
            "data-phone",
            "data-contact-phone",
            "data-phone-number",
            "data-reveal-phone",
            "data-number",
            "data-contact",
        ]
        
        for attr in data_attrs:
            phone = element.get(attr)
            if phone:
                return phone.strip()
        
        # Also check parent elements
        parent = element.parent if hasattr(element, 'parent') else None
        if parent:
            for attr in data_attrs:
                phone = parent.get(attr)
                if phone:
                    return phone.strip()
        
        return None
    
    def _find_phone_api_endpoint(self, soup: BeautifulSoup, url: str, job_id: str) -> Optional[str]:
        """Find API endpoint for fetching phone number"""
        # Common patterns for phone reveal endpoints
        base_url = "https://www.gumtree.com.au" if "gumtree.com.au" in url else "https://www.gumtree.com"
        
        # First, check if reveal button has href or data attributes with endpoint
        reveal_button = self._find_reveal_phone_button(soup)
        if reveal_button:
            # Check href attribute
            href = reveal_button.get("href", "") if hasattr(reveal_button, 'get') else ""
            if href and ("api" in href.lower() or "phone" in href.lower() or "contact" in href.lower()):
                if href.startswith("http"):
                    return href
                elif href.startswith("/"):
                    return base_url + href
                else:
                    return base_url + "/" + href
            
            # Check onclick or data attributes for endpoint
            onclick = reveal_button.get("onclick", "") if hasattr(reveal_button, 'get') else ""
            if onclick:
                # Extract URL from onclick
                url_match = re.search(r'["\']([^"\']*(?:api|phone|contact)[^"\']*)["\']', onclick, re.I)
                if url_match:
                    endpoint = url_match.group(1)
                    if endpoint.startswith("http"):
                        return endpoint
                    elif endpoint.startswith("/"):
                        return base_url + endpoint
                    else:
                        return base_url + "/" + endpoint
            
            # Check data attributes
            for attr in ["data-url", "data-endpoint", "data-api", "data-href"]:
                endpoint = reveal_button.get(attr, "") if hasattr(reveal_button, 'get') else ""
                if endpoint:
                    if endpoint.startswith("http"):
                        return endpoint
                    elif endpoint.startswith("/"):
                        return base_url + endpoint
                    else:
                        return base_url + "/" + endpoint
        
        # Try to construct endpoint from URL structure
        if job_id:
            # Try multiple endpoint patterns for Australian Gumtree
            if "/s-ad/" in url:
                endpoints = [
                    f"{base_url}/api/ads/{job_id}/phone",
                    f"{base_url}/api/v1/ads/{job_id}/phone",
                    f"{base_url}/api/contact/{job_id}/phone",
                    f"{base_url}/api/ads/{job_id}/contact",
                    f"{base_url}/s-ad/api/phone/{job_id}",
                    f"{base_url}/api/phone/{job_id}",
                ]
                # Return first pattern (we'll try all in _fetch_phone_from_api if needed)
                return endpoints[0]
            
            # UK Gumtree pattern
            if "/p/" in url:
                endpoints = [
                    f"{base_url}/api/ads/{job_id}/phone",
                    f"{base_url}/api/v1/ads/{job_id}/phone",
                    f"{base_url}/api/contact/{job_id}/phone",
                ]
                return endpoints[0]
        
        return None
    
    def _extract_phone_endpoint_from_js(self, soup: BeautifulSoup, url: str, job_id: str) -> Optional[str]:
        """Extract phone API endpoint from JavaScript code"""
        script_tags = soup.find_all("script")
        base_url = "https://www.gumtree.com.au" if "gumtree.com.au" in url else "https://www.gumtree.com"
        
        endpoint_patterns = [
            r'["\']([^"\']*api[^"\']*phone[^"\']*)["\']',
            r'["\']([^"\']*api[^"\']*number[^"\']*)["\']',  # Added: "api*number"
            r'["\']([^"\']*contact[^"\']*api[^"\']*)["\']',
            r'["\']([^"\']*reveal[^"\']*phone[^"\']*)["\']',
            r'["\']([^"\']*reveal[^"\']*number[^"\']*)["\']',  # Added: "reveal*number"
            r'["\']([^"\']*show[^"\']*number[^"\']*)["\']',  # Added: "show*number"
            r'["\']([^"\']*ads[^"\']*phone[^"\']*)["\']',
            r'["\']([^"\']*ads[^"\']*contact[^"\']*)["\']',  # Added: "ads*contact"
            r'url:\s*["\']([^"\']*phone[^"\']*)["\']',
            r'url:\s*["\']([^"\']*number[^"\']*)["\']',  # Added: url with "number"
            r'endpoint:\s*["\']([^"\']*phone[^"\']*)["\']',  # Added: endpoint with "phone"
            r'endpoint:\s*["\']([^"\']*contact[^"\']*)["\']',  # Added: endpoint with "contact"
        ]
        
        for script in script_tags:
            script_text = script.get_text()
            for pattern in endpoint_patterns:
                matches = re.findall(pattern, script_text, re.I)
                for match in matches:
                    # Make absolute URL if relative
                    if match.startswith("/"):
                        return base_url + match
                    elif match.startswith("http"):
                        return match
                    elif "api" in match.lower():
                        return base_url + "/" + match
        
        return None
    
    def _fetch_phone_from_api(self, endpoint: str, listing_url: str, job_id: str = None) -> Optional[str]:
        """Fetch phone number from API endpoint using authenticated session"""
        # If endpoint is a pattern, try multiple variations
        base_url = "https://www.gumtree.com.au" if "gumtree.com.au" in listing_url else "https://www.gumtree.com"
        
        endpoints_to_try = [endpoint]
        
        # If it's a constructed endpoint, try variations
        if job_id and "/api/ads/" in endpoint:
            endpoints_to_try = [
                endpoint,
                endpoint.replace("/api/ads/", "/api/v1/ads/"),
                endpoint.replace("/api/ads/", "/api/contact/"),
                endpoint.replace("/phone", "/contact"),
                f"{base_url}/api/phone/{job_id}",
                f"{base_url}/api/contact/{job_id}",
            ]
        
        for api_endpoint in endpoints_to_try:
            try:
                # Use Scrapfly to make the API call with same session
                # Use POST method as Gumtree might require POST for phone reveal
                result = self.client.scrape(api_endpoint)
                
                if result["success"]:
                    # Try to parse JSON response
                    try:
                        data = json.loads(result["html"])
                        # Common response formats
                        phone = (
                            data.get("phone") or
                            data.get("phoneNumber") or
                            data.get("contactPhone") or
                            data.get("number") or
                            data.get("data", {}).get("phone") or
                            data.get("data", {}).get("phoneNumber") or
                            data.get("result", {}).get("phone") or
                            data.get("result", {}).get("phoneNumber")
                        )
                        if phone and self._is_valid_phone(phone, job_id):
                            return str(phone).strip()
                    except (json.JSONDecodeError, AttributeError):
                        # If not JSON, try to extract from HTML/text
                        soup = BeautifulSoup(result["html"], "lxml")
                        phone = self._extract_phone_from_html(soup, job_id)
                        if phone:
                            return phone
            except Exception as e:
                # Try next endpoint if this one fails
                continue
        
        return None
    
    def _is_valid_phone(self, phone: str, job_id: str = None) -> bool:
        """Validate that a phone number is actually a phone, not a job ID or other number"""
        if not phone:
            return False
        
        # Remove formatting
        clean_phone = re.sub(r'[^\d+]', '', phone)
        
        # Exclude job IDs
        if job_id and clean_phone == job_id:
            return False
        
        # Australian phone validation
        # Should be 10 digits (with or without country code)
        digits_only = re.sub(r'[^\d]', '', clean_phone)
        
        # Remove country code if present
        if digits_only.startswith("61"):
            digits_only = digits_only[2:]
        elif digits_only.startswith("+61"):
            digits_only = digits_only[3:]
        
        # Should be 10 digits for Australian numbers
        if len(digits_only) == 10:
            # Should start with 0 for local format or 4 for mobile
            if digits_only.startswith("0") or digits_only.startswith("4"):
                return True
        
        return False
