"""
Scrapfly API Client for Web Scraping
"""
import logging
import random
import threading
import os
import requests
import time
import json
from typing import Dict, Optional, Any
from config import SCRAPFLY_CONFIG, REQUEST_TIMEOUT, DELAY_BETWEEN_REQUESTS


class ScrapflyClient:
    """Client for interacting with Scrapfly API"""
    
    def __init__(self, api_key: str = None, session_id: str = None):
        self.api_key = api_key or SCRAPFLY_CONFIG["api_key"]
        self.api_url = SCRAPFLY_CONFIG["url"]
        self.session_id = session_id  # Scrapfly session ID for maintaining cookies
        self._local = threading.local()
        self.logger = logging.getLogger("scrapfly")
    
    def _get_session(self) -> requests.Session:
        """Requests Session is not guaranteed thread-safe; keep one per thread."""
        sess = getattr(self._local, "session", None)
        if sess is None:
            sess = requests.Session()
            sess.headers.update({"X-API-KEY": self.api_key})
            self._local.session = sess
        return sess

    def _log(self, event: str, **fields: Any) -> None:
        # single-line key=value logs play well with Railway log aggregation
        parts = [f"event={event}"]
        for k, v in fields.items():
            if v is None:
                continue
            parts.append(f"{k}={json.dumps(v, ensure_ascii=True)}")
        self.logger.info(" ".join(parts))

    def _is_blocked_or_challenged(self, status_code: int, html: str, expected_contains: Optional[Any] = None) -> bool:
        """
        Heuristics only. For 200 responses, prefer letting the caller's parser decide (e.g. 0 listings)
        unless the content is clearly wrong/empty.
        """
        if status_code in (403, 429):
            return True
        if not html:
            return True
        lowered = html.lower()

        # If caller provided "expected" substrings, treat missing expectations as suspicious.
        if expected_contains:
            if isinstance(expected_contains, (str, bytes)):
                expected_list = [expected_contains]
            else:
                expected_list = list(expected_contains)
            if expected_list and not any(str(x).lower() in lowered for x in expected_list if x):
                return True

        markers = [
            "captcha",
            "verify you are human",
            "unusual traffic",
            "pardon our interruption",
            "cloudflare",
        ]
        return any(m in lowered for m in markers)

    def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Scrape a URL using Scrapfly API
        
        Args:
            url: URL to scrape
            **kwargs: Additional Scrapfly parameters
        
        Returns:
            Dictionary containing response data
        """
        custom_headers = kwargs.pop("headers", None)
        context = kwargs.pop("context", None) or {}
        timeout_s = int(kwargs.pop("timeout", REQUEST_TIMEOUT))
        max_tries = int(kwargs.pop("max_tries", os.environ.get("SCRAPFLY_MAX_TRIES", "4")))
        expect_content = bool(kwargs.pop("expect_content", True))
        expected_contains = kwargs.pop("expected_contains", None)

        # Allow explicit override; otherwise use "auto" fast->hard->hard+js
        policy = kwargs.pop("policy", "auto")

        # Country detection (Gumtree AU)
        country = kwargs.get("country", SCRAPFLY_CONFIG.get("country", "AU"))
        if "gumtree.com.au" in url:
            country = "AU"

        fast_params = {
            "render_js": False,
            "asp": False,
            "premium_proxy": False,
        }
        hard_params = {
            "render_js": False,
            "asp": True,
            "premium_proxy": True,
        }
        hard_js_params = {
            "render_js": True,
            "asp": True,
            "premium_proxy": True,
        }

        if policy == "fast":
            param_steps = [fast_params]
        elif policy == "hard":
            param_steps = [hard_params, hard_js_params]
        else:
            param_steps = [fast_params, hard_params, hard_js_params]

        # retry/backoff for transient failures
        backoffs = [5, 10, 20]  # seconds
        max_retry_sleep_s = int(os.environ.get("SCRAPFLY_MAX_RETRY_SLEEP_S", "120"))
        attempt = 0
        step_idx = 0

        last_error = None
        while attempt < max_tries:
            attempt += 1
            step = param_steps[min(step_idx, len(param_steps) - 1)].copy()
            # explicit overrides win
            step["render_js"] = bool(kwargs.get("render_js", step["render_js"]))
            step["asp"] = bool(kwargs.get("asp", step["asp"]))
            step["premium_proxy"] = bool(kwargs.get("premium_proxy", step["premium_proxy"]))

            # Build query parameters
            query_params = {
                "key": self.api_key,
                "url": url,
                "render_js": "true" if step["render_js"] else "false",
                "country": country,
                "premium_proxy": "true" if step["premium_proxy"] else "false",
                "asp": "true" if step["asp"] else "false",
            }
            if self.session_id:
                query_params["session"] = self.session_id
            if custom_headers:
                for header_name, header_value in custom_headers.items():
                    query_params[f"headers[{header_name}]"] = str(header_value)

            started = time.perf_counter()
            try:
                self._log(
                    "scrapfly_request_start",
                    url=url,
                    attempt=attempt,
                    step=step_idx,
                    timeout_s=timeout_s,
                    render_js=step["render_js"],
                    asp=step["asp"],
                    premium_proxy=step["premium_proxy"],
                    country=country,
                    **context,
                )
                resp = self._get_session().get(self.api_url, params=query_params, timeout=timeout_s)
                api_http_status = resp.status_code
                api_retry_after = resp.headers.get("Retry-After")
                raw_text = resp.text
                try:
                    data = resp.json()
                except Exception:
                    data = {}

                # If Scrapfly API itself errors (4xx/5xx), surface it clearly.
                # Note: Target HTTP status is typically in result.status_code; api_http_status reflects Scrapfly API health.
                if api_http_status >= 400:
                    # Best-effort message extraction
                    msg = None
                    try:
                        if isinstance(data, dict):
                            err = data.get("error") or data.get("errors")
                            if isinstance(err, dict):
                                msg = err.get("message") or err.get("code") or json.dumps(err, ensure_ascii=True)
                            elif isinstance(err, list) and err:
                                msg = json.dumps(err[:1], ensure_ascii=True)
                            elif err:
                                msg = str(err)
                            if not msg:
                                msg = data.get("message") or data.get("detail")
                    except Exception:
                        msg = None
                    if not msg and raw_text:
                        msg = raw_text.strip()[:500]

                    self._log(
                        "scrapfly_api_http_error",
                        url=url,
                        attempt=attempt,
                        step=step_idx,
                        api_http_status=api_http_status,
                        api_retry_after=api_retry_after,
                        message=(msg[:300] if isinstance(msg, str) else msg),
                        **context,
                    )

                    # Retry only for rate limit (429) and 5xx. Fail fast for other 4xx (e.g. 401/402/422).
                    if api_http_status == 429:
                        reason = "rate_limited"
                        last_error = f"rate_limited api_http_status=429"
                    elif api_http_status >= 500:
                        reason = "http_error"
                        last_error = f"scrapfly_api_5xx api_http_status={api_http_status}"
                    else:
                        return {
                            "success": False,
                            "url": url,
                            "error": f"scrapfly_api_error api_http_status={api_http_status}" + (f" message={msg}" if msg else ""),
                            "html": "",
                            "status_code": api_http_status,
                            "attempts": attempt,
                            "policy_step": step_idx,
                            "params_used": {"country": country, **step},
                        }
                result_data = data.get("result") if isinstance(data, dict) else {}
                if not isinstance(result_data, dict):
                    result_data = {}
                html = result_data.get("content", "") or ""
                status_code = int(result_data.get("status_code") or api_http_status or 0)

                if "session" in result_data and not self.session_id:
                    self.session_id = result_data["session"]

                elapsed_ms = int((time.perf_counter() - started) * 1000)
                blocked = self._is_blocked_or_challenged(status_code, html, expected_contains=expected_contains) if expect_content else False

                self._log(
                    "scrapfly_request_end",
                    url=url,
                    attempt=attempt,
                    step=step_idx,
                    elapsed_ms=elapsed_ms,
                    api_http_status=api_http_status,
                    status_code=status_code,
                    blocked=blocked,
                    html_len=len(html),
                    api_retry_after=api_retry_after,
                    **context,
                )

                # Success path:
                # - For 200 responses, return content even if heuristics are "suspicious" and let parsing decide.
                # - For obvious target errors (403/429) keep failing to enable retries/backoff.
                if api_http_status < 500 and status_code not in (403, 429) and html:
                    time.sleep(DELAY_BETWEEN_REQUESTS)
                    return {
                        "success": True,
                        "url": url,
                        "html": html,
                        "status_code": status_code or 200,
                        "response": data,
                        "session_id": self.session_id,
                        "attempts": attempt,
                        "policy_step": step_idx,
                        "params_used": {"country": country, **step},
                        "elapsed_ms": elapsed_ms,
                        "blocked_suspected": blocked,
                    }

                # Quota exhausted is usually hard-fail (don't spin)
                if status_code == 403 and not blocked:
                    return {
                        "success": False,
                        "url": url,
                        "error": "403 Forbidden - target denied or Scrapfly quota/credits may be exhausted.",
                        "html": html,
                        "status_code": 403,
                        "attempts": attempt,
                        "policy_step": step_idx,
                        "params_used": {"country": country, **step},
                        "elapsed_ms": elapsed_ms,
                    }

                # Decide retry/fallback (only for clear transient/denial cases)
                reason = "blocked" if status_code == 403 else ("rate_limited" if status_code == 429 or api_http_status == 429 else "http_error")
                last_error = f"{reason} status_code={status_code} api_http_status={api_http_status}"

            except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout) as e:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                reason = "timeout"
                last_error = f"{reason}: {str(e)}"
                self._log(
                    "scrapfly_request_error",
                    url=url,
                    attempt=attempt,
                    step=step_idx,
                    reason=reason,
                    elapsed_ms=elapsed_ms,
                    **context,
                )
            except requests.exceptions.RequestException as e:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                reason = "request_error"
                last_error = f"{reason}: {str(e)}"
                self._log(
                    "scrapfly_request_error",
                    url=url,
                    attempt=attempt,
                    step=step_idx,
                    reason=reason,
                    elapsed_ms=elapsed_ms,
                    **context,
                )

            # Retry / backoff / escalate policy
            if reason == "blocked":
                step_idx = min(step_idx + 1, len(param_steps) - 1)
            # For rate limiting, don't waste time escalating params; just wait and retry.

            # Backoff (cap by list length)
            sleep_s = backoffs[min(attempt - 1, len(backoffs) - 1)]
            # small jitter to avoid thundering herd
            sleep_s = sleep_s + random.uniform(0, 0.5)

            # Honor Retry-After if provided/known (Scrapfly API or result)
            retry_after_s = None
            try:
                # Some APIs return "Retry-After" in headers; also handle numeric strings
                if 'api_retry_after' in locals() and api_retry_after:
                    retry_after_s = int(float(str(api_retry_after).strip()))
            except Exception:
                retry_after_s = None
            try:
                # Some Scrapfly responses may include retry hints in JSON
                if isinstance(data, dict):
                    ra = data.get("retry_after") or (data.get("result") or {}).get("retry_after")
                    if ra is not None:
                        retry_after_s = int(float(str(ra).strip()))
            except Exception:
                pass

            if reason == "rate_limited" and retry_after_s:
                sleep_s = max(sleep_s, retry_after_s)

            sleep_s = min(float(sleep_s), float(max_retry_sleep_s))
            self._log(
                "scrapfly_retry_sleep",
                url=url,
                attempt=attempt,
                step=step_idx,
                reason=reason,
                sleep_s=round(sleep_s, 2),
                retry_after_s=retry_after_s,
                **context,
            )
            time.sleep(sleep_s)

        return {
            "success": False,
            "url": url,
            "error": last_error or "Failed after retries",
            "html": "",
            "status_code": 0,
            "attempts": attempt,
            "policy_step": step_idx,
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
        sess = getattr(self._local, "session", None)
        if sess is not None:
            sess.close()
