"""
Working draft: Rate-limited Gumtree scraper adapter.

This file previously became non-functional because it removed core parsing helpers
like `_parse_listings_page()` / `_parse_listing_details()`. To keep this draft usable,
we now *reuse the proven scraper implementation* from `gumtree_scraper.py` and
only add **compliant throttling** (randomized spacing + UA rotation + capped in-flight
requests) on top.

Note: This does NOT "bypass" Scrapfly limits. It helps you stay under them.
"""

import os
import time
import json
import random
import logging
import threading
from typing import Dict, Optional, Any, Callable

from fake_useragent import UserAgent

from gumtree_scraper import GumtreeScraper as BaseGumtreeScraper


class RateLimitHandler:
    """
    A small throttler that:
    - rotates User-Agent (sent as part of request headers to Scrapfly)
    - enforces a minimum randomized gap between requests (shared across threads)
    - limits in-flight requests (so ThreadPoolExecutor can't spike concurrency)
    - retries a few times on Scrapfly 429 with exponential backoff (5/10/20/40)

    All timings are configurable via env vars:
    - SCRAPFLY_MIN_DELAY_S (default 1.5)
    - SCRAPFLY_MAX_DELAY_S (default 3.0)
    - SCRAPFLY_INFLIGHT_LIMIT (default 2)
    - SCRAPFLY_429_MAX_RETRIES (default 2)
    """

    def __init__(self):
        self.logger = logging.getLogger("rate_limit_handler")
        self.ua = UserAgent()

        self.min_delay_s = float(os.environ.get("SCRAPFLY_MIN_DELAY_S", "1.5"))
        self.max_delay_s = float(os.environ.get("SCRAPFLY_MAX_DELAY_S", "3.0"))
        self.inflight_limit = int(os.environ.get("SCRAPFLY_INFLIGHT_LIMIT", "2"))
        self.max_429_retries = int(os.environ.get("SCRAPFLY_429_MAX_RETRIES", "2"))

        self._lock = threading.Lock()
        self._next_allowed_ts = 0.0
        self._sem = threading.Semaphore(self.inflight_limit)

        # Fixed backoff ladder for repeated 429s
        self._backoffs = [5, 10, 20, 40]

    def get_headers(self, base_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = dict(base_headers or {})
        headers.setdefault("User-Agent", self.ua.random)
        return headers

    def _sleep_until_slot(self) -> float:
        """Global pacing across threads."""
        delay = random.uniform(self.min_delay_s, self.max_delay_s)
        with self._lock:
            now = time.time()
            sleep_for = max(0.0, self._next_allowed_ts - now)
            target = max(now, self._next_allowed_ts) + delay
            self._next_allowed_ts = target
        if sleep_for > 0:
            time.sleep(sleep_for)
        return sleep_for

    def call_scrapfly(
        self,
        func: Callable[..., Dict[str, Any]],
        *,
        url: str,
        headers: Dict[str, str],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Wrap a Scrapfly call (e.g., ScrapflyClient.scrape_with_headers) with pacing and 429 retry.
        """
        attempt_429 = 0
        while True:
            with self._sem:
                slept = self._sleep_until_slot()
                self.logger.info(
                    "event=throttle_before url=%s slept_s=%s inflight_limit=%s",
                    url,
                    round(slept, 2),
                    self.inflight_limit,
                )
                res = func(url, headers=headers, **kwargs)

            # If Scrapfly says 429, we wait and retry a couple of times
            error = (res.get("error") or "").lower()
            status_code = res.get("status_code")
            if res.get("success") or (status_code not in (429,) and "rate_limited" not in error):
                return res

            if attempt_429 >= self.max_429_retries:
                return res

            backoff_s = self._backoffs[min(attempt_429, len(self._backoffs) - 1)]
            attempt_429 += 1
            self.logger.warning(
                "event=throttle_429_retry url=%s attempt=%s backoff_s=%s",
                url,
                attempt_429,
                backoff_s,
            )
            time.sleep(backoff_s)


class GumtreeScraper(BaseGumtreeScraper):
    """
    Drop-in replacement for `gumtree_scraper.GumtreeScraper` that adds pacing + UA rotation
    on top of the existing Scrapfly-powered implementation.
    """

    def __init__(self):
        super().__init__()
        self._rate = RateLimitHandler()

        # Monkey-patch the Scrapfly client so all existing scraper logic benefits.
        orig = self.client.scrape_with_headers

        def wrapped(url: str, headers: Optional[Dict[str, str]] = None, **kwargs: Any):
            merged_headers = self._rate.get_headers(headers or {})
            return self._rate.call_scrapfly(orig, url=url, headers=merged_headers, **kwargs)

        self.client.scrape_with_headers = wrapped  # type: ignore[attr-defined]