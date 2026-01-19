"""
Scrapfly API Client for Web Scraping
"""
import os
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
        # Scrapfly API key can be in header or query parameter
        self.session.headers.update({
            "X-API-KEY": self.api_key,
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
        # Internal: allow limited 422 retries (Scrapfly can return 422 for unsupported options on some plans/keys)
        _retry_422_count = int(kwargs.pop("_retry_422_count", 0))
        _max_422_retries = int(kwargs.pop("max_422_retries", os.environ.get("SCRAPFLY_422_MAX_RETRIES", "3")))
        
        # Build request payload
        payload = {
            "url": url,
            "render_js": kwargs.get("render_js", SCRAPFLY_CONFIG.get("render_js", True)),
            "country": kwargs.get("country", SCRAPFLY_CONFIG.get("country", "AU")),
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
                "key": self.api_key,  # API key in query string
                "url": url,
                "render_js": "true" if payload["render_js"] else "false",
                "country": country,
                "premium_proxy": "true" if payload["premium_proxy"] else "false",
                "asp": "true" if payload["asp"] else "false",
            }

            # Include any additional Scrapfly parameters (e.g., cache, cache_clear, etc.)
            # NOTE: headers are handled separately via headers[Header-Name] params.
            for k, v in payload.items():
                if k in ("url", "render_js", "country", "premium_proxy", "asp", "headers"):
                    continue
                if isinstance(v, bool):
                    query_params[k] = "true" if v else "false"
                elif v is None:
                    continue
                else:
                    query_params[k] = str(v)
            
            if self.session_id:
                query_params["session"] = self.session_id
            
            # Scrapfly expects headers as individual query parameters: headers[Header-Name]=value
            # Example: headers[User-Agent]=Mozilla/5.0...
            if custom_headers:
                for header_name, header_value in custom_headers.items():
                    # Use bracket notation for nested parameters
                    query_params[f"headers[{header_name}]"] = str(header_value)
            
            # Use GET request with query parameters
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
            # Get detailed error message
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.text
                    error_detail = f"{str(e)} - Response: {error_body[:500]}"
                except:
                    pass

            # Special handling for 422 (unprocessable entity) from Scrapfly API:
            # Often indicates plan/key doesn't allow certain options (asp/premium_proxy).
            # Retry a few times with safer params (disable asp/premium_proxy) to avoid hard failure.
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 422:
                if _retry_422_count < _max_422_retries:
                    # Backoff a bit to avoid immediate rejections
                    time.sleep(2 * (_retry_422_count + 1))
                    return self.scrape(
                        url,
                        headers=custom_headers,
                        render_js=payload.get("render_js", False),
                        country=payload.get("country", "AU"),
                        premium_proxy=False,
                        asp=False,
                        _retry_422_count=_retry_422_count + 1,
                        max_422_retries=_max_422_retries,
                    )
            
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
            
            # Handle quota exceeded (403 errors)
            if e.response.status_code == 403:
                return {
                    "success": False,
                    "url": url,
                    "error": "403 Forbidden - Scrapfly quota/credits may be exhausted. Check your Scrapfly account.",
                    "html": "",
                    "status_code": 403,
                }
            
            return {
                "success": False,
                "url": url,
                "error": error_detail,
                "html": "",
                "status_code": e.response.status_code if hasattr(e, 'response') and e.response else 0,
            }
        except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout) as e:
            # Timeout exceptions - let retry decorator handle these
            raise  # Re-raise so @retry decorator can retry
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
            headers: Custom headers to use
            **kwargs: Additional Scrapfly parameters
        
        Returns:
            Dictionary containing response data
        """
        # Pass headers to scrape method
        if headers:
            kwargs["headers"] = headers
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
