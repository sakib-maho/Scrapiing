"""
phone_extractor.py
- Prefer reveal/phone endpoints via XHR captured by Scrapfly browser_data
- Detect Gumtree AU geo restriction message (outside Australia / VPN)
- Provide a verbose debug trail to understand what's hidden
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from scrapfly_client import ScrapflyClient


class PhoneExtractor:
    def __init__(self, client: ScrapflyClient):
        self.client = client

    def extract_phone(
        self,
        soup: BeautifulSoup,
        listing_url: str,
        job_id: str = "",
        *,
        scrape_result: Optional[Dict[str, Any]] = None,
        debug: bool = False,
    ) -> Optional[str]:
        job_id = job_id or self._job_id_from_url(listing_url)
        is_au = "gumtree.com.au" in listing_url

        # 0) GEO-BLOCK detection (very common for Gumtree AU)
        if self._looks_geo_blocked(soup):
            if debug:
                print("    ⚠ Detected Gumtree AU geo/VPN restriction message in HTML.")
            return None

        # 1) Direct tel: (rare)
        tel = self._extract_tel(soup)
        if tel:
            if debug:
                print("    ✓ Found tel: link in HTML.")
            return tel

        # 2) If we already have browser_data, inspect XHR first
        if scrape_result:
            phone = self._extract_from_browser_data(scrape_result.get("browser_data") or {}, job_id, debug=debug)
            if phone:
                return phone

        # 3) Fetch with JS rendering enabled to capture XHR
        rendered = self.client.scrape(
            listing_url,
            render_js=True,
            country="AU" if is_au else None,
            session_sticky_proxy=True,
            premium_proxy=True,
            asp=True,
            headers={
                "Referer": listing_url,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        if not rendered.get("success"):
            if debug:
                print(f"    ⚠ render_js scrape failed: {rendered.get('error')}")
            return None

        soup2 = BeautifulSoup(rendered.get("html", ""), "lxml")
        if self._looks_geo_blocked(soup2):
            if debug:
                print("    ⚠ Detected Gumtree AU geo/VPN restriction after render_js scrape.")
            return None

        tel2 = self._extract_tel(soup2)
        if tel2:
            if debug:
                print("    ✓ Found tel: link after render_js.")
            return tel2

        phone = self._extract_from_browser_data(rendered.get("browser_data") or {}, job_id, debug=debug)
        if phone:
            return phone

        # 4) If still nothing, attempt to discover and replay phone endpoints found in page scripts
        endpoints = self._discover_endpoints(soup2, listing_url, job_id)
        if debug and endpoints:
            print(f"    ℹ Discovered {len(endpoints)} possible phone/contact endpoints from HTML/scripts.")
            for e in endpoints[:10]:
                print(f"      - {e}")

        phone = self._fetch_phone_from_endpoints(endpoints, listing_url, job_id, debug=debug)
        return phone

    # --------------------------
    # GEO block detection
    # --------------------------
    def _looks_geo_blocked(self, soup: BeautifulSoup) -> bool:
        text = soup.get_text(" ", strip=True).lower()
        # Gumtree AU help text is about "outside of australia" / VPN
        triggers = [
            "outside of australia",
            "unable to accept responses",
            "disconnect and try again",
            "using a vpn",
        ]
        return any(t in text for t in triggers)

    # --------------------------
    # Direct tel:
    # --------------------------
    def _extract_tel(self, soup: BeautifulSoup) -> Optional[str]:
        a = soup.find("a", href=re.compile(r"^tel:", re.I))
        if not a:
            return None
        href = a.get("href", "")
        phone = href.split(":", 1)[-1].strip()
        return self._normalize_phone(phone)

    # --------------------------
    # XHR extraction (best signal)
    # --------------------------
    def _extract_from_browser_data(self, browser_data: Dict[str, Any], job_id: str, *, debug: bool) -> Optional[str]:
        xhr_calls = self._get_xhr_calls(browser_data)
        if debug:
            print(f"    ℹ XHR calls captured: {len(xhr_calls)}")

        # First pass: look for phone-like keys in JSON responses
        for call in xhr_calls:
            url = self._xhr_url(call)
            status = self._xhr_status(call)
            body = self._xhr_body(call)

            if debug and url:
                if any(k in (url or "").lower() for k in ["phone", "contact", "reveal", "number", "vip"]):
                    snippet = (body or "")[:160].replace("\n", " ")
                    print(f"    🔎 XHR match candidate: {status} {url} | {snippet}")

            phone = self._extract_phone_from_payload(body, job_id)
            if phone:
                if debug:
                    print(f"    ✓ Phone found in XHR response from: {url}")
                return phone

        return None

    def _get_xhr_calls(self, browser_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(browser_data, dict):
            return []
        for key in ("xhr_call", "xhr_calls"):
            v = browser_data.get(key)
            if isinstance(v, list):
                return [c for c in v if isinstance(c, dict)]
        return []

    def _xhr_url(self, call: Dict[str, Any]) -> str:
        req = call.get("request")
        if isinstance(req, dict) and req.get("url"):
            return str(req.get("url"))
        if call.get("url"):
            return str(call.get("url"))
        return ""

    def _xhr_status(self, call: Dict[str, Any]) -> str:
        resp = call.get("response")
        if isinstance(resp, dict) and resp.get("status"):
            return str(resp.get("status"))
        if isinstance(resp, dict) and resp.get("status_code"):
            return str(resp.get("status_code"))
        return ""

    def _xhr_body(self, call: Dict[str, Any]) -> str:
        resp = call.get("response")
        if isinstance(resp, dict) and resp.get("body") is not None:
            return str(resp.get("body"))
        if call.get("body") is not None:
            return str(call.get("body"))
        return ""

    def _extract_phone_from_payload(self, payload: str, job_id: str) -> Optional[str]:
        if not payload:
            return None

        # JSON parse
        try:
            data = json.loads(payload)
            phone = self._find_phone_in_json(data)
            if phone:
                phone = self._normalize_phone(phone)
                if self._is_valid_phone(phone, job_id):
                    return phone
        except Exception:
            pass

        # fallback: phone regex (still safer than description, because this is XHR responses)
        m = re.search(r"(?:\+?61\s?\d[\d\s-]{7,}|0\d[\d\s-]{7,}|\+\d[\d\s-]{7,})", payload)
        if m:
            phone = self._normalize_phone(m.group(0))
            if self._is_valid_phone(phone, job_id):
                return phone

        return None

    def _find_phone_in_json(self, obj: Any) -> Optional[str]:
        # recursively look for common phone keys
        if isinstance(obj, dict):
            for k in ("phone", "phoneNumber", "contactPhone", "number", "mobile"):
                v = obj.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            for v in obj.values():
                found = self._find_phone_in_json(v)
                if found:
                    return found
        elif isinstance(obj, list):
            for it in obj:
                found = self._find_phone_in_json(it)
                if found:
                    return found
        return None

    # --------------------------
    # Endpoint discovery & replay
    # --------------------------
    def _discover_endpoints(self, soup: BeautifulSoup, listing_url: str, job_id: str) -> List[str]:
        base = "https://www.gumtree.com.au" if "gumtree.com.au" in listing_url else "https://www.gumtree.com"
        found: List[str] = []

        # Search scripts for /api/... strings containing job_id and phone/contact keywords
        for script in soup.find_all("script"):
            txt = script.get_text(" ", strip=True)
            if not txt:
                continue
            for m in re.findall(r'["\'](\/[^"\']+)["\']', txt):
                if job_id in m and re.search(r"(api|phone|contact|reveal|number|vip)", m, re.I):
                    found.append(self._abs_url(m, base))

        # Also look for data-* endpoints
        for el in soup.find_all(attrs=True):
            for attr in ("data-endpoint", "data-url", "data-href"):
                v = el.get(attr)
                if isinstance(v, str) and job_id in v and re.search(r"(phone|contact|reveal|vip)", v, re.I):
                    found.append(self._abs_url(v, base))

        # de-dup
        out, seen = [], set()
        for x in found:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    def _fetch_phone_from_endpoints(self, endpoints: List[str], listing_url: str, job_id: str, *, debug: bool) -> Optional[str]:
        if not endpoints:
            return None

        # headers that often matter
        hdr = {
            "Referer": listing_url,
            "Origin": "https://www.gumtree.com.au" if "gumtree.com.au" in listing_url else "https://www.gumtree.com",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
        }

        for ep in endpoints:
            for method in ("GET", "POST"):
                r = self.client.scrape(
                    ep,
                    method=method,
                    render_js=False,
                    session_sticky_proxy=True,
                    premium_proxy=True,
                    asp=True,
                    country="AU" if "gumtree.com.au" in listing_url else None,
                    headers=hdr,
                )
                if not r.get("success"):
                    if debug:
                        print(f"    ⚠ Endpoint {method} failed: {ep} -> {r.get('error')}")
                    continue

                body = (r.get("html") or "").strip()
                phone = self._extract_phone_from_payload(body, job_id)
                if phone:
                    if debug:
                        print(f"    ✓ Phone found via endpoint replay: {method} {ep}")
                    return phone

                if debug:
                    snippet = body[:160].replace("\n", " ")
                    print(f"    … Endpoint no phone: {method} {ep} | {snippet}")

        return None

    # --------------------------
    # Helpers
    # --------------------------
    def _job_id_from_url(self, url: str) -> str:
        m = re.search(r"/(\d+)(?:\?|$)", url)
        return m.group(1) if m else ""

    def _abs_url(self, maybe: str, base: str) -> str:
        if maybe.startswith("http"):
            return maybe
        if maybe.startswith("/"):
            return base + maybe
        return base + "/" + maybe

    def _normalize_phone(self, raw: str) -> str:
        raw = (raw or "").strip().replace("\u00a0", " ")
        # keep leading +
        raw = re.sub(r"[^\d+]", "", raw)
        raw = re.sub(r"^\++", "+", raw)
        return raw

    def _is_valid_phone(self, phone: str, job_id: str) -> bool:
        if not phone:
            return False
        digits = re.sub(r"\D", "", phone)
        if job_id and digits.endswith(str(job_id)):
            return False
        return 8 <= len(digits) <= 15
