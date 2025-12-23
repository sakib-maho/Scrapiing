"""phone_extractor.py

Gumtree phone extraction.

Important: Gumtree often hides phone numbers behind a "Show number"/"Call" button.
For Gumtree AU, Gumtree explicitly notes that phone numbers may not be visible when
accessing from outside Australia (e.g., overseas/VPN). Therefore, using an AU proxy
is typically required to see/reveal the number.

This extractor tries, in order:
  1) Direct tel: links or obvious phone text in HTML
  2) Rendered HTML (render_js) if the first soup was non-rendered
  3) Scrapfly browser_data.xhr_call inspection (common for "reveal" endpoints)
  4) A tiny js_scenario that clicks a likely "show/call/phone" button and then
     re-checks both rendered HTML and XHR captures.

Scrapfly docs used:
 - Javascript Rendering / XHR capture: https://scrapfly.io/docs/scrape-api/javascript-rendering
 - Javascript Scenario: https://scrapfly.io/docs/scrape-api/javascript-scenario
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from scrapfly_client import ScrapflyClient


class PhoneExtractor:
    """Extract phone numbers from Gumtree listing pages."""

    # Generic phone patterns (AU + international). We keep them permissive and
    # then normalize.
    PHONE_RE = re.compile(
        r"(?:\+\d{1,3}[\s\-]?)?(?:\(?0\)?\s?)?(?:\d[\s\-]?){8,12}"
    )

    # Slightly stricter AU pattern (common formats)
    AU_PHONE_RE = re.compile(
        r"(?:\+?61\s?[2-478]\s?\d{4}\s?\d{4}|0[2-478]\s?\d{4}\s?\d{4}|04\s?\d{2}\s?\d{3}\s?\d{3})"
    )

    def __init__(self, client: ScrapflyClient):
        self.client = client

    # -----------------------------
    # Public API
    # -----------------------------
    def extract_phone(
        self,
        soup: BeautifulSoup,
        listing_url: str,
        job_id: str = "",
        scrape_result: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Extract phone number for a listing.

        Args:
            soup: BeautifulSoup of the listing HTML already fetched.
            listing_url: listing URL
            job_id: numeric id if available
            scrape_result: optional raw result dict returned by ScrapflyClient.scrape

        Returns:
            E.164-like string (best effort) or None.
        """

        # 1) Obvious from HTML (tel: links, text blobs)
        phone = self._extract_from_html(soup, prefer_au="gumtree.com.au" in listing_url)
        if phone:
            return phone

        # 2) If we already have browser_data from the initial scrape, inspect XHR calls
        if scrape_result:
            phone = self._extract_from_browser_data(scrape_result.get("browser_data") or {}, prefer_au="gumtree.com.au" in listing_url)
            if phone:
                return phone

        # 3) Rendered HTML + XHR capture (no click)
        rendered = self.client.scrape(
            listing_url,
            render_js=True,
            debug=False,
            rendering_wait=3500,
            wait_for_selector="body",
            headers={"Referer": listing_url},
        )
        if rendered.get("success"):
            soup2 = BeautifulSoup(rendered.get("html", ""), "lxml")
            phone = self._extract_from_html(soup2, prefer_au="gumtree.com.au" in listing_url)
            if phone:
                return phone
            phone = self._extract_from_browser_data(rendered.get("browser_data") or {}, prefer_au="gumtree.com.au" in listing_url)
            if phone:
                return phone

        # 4) Try a JS scenario to click a "show/call/phone" button, then re-check
        clicked = self._scrape_with_reveal_click(listing_url)
        if clicked.get("success"):
            soup3 = BeautifulSoup(clicked.get("html", ""), "lxml")
            phone = self._extract_from_html(soup3, prefer_au="gumtree.com.au" in listing_url)
            if phone:
                return phone
            phone = self._extract_from_browser_data(clicked.get("browser_data") or {}, prefer_au="gumtree.com.au" in listing_url)
            if phone:
                return phone

        return None

    # -----------------------------
    # Internals
    # -----------------------------
    def _extract_from_html(self, soup: BeautifulSoup, prefer_au: bool) -> Optional[str]:
        """Extract phone from tel: links or visible text."""

        # tel: links are best
        tel_link = soup.find("a", href=re.compile(r"^tel:", re.I))
        if tel_link and tel_link.get("href"):
            return self._normalize_phone(tel_link["href"].replace("tel:", ""), prefer_au=prefer_au)

        # Sometimes embedded in JSON/script tags as "phone"/"telephone" etc.
        # We do a lightweight regex scan on the whole HTML text.
        html_text = soup.get_text(" ", strip=True)

        # Prefer AU-specific patterns when scraping AU domain
        if prefer_au:
            m = self.AU_PHONE_RE.search(html_text)
            if m:
                return self._normalize_phone(m.group(0), prefer_au=True)

        m2 = self.PHONE_RE.search(html_text)
        if m2:
            return self._normalize_phone(m2.group(0), prefer_au=prefer_au)

        return None

    def _extract_from_browser_data(self, browser_data: Dict[str, Any], prefer_au: bool) -> Optional[str]:
        """Search Scrapfly browser_data for phone numbers.

        With render_js enabled, Scrapfly can capture XHR calls under
        result.browser_data.xhr_call. Gumtree's "reveal" often happens via XHR.
        """
        if not browser_data:
            return None

        xhr_calls: List[Dict[str, Any]] = []
        # key name in docs: xhr_call (singular), but be defensive.
        if isinstance(browser_data.get("xhr_call"), list):
            xhr_calls = browser_data["xhr_call"]
        elif isinstance(browser_data.get("xhr_calls"), list):
            xhr_calls = browser_data["xhr_calls"]

        for call in xhr_calls:
            # Try response body first
            resp = call.get("response") or {}
            body = resp.get("body") or call.get("body") or ""
            if isinstance(body, (dict, list)):
                body_str = str(body)
            else:
                body_str = str(body)

            phone = self._extract_phone_from_text(body_str, prefer_au=prefer_au)
            if phone:
                return phone

            # Also inspect request URL (sometimes phone is embedded, rare)
            req = call.get("request") or {}
            url = req.get("url") or call.get("url") or ""
            phone = self._extract_phone_from_text(str(url), prefer_au=prefer_au)
            if phone:
                return phone

        # js_scenario execute steps can return values (we might return phone directly)
        js_info = browser_data.get("js_scenario") or {}
        steps = js_info.get("steps") if isinstance(js_info, dict) else None
        if isinstance(steps, list):
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if step.get("action") != "execute":
                    continue
                result = step.get("result")
                if result:
                    phone = self._extract_phone_from_text(str(result), prefer_au=prefer_au)
                    if phone:
                        return phone

        return None

    def _scrape_with_reveal_click(self, listing_url: str) -> Dict[str, Any]:
        """Run a tiny JS scenario that clicks a likely reveal button.

        We intentionally don't hardcode Gumtree selectors; instead we run JS that
        searches for any element with text containing common reveal phrases.
        """

        js = r"""
            const phrases = [
              'show number','show phone','show phone number','phone number',
              'call','reveal','show','contact'
            ];

            function clickFirstMatching() {
              const candidates = Array.from(document.querySelectorAll('button,a'));
              for (const el of candidates) {
                const t = (el.innerText || '').trim().toLowerCase();
                if (!t) continue;
                if (phrases.some(p => t.includes(p))) {
                  el.click();
                  return t;
                }
              }
              return null;
            }

            const clicked = clickFirstMatching();
            // Return something useful for debugging
            return {clicked_text: clicked, tel: (document.querySelector('a[href^="tel:"]')||{}).href || null};
        """.strip()

        scenario = [
            {"wait_for_selector": {"selector": "body", "timeout": 8000}},
            {"scroll": {"selector": "bottom"}},
            {"execute": {"script": js, "timeout": 3000}},
            {"wait": 2500},
        ]

        return self.client.scrape(
            listing_url,
            render_js=True,
            js_scenario=scenario,
            rendering_wait=2500,
            wait_for_selector="body",
            headers={"Referer": listing_url},
            debug=False,
        )

    def _extract_phone_from_text(self, text: str, prefer_au: bool) -> Optional[str]:
        if not text:
            return None

        if prefer_au:
            m = self.AU_PHONE_RE.search(text)
            if m:
                return self._normalize_phone(m.group(0), prefer_au=True)

        m2 = self.PHONE_RE.search(text)
        if m2:
            return self._normalize_phone(m2.group(0), prefer_au=prefer_au)
        return None

    def _normalize_phone(self, raw: str, prefer_au: bool) -> Optional[str]:
        """Normalize phone number to a safe display string.

        We keep it simple: strip non-digits except leading +.
        If AU and number looks like local '0xxxxxxxxx', convert to +61.
        """
        if not raw:
            return None
        raw = raw.strip()

        # Keep leading + if present
        lead_plus = raw.startswith("+")
        digits = re.sub(r"\D+", "", raw)

        if not digits:
            return None

        if lead_plus:
            return "+" + digits

        if prefer_au:
            # AU mobile/landline often start with 0
            if digits.startswith("0") and len(digits) in (9, 10):
                return "+61" + digits[1:]
            if digits.startswith("61"):
                return "+" + digits

        # Fallback: return digits as-is
        return digits
