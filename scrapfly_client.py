"""
Scrapfly API Client for Web Scraping
"""
import requests
import time
import json
from typing import Dict, Optional, Any
from config import SCRAPFLY_CONFIG, REQUEST_TIMEOUT, DELAY_BETWEEN_REQUESTS
from retrying import retry


class ScrapflyClient:
    """Client for interacting with Scrapfly API"""
    
    def __init__(self, api_key: str = None, session_id: str = None):
        self.api_key = api_key or SCRAPFLY_CONFIG["api_key"]
        self.api_url = SCRAPFLY_CONFIG["url"]
        self.session_id = session_id  # Scrapfly session ID for maintaining cookies
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        })
    
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Scrape a URL using Scrapfly API
        
        Args:
            url: URL to scrape
            **kwargs: Additional Scrapfly parameters
        
        Returns:
            Dictionary containing response data
        """
        # Extract headers if provided
        custom_headers = kwargs.pop("headers", None)
        
        # Build request payload
        payload = {
            "url": url,
            "render_js": kwargs.get("render_js", SCRAPFLY_CONFIG.get("render_js", True)),
            "country": kwargs.get("country", SCRAPFLY_CONFIG.get("country", "GB")),
            "premium_proxy": kwargs.get("premium_proxy", SCRAPFLY_CONFIG.get("premium_proxy", True)),
            "asp": kwargs.get("asp", SCRAPFLY_CONFIG.get("asp", True)),
        }
        
        # Add custom headers if provided
        if custom_headers:
            payload["headers"] = custom_headers
        
        # Add any other additional parameters
        for key, value in kwargs.items():
            if key not in ["render_js", "country", "premium_proxy", "asp", "headers"]:
                payload[key] = value
        
        try:
            # Scrapfly API uses GET with query parameters
            # Detect country from URL if Australian
            country = payload["country"]
            if "gumtree.com.au" in url:
                country = "AU"
            
            # Build query parameters
            query_params = {
                "url": url,
                "render_js": str(payload["render_js"]).lower(),
                "country": country,
                "premium_proxy": str(payload["premium_proxy"]).lower(),
                "asp": str(payload["asp"]).lower(),
            }
            
            # Add session ID if available (for maintaining authentication)
            if self.session_id:
                query_params["session"] = self.session_id
            
            # Add headers as a JSON string if provided
            if custom_headers:
                query_params["headers"] = json.dumps(custom_headers)
            
            response = self.session.get(
                self.api_url,
                params=query_params,
                timeout=REQUEST_TIMEOUT
            )
            
            response.raise_for_status()
            
            data = response.json()
            
            # Extract and store session ID from response if available
            result_data = data.get("result", {})
            if "session" in result_data and not self.session_id:
                self.session_id = result_data["session"]
            
            # Add delay between requests
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
            return {
                "success": True,
                "url": url,
                "html": result_data.get("content", ""),
                "status_code": result_data.get("status_code", 200),
                "response": data,
                "session_id": self.session_id,  # Return session ID for reuse
            }
            
        except requests.exceptions.HTTPError as e:
            # Handle rate limiting (429 errors)
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait_seconds = int(retry_after)
                    except ValueError:
                        wait_seconds = 60  # Default to 60 seconds
                else:
                    wait_seconds = 60  # Default wait time
                
                return {
                    "success": False,
                    "url": url,
                    "error": f"429 Rate Limit Exceeded. Wait {wait_seconds} seconds before retrying.",
                    "html": "",
                    "status_code": 429,
                    "retry_after": wait_seconds,
                }
            
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "html": "",
                "status_code": e.response.status_code if hasattr(e, 'response') else 0,
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "html": "",
                "status_code": 0,
            }
    
    def scrape_with_headers(self, url: str, headers: Dict = None, **kwargs) -> Dict[str, Any]:
        """
        Scrape a URL with custom headers
        
        Args:
            url: URL to scrape
            headers: Custom headers to use (Note: Scrapfly handles headers automatically)
            **kwargs: Additional Scrapfly parameters
        
        Returns:
            Dictionary containing response data
        """
        # Scrapfly automatically handles headers, so we can just call scrape
        # Custom headers are optional as Scrapfly uses its own headers
        return self.scrape(url, **kwargs)
    
    def get_cookies(self, url: str) -> Dict[str, str]:
        """
        Get cookies from a Scrapfly request
        
        Args:
            url: URL to get cookies from
        
        Returns:
            Dictionary of cookies
        """
        result = self.scrape(url)
        if result["success"]:
            # Extract cookies from response if available
            response_data = result.get("response", {})
            cookies = response_data.get("result", {}).get("cookies", {})
            return cookies
        return {}
    
    def close(self):
        """Close the session"""
        self.session.close()
