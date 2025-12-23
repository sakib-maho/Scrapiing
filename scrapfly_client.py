"""
Scrapfly API Client for Web Scraping
- Keeps a stable Scrapfly session key for cookie + navigation + proxy stickiness
- Forwards custom headers using Scrapfly "headers[Name]=Value" format
- Returns browser_data (XHR capture) and response headers if present
"""

from __future__ import annotations

import re
import time
import uuid
from typing import Any, Dict, Optional

import requests
from retrying import retry

from config import SCRAPFLY_CONFIG, REQUEST_TIMEOUT, DELAY_BETWEEN_REQUESTS


class ScrapflyClient:
    def __init__(self, api_key: str = None, session_id: str = None):
        self.api_key = api_key or SCRAPFLY_CONFIG["api_key"]
        self.api_url = SCRAPFLY_CONFIG["url"]

        # Always keep a stable session unless caller explicitly sets one.
        # This helps with cookie continuity and sticky proxy behavior.
        self.session_id = session_id or f"gumtree-{uuid.uuid4().hex}"

        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    @staticmethod
    def _infer_country(url: str, fallback: str) -> str:
        if "gumtree.com.au" in (url or "").lower():
            return "AU"
        return fallback

    @staticmethod
    def _flatten_headers(headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """
        Scrapfly supports passing headers via query params:
          headers[User-Agent]=...
          headers[Accept-Language]=...
        """
        out: Dict[str, str] = {}
        if not headers:
            return out
        for k, v in headers.items():
            if v is None:
                continue
            out[f"headers[{k}]"] = str(v)
        return out

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def scrape(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Returns a dict compatible with PhoneExtractor expectations:
          {
            "success": bool,
            "url": ...,
            "html": ...,
            "response": <full scrapfly JSON>,
            "browser_data": ...,
            ...
          }
        """
        method = (method or "GET").upper()

        render_js = kwargs.pop("render_js", SCRAPFLY_CONFIG.get("render_js", True))
        premium_proxy = kwargs.pop("premium_proxy", SCRAPFLY_CONFIG.get("premium_proxy", True))
        asp = kwargs.pop("asp", SCRAPFLY_CONFIG.get("asp", True))

        # This is Scrapfly debug param (not your app debug).
        # When True, Scrapfly often returns richer diagnostic/network structures.
        debug = kwargs.pop("debug", False)

        # Sticky proxy keeps the same exit IP per session (helps stateful flows).
        session_sticky_proxy = kwargs.pop("session_sticky_proxy", True)

        country = self._infer_country(url, kwargs.pop("country", SCRAPFLY_CONFIG.get("country", "GB")))

        params: Dict[str, Any] = {
            "key": self.api_key,
            "url": url,
            "render_js": str(bool(render_js)).lower(),
            "country": country,
            "premium_proxy": str(bool(premium_proxy)).lower(),
            "asp": str(bool(asp)).lower(),
            "session": self.session_id,
            "session_sticky_proxy": str(bool(session_sticky_proxy)).lower(),
        }

        if debug:
            params["debug"] = "true"

        # Pass-through any other Scrapfly params
        for k, v in kwargs.items():
            if v is None:
                continue
            params[k] = v

        # Forward headers in Scrapfly "headers[...]" form
        params.update(self._flatten_headers(headers))

        try:
            resp = self.session.request(
                method=method,
                url=self.api_url,
                params=params,
                data=body,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()

            data = resp.json() if resp.content else {}
            result = data.get("result", {}) if isinstance(data, dict) else {}
            if not isinstance(result, dict):
                result = {}

            time.sleep(DELAY_BETWEEN_REQUESTS)

            return {
                "success": True,
                "url": url,
                "html": result.get("content", "") or "",
                "status_code": result.get("status_code", resp.status_code),
                "cookies": result.get("cookies", {}) or {},
                "browser_data": result.get("browser_data", {}) or {},
                "result_headers": result.get("headers", {}) or {},
                "response": data,  # full payload (PhoneExtractor mines this)
                "session_id": self.session_id,
                "country": country,
            }

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if getattr(e, "response", None) is not None else 0
            if status == 429:
                retry_after = 60
                ra = e.response.headers.get("Retry-After") if e.response is not None else None
                if ra and re.match(r"^\d+$", ra.strip()):
                    retry_after = int(ra.strip())
                return {
                    "success": False,
                    "url": url,
                    "error": f"429 Rate Limit Exceeded. Wait {retry_after} seconds before retrying.",
                    "html": "",
                    "status_code": 429,
                    "retry_after": retry_after,
                }
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "html": "",
                "status_code": status,
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
        return self.scrape(url, headers=headers, **kwargs)

    def close(self):
        self.session.close()
