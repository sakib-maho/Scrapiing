"""scrapfly_client.py

Scrapfly Web Scraping API client used by this project.

Why this wrapper exists:
 - Keep a single Scrapfly *session* across multiple requests (required for flows like
   Gumtree's "reveal phone" which depends on same browser/session context).
 - Support Scrapfly browser features (render_js, wait_for_selector, js_scenario) and
   expose browser_data (especially XHR captures) to higher-level extractors.

Docs references (important for parameters/behavior):
 - Javascript Rendering / browser_data.xhr_call: https://scrapfly.io/docs/scrape-api/javascript-rendering
 - Javascript Scenario: https://scrapfly.io/docs/scrape-api/javascript-scenario
 - Debug: https://scrapfly.io/docs/scrape-api/debug
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any, Dict, Optional, Union

import requests
from retrying import retry

from config import DELAY_BETWEEN_REQUESTS, REQUEST_TIMEOUT, SCRAPFLY_CONFIG


JsonLike = Union[dict, list]


class ScrapflyClient:
    """Client for interacting with Scrapfly API."""

    def __init__(self, api_key: Optional[str] = None, session_id: Optional[str] = None):
        self.api_key = api_key or SCRAPFLY_CONFIG["api_key"]
        self.api_url = SCRAPFLY_CONFIG["url"]

        # Scrapfly session id (NOT your python requests session) - enables cookie/proxy stickiness.
        self.session_id = session_id

        self.session = requests.Session()
        # Scrapfly supports key either as query param or via header. We keep the header,
        # but also send key as a query param for maximum compatibility.
        self.session.headers.update({
            "X-API-KEY": self.api_key,
            "Accept": "application/json",
        })

    @staticmethod
    def _detect_country(url: str, default_country: str) -> str:
        # Gumtree AU blocks certain content when accessed from outside AU.
        if "gumtree.com.au" in url:
            return "AU"
        return default_country

    @staticmethod
    def _flatten_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """Scrapfly expects headers via query params: headers[Name]=Value."""
        flat: Dict[str, str] = {}
        for k, v in headers.items():
            if v is None:
                continue
            flat[f"headers[{k}]"] = str(v)
        return flat

    @staticmethod
    def _b64_json(value: JsonLike) -> str:
        raw = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return base64.b64encode(raw).decode("ascii")

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def scrape(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Scrape a URL through Scrapfly.

        Supported kwargs used in this project:
          - render_js: bool
          - wait_for_selector: str
          - rendering_wait: int (ms)
          - js_scenario: list|dict|str (if list/dict it'll be base64-encoded)
          - debug: bool
          - country: str
          - asp: bool
          - premium_proxy: bool
          - session_sticky_proxy: bool (recommended True when using sessions)
          - headers: dict[str,str] (sent as Scrapfly headers[...])
          - method: HTTP method to use for the target request (rarely needed here)
          - body: raw body for POST/PUT (rare)
          - content_type: request content-type when using body
        """

        method = str(kwargs.pop("method", "GET")).upper()
        headers: Optional[Dict[str, str]] = kwargs.pop("headers", None)

        # Base defaults
        render_js = bool(kwargs.pop("render_js", SCRAPFLY_CONFIG.get("render_js", True)))
        default_country = str(kwargs.pop("country", SCRAPFLY_CONFIG.get("country", "GB")))
        asp = bool(kwargs.pop("asp", SCRAPFLY_CONFIG.get("asp", True)))
        premium_proxy = bool(kwargs.pop("premium_proxy", SCRAPFLY_CONFIG.get("premium_proxy", True)))
        debug = bool(kwargs.pop("debug", False))

        # AU detection override
        country = self._detect_country(url, default_country)

        query_params: Dict[str, Any] = {
            "key": self.api_key,
            "url": url,
            "render_js": str(render_js).lower(),
            "country": country,
            "premium_proxy": str(premium_proxy).lower(),
            "asp": str(asp).lower(),
        }

        # Keep session context (cookies + proxy stickiness)
        if self.session_id:
            query_params["session"] = self.session_id
            # Unless explicitly overridden, keep the proxy sticky.
            if "session_sticky_proxy" not in kwargs:
                kwargs["session_sticky_proxy"] = True

        # Optional browser controls
        if "wait_for_selector" in kwargs and kwargs["wait_for_selector"]:
            query_params["wait_for_selector"] = str(kwargs.pop("wait_for_selector"))
        if "rendering_wait" in kwargs and kwargs["rendering_wait"]:
            query_params["rendering_wait"] = int(kwargs.pop("rendering_wait"))

        # Javascript scenario (base64 JSON array)
        if "js_scenario" in kwargs and kwargs["js_scenario"]:
            js_scenario = kwargs.pop("js_scenario")
            if isinstance(js_scenario, (dict, list)):
                query_params["js_scenario"] = self._b64_json(js_scenario)  # type: ignore[arg-type]
            else:
                query_params["js_scenario"] = str(js_scenario)

        # Debug (captures extra diagnostics; with render_js it can capture screenshots)
        if debug:
            query_params["debug"] = "true"

        # Session sticky proxy setting (docs: sessions)
        if "session_sticky_proxy" in kwargs:
            query_params["session_sticky_proxy"] = str(bool(kwargs.pop("session_sticky_proxy"))).lower()

        # Extra Scrapfly params passthrough (timeout, cache, etc.)
        # NOTE: these must already be valid Scrapfly params.
        for k, v in list(kwargs.items()):
            if v is None:
                continue
            query_params[k] = v

        # Custom headers (Scrapfly expects headers[Name]=Value)
        if headers:
            query_params.update(self._flatten_headers(headers))

        # Optional body (for POST requests) — rarely used here
        body = kwargs.pop("body", None)
        content_type = kwargs.pop("content_type", None)
        request_headers: Dict[str, str] = {}
        if content_type:
            request_headers["Content-Type"] = str(content_type)

        try:
            resp = self.session.request(
                method,
                self.api_url,
                params=query_params,
                data=body,
                headers=request_headers or None,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()

            data = resp.json()
            result = data.get("result", {}) or {}

            # Store session id for reuse
            if isinstance(result, dict) and result.get("session") and not self.session_id:
                self.session_id = result.get("session")

            # Throttle requests slightly
            time.sleep(DELAY_BETWEEN_REQUESTS)

            return {
                "success": True,
                "url": url,
                "final_url": result.get("url", url),
                "html": result.get("content", ""),
                "status_code": result.get("status_code", 200),
                "cookies": result.get("cookies", {}) or {},
                "browser_data": result.get("browser_data", {}) or {},
                "response": data,  # full JSON (useful for debugging)
                "session_id": self.session_id,
            }

        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, "status_code", 0) or 0
            # Scrapfly itself might return 429 when credit/rate limited.
            if status == 429:
                retry_after = 60
                if e.response is not None:
                    ra = e.response.headers.get("Retry-After")
                    if ra:
                        try:
                            retry_after = int(ra)
                        except ValueError:
                            retry_after = 60
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

    def scrape_with_headers(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> Dict[str, Any]:
        """Scrape with custom headers (forwarded to Scrapfly properly)."""
        return self.scrape(url, headers=headers, **kwargs)

    def get_cookies(self, url: str) -> Dict[str, str]:
        """Fetch cookies from a scrape result."""
        result = self.scrape(url)
        if result.get("success"):
            return result.get("cookies", {}) or {}
        return {}

    def close(self) -> None:
        self.session.close()
