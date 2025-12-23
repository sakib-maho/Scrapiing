"""
Phone extractor for Gumtree listings.

Goals:
- Extract phone if it is publicly present (HTML, embedded JSON, or guest-accessible API responses).
- Re-use Scrapfly's rendered/network/debug payloads when available (XHR/Network capture).
- Try known/public Gumtree AU API endpoints without attempting to bypass authentication.
- Validate/normalize Australian phone numbers to avoid false positives (e.g. "06224313").

NOTE:
If Gumtree requires authentication to reveal a phone number for a given ad, a guest scraper
may legitimately receive no phone (or 401/403 responses). In that case this returns None.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from bs4 import BeautifulSoup

JsonLike = Union[Dict[str, Any], List[Any]]


class PhoneExtractor:
    def __init__(self, client: Any):
        """
        client: expected to be an instance of ScrapflyClient (or compatible),
                providing a .scrape(url, **kwargs) method returning dict:
                {"success": bool, "html": str, "response": dict, "browser_data": dict, ...}
        """
        self.client = client

        # AU phone patterns we accept (after normalization):
        # - Mobile: 04XXXXXXXX (10 digits)
        # - Landline: 0[2378]XXXXXXXX (10 digits)
        # - Intl: +61[2|3|4|7|8]XXXXXXXX
        # - 13/1300/1800 numbers
        self._re_candidate = re.compile(
            r"""
            (?:
                \+?61[\s\-]?\(?0?\)?[\s\-]?\d[\d\s\-]{6,14}     # +61 ...
                |
                0[2378][\s\-]?\d{4}[\s\-]?\d{4}                # 02/03/07/08 xxxx xxxx
                |
                04[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{3}         # 04xx xxx xxx
                |
                13[\s\-]?\d{2}[\s\-]?\d{2}                     # 13 xx xx
                |
                1300[\s\-]?\d{3}[\s\-]?\d{3}                   # 1300 xxx xxx
                |
                1800[\s\-]?\d{3}[\s\-]?\d{3}                   # 1800 xxx xxx
            )
            """,
            re.VERBOSE,
        )

        # Token-ish things we might see (NOT a phone):
        self._re_token_key = re.compile(r"(?:bbtoken|token|csrf|auth|session)", re.IGNORECASE)

        # Things we should not treat as phone numbers (base64 blobs, short bare numbers etc.)
        self._re_blacklist = re.compile(
            r"(?:\b\d{7,}\b.*\b(base64|jpeg|png)\b)|(?:^\d{7,8}$)", re.IGNORECASE
        )

    # ---------------------------
    # Public entry point
    # ---------------------------
    def extract_phone(
        self,
        soup: BeautifulSoup,
        listing_url: str,
        job_id: str = "",
        scrape_result: Optional[Dict[str, Any]] = None,
        debug: bool = False,
    ) -> Optional[str]:
        # 0) tel: links
        phone = self._from_tel_links(soup, debug=debug)
        if phone:
            return phone

        # 1) focused DOM
        phone = self._from_specific_dom_areas(soup, debug=debug)
        if phone:
            return phone

        # 2) embedded state/scripts/meta
        phone = self._from_embedded_state(soup, debug=debug)
        if phone:
            return phone

        # 3) Scrapfly payload mining (response + browser_data)
        token_hint = None
        if scrape_result:
            phone, token_hint = self._from_scrapfly_payload(scrape_result, debug=debug)
            if phone:
                return phone

        # 4) Public AU endpoints (optionally token-assisted)
        if self._is_gumtree_au(listing_url) and job_id:
            phone = self._try_public_au_endpoints(
                ad_id=job_id,
                soup=soup,
                scrape_result=scrape_result,
                bb_token=token_hint,
                debug=debug,
            )
            if phone:
                return phone

        # 5) broad scan as last resort
        phone = self._from_broad_text_scan(soup, debug=debug)
        if phone:
            return phone

        return None

    # ---------------------------
    # Extraction: tel links
    # ---------------------------
    def _from_tel_links(self, soup: BeautifulSoup, debug: bool = False) -> Optional[str]:
        for a in soup.select('a[href^="tel:"]'):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            raw = href.replace("tel:", "").strip()
            phone = self._normalize_au_phone(raw)
            if phone:
                if debug:
                    print(f"    ✓ Phone found in tel: link: {phone}")
                return phone
        return None

    # ---------------------------
    # Extraction: targeted DOM
    # ---------------------------
    def _from_specific_dom_areas(self, soup: BeautifulSoup, debug: bool = False) -> Optional[str]:
        selectors = [
            "[data-testid='reveal-number']",
            "[data-testid='pageSideColumn']",
            "[data-testid='seller-profile']",
            "[data-testid='click-show-number']",
            ".vip-contact, .contact, .seller, .seller-card",
        ]
        for sel in selectors:
            for node in soup.select(sel):
                txt = self._compact_text(node.get_text(" ", strip=True))
                phone = self._first_valid_phone_in_text(txt)
                if phone:
                    if debug:
                        print(f"    ✓ Phone found in DOM area {sel}: {phone}")
                    return phone
        return None

    # ---------------------------
    # Extraction: embedded state
    # ---------------------------
    def _from_embedded_state(self, soup: BeautifulSoup, debug: bool = False) -> Optional[str]:
        # meta tags
        for meta in soup.find_all("meta"):
            content = meta.get("content")
            if content:
                phone = self._first_valid_phone_in_text(content)
                if phone:
                    if debug:
                        print("    ✓ Phone found in meta content")
                    return phone

        # JSON-LD
        for script in soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)}):
            raw = (script.string or script.get_text() or "").strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue
            phone = self._find_phone_in_json(data, debug=debug)
            if phone:
                if debug:
                    print("    ✓ Phone found in JSON-LD")
                return phone

        # other scripts (state blobs)
        for script in soup.find_all("script"):
            raw = (script.string or script.get_text() or "").strip()
            if not raw or len(raw) < 30:
                continue

            if any(k in raw for k in ("__NEXT_DATA__", "__APOLLO_STATE__", "window.__", "adId", "categoryId")):
                json_obj = self._extract_json_object_from_js(raw)
                if json_obj is not None:
                    phone = self._find_phone_in_json(json_obj, debug=debug)
                    if phone:
                        if debug:
                            print("    ✓ Phone found in embedded script JSON/state")
                        return phone

                phone = self._first_valid_phone_in_text(raw)
                if phone:
                    if debug:
                        print("    ✓ Phone found by scanning script text")
                    return phone

        return None

    # ---------------------------
    # Extraction: Scrapfly mining
    # returns (phone, bbToken_or_None)
    # ---------------------------
    def _from_scrapfly_payload(
        self, scrape_result: Dict[str, Any], debug: bool = False
    ) -> Tuple[Optional[str], Optional[str]]:
        bb_token = None

        # Prefer explicit browser_data if your ScrapflyClient exposes it
        browser_data = scrape_result.get("browser_data")
        if isinstance(browser_data, dict):
            # 1) try to find phone in browser_data JSON
            phone = self._find_phone_in_json(browser_data, debug=debug)
            if phone:
                if debug:
                    print("    ✓ Phone found in Scrapfly browser_data")
                return phone, None

            # 2) try to find bbToken in browser_data
            bb_token = self._find_token_in_json(browser_data)
            if bb_token and debug:
                print(f"    ℹ Found token-like value in browser_data (bbToken?): {bb_token[:10]}...")

            # 3) mine network calls inside browser_data
            calls = self._collect_network_calls(browser_data)
            if debug:
                print(f"    ℹ XHR calls captured: {len(calls)}")
            phone = self._scan_calls_for_phone(calls, debug=debug)
            if phone:
                return phone, bb_token

            # also scan calls for token if not already
            if not bb_token:
                bb_token = self._scan_calls_for_token(calls)
                if bb_token and debug:
                    print(f"    ℹ Found token-like value in XHR calls (bbToken?): {bb_token[:10]}...")

        # Fallback: full response JSON
        response = scrape_result.get("response")
        if isinstance(response, dict):
            phone = self._find_phone_in_json(response, debug=debug)
            if phone:
                if debug:
                    print("    ✓ Phone found in Scrapfly response JSON")
                return phone, bb_token

            if not bb_token:
                bb_token = self._find_token_in_json(response)
                if bb_token and debug:
                    print(f"    ℹ Found token-like value in response JSON (bbToken?): {bb_token[:10]}...")

            calls = self._collect_network_calls(response)
            if debug:
                print(f"    ℹ Network/XHR-like calls discovered: {len(calls)}")
            phone = self._scan_calls_for_phone(calls, debug=debug)
            if phone:
                return phone, bb_token

            if not bb_token:
                bb_token = self._scan_calls_for_token(calls)
                if bb_token and debug:
                    print(f"    ℹ Found token-like value in response calls (bbToken?): {bb_token[:10]}...")

        return None, bb_token

    def _scan_calls_for_phone(
        self, calls: List[Tuple[Optional[int], str, Any]], debug: bool = False
    ) -> Optional[str]:
        for status, url, body in calls:
            if body is None:
                continue

            parsed: Optional[JsonLike] = None

            if isinstance(body, (dict, list)):
                parsed = body
            else:
                body_str = str(body)
                # scan text first (fast)
                phone = self._first_valid_phone_in_text(body_str)
                if phone:
                    if debug:
                        print(f"    ✓ Phone found in XHR response from: {url}")
                    return phone
                # then try json load
                parsed = self._safe_json_loads(body_str)

            if parsed is not None:
                phone = self._find_phone_in_json(parsed, debug=debug)
                if phone:
                    if debug:
                        print(f"    ✓ Phone found in XHR JSON from: {url}")
                    return phone

                # If there is a "phone" key but it's NOT valid (e.g. short id), log it
                raw_phone = self._find_raw_phone_like_value(parsed)
                if raw_phone and debug:
                    print(f"    … Found phone-like field but rejected by AU validation: {raw_phone} (from {url})")

        return None

    def _scan_calls_for_token(self, calls: List[Tuple[Optional[int], str, Any]]) -> Optional[str]:
        for _, _, body in calls:
            if body is None:
                continue
            if isinstance(body, (dict, list)):
                tok = self._find_token_in_json(body)
                if tok:
                    return tok
            else:
                s = str(body)
                # common bbToken pattern in JSON strings
                m = re.search(r'"bbToken"\s*:\s*"([^"]+)"', s)
                if m:
                    return m.group(1)
        return None

    # ---------------------------
    # Extraction: AU endpoints
    # ---------------------------
    def _try_public_au_endpoints(
        self,
        ad_id: str,
        soup: BeautifulSoup,
        scrape_result: Optional[Dict[str, Any]],
        bb_token: Optional[str],
        debug: bool = False,
    ) -> Optional[str]:
        category_id = self._extract_category_id(soup) or self._extract_category_id_from_scrapfly(scrape_result)
        random_user_id = int(time.time() * 1000)

        # Always try endpoints commonly hit by the SPA (guest-access varies)
        endpoints: List[Tuple[str, Optional[Dict[str, str]]]] = []
        endpoints.append((f"https://gt-api.gumtree.com.au/web/vip/extended-data/{ad_id}?similarListingsSize=6", None))

        if category_id:
            endpoints.append(
                (
                    "https://gt-api.gumtree.com.au/web/vip/contact-poster-info"
                    f"?adId={ad_id}&categoryId={category_id}&randomUserId={random_user_id}",
                    None,
                )
            )

        # ext-metadata often contains bbToken
        endpoints.append((f"https://gt-api.gumtree.com.au/web/ws/vip/ext-metadata.json?adId={ad_id}", None))

        # If we have a token, try a few likely reveal endpoints using headers and/or query param.
        # These are "best-guess" based on common SPA patterns; if they 404/401, we just ignore.
        if bb_token:
            token_headers = {
                "x-bb-token": bb_token,
                "x-bbtoken": bb_token,
                "bbtoken": bb_token,
                "x-bot-token": bb_token,
            }
            candidates = [
                f"https://gt-api.gumtree.com.au/web/vip/phone?adId={ad_id}",
                f"https://gt-api.gumtree.com.au/web/vip/phone-number?adId={ad_id}",
                f"https://gt-api.gumtree.com.au/web/vip/reveal-number?adId={ad_id}",
                f"https://gt-api.gumtree.com.au/web/vip/reveal-phone?adId={ad_id}",
                f"https://gt-api.gumtree.com.au/web/vip/show-number?adId={ad_id}",
                # token as query param (some systems do this)
                f"https://gt-api.gumtree.com.au/web/vip/phone?adId={ad_id}&bbToken={bb_token}",
                f"https://gt-api.gumtree.com.au/web/vip/reveal-phone?adId={ad_id}&bbToken={bb_token}",
            ]
            for u in candidates:
                endpoints.append((u, token_headers))

        # Also try any gt-api URLs present in the page (public-only checks)
        for u in self._discover_gt_api_urls_from_html(soup):
            endpoints.append((u, None))

        # De-dupe preserve order
        seen = set()
        deduped: List[Tuple[str, Optional[Dict[str, str]]]] = []
        for u, h in endpoints:
            key = (u, json.dumps(h, sort_keys=True) if h else "")
            if key in seen:
                continue
            seen.add(key)
            deduped.append((u, h))

        for api_url, hdrs in deduped:
            try:
                res = self.client.scrape(api_url, render_js=False, headers=hdrs)
            except Exception:
                continue
            if not isinstance(res, dict) or not res.get("success"):
                continue

            payload = res.get("response")
            if isinstance(payload, dict):
                phone = self._find_phone_in_json(payload, debug=debug)
                if phone:
                    if debug:
                        print(f"    ✓ Phone found via AU endpoint JSON: {api_url}")
                    return phone

                # Update token hint if we find it later
                if not bb_token:
                    bb_token = self._find_token_in_json(payload)

            html = res.get("html") or ""
            if html:
                phone = self._first_valid_phone_in_text(html)
                if phone:
                    if debug:
                        print(f"    ✓ Phone found via AU endpoint text scan: {api_url}")
                    return phone

        return None

    def _discover_gt_api_urls_from_html(self, soup: BeautifulSoup) -> List[str]:
        html = self._strip_base64(str(soup))
        urls = set(re.findall(r"https://gt-api\.gumtree\.com\.au/[^\s\"'<>]+", html))
        filtered = []
        for u in urls:
            if any(bad in u for bad in ("google", "doubleclick", "analytics")):
                continue
            filtered.append(u)
        return sorted(filtered)

    # ---------------------------
    # Broad scan
    # ---------------------------
    def _from_broad_text_scan(self, soup: BeautifulSoup, debug: bool = False) -> Optional[str]:
        html = self._strip_base64(str(soup))
        phone = self._first_valid_phone_in_text(html)
        if phone and debug:
            print("    ✓ Phone found by broad HTML scan")
        return phone

    # ---------------------------
    # Helpers: calls collection
    # ---------------------------
    def _collect_network_calls(self, obj: Any) -> List[Tuple[Optional[int], str, Any]]:
        calls: List[Tuple[Optional[int], str, Any]] = []

        def visit(x: Any):
            if isinstance(x, dict):
                url = x.get("url") or x.get("request_url") or x.get("requestUrl")
                status = x.get("status") or x.get("status_code") or x.get("statusCode")
                body = (
                    x.get("body")
                    or x.get("response")
                    or x.get("response_body")
                    or x.get("content")
                    or x.get("data")
                    or x.get("payload")
                )
                if isinstance(url, str) and url.startswith("http"):
                    calls.append((self._as_int(status), url, body))
                for v in x.values():
                    visit(v)
            elif isinstance(x, list):
                for v in x:
                    visit(v)

        visit(obj)

        # De-dup
        seen = set()
        uniq: List[Tuple[Optional[int], str, Any]] = []
        for st, u, b in calls:
            key = (u, (str(b)[:160] if b is not None else ""))
            if key in seen:
                continue
            seen.add(key)
            uniq.append((st, u, b))
        return uniq

    # ---------------------------
    # Helpers: JSON parsing
    # ---------------------------
    def _safe_json_loads(self, s: str) -> Optional[JsonLike]:
        s = s.strip()
        if not s:
            return None
        if not ((s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]"))):
            return None
        try:
            return json.loads(s)
        except Exception:
            return None

    def _extract_json_object_from_js(self, js: str) -> Optional[JsonLike]:
        m = re.search(r"=\s*({.*?})\s*;?\s*$", js, re.DOTALL)
        if not m:
            m = re.search(r"(__NEXT_DATA__|__APOLLO_STATE__)\s*=\s*({.*?})\s*;?", js, re.DOTALL)
        if not m:
            return None
        blob = m.group(m.lastindex) if m.lastindex else m.group(1)
        blob = blob.strip()
        try:
            return json.loads(blob)
        except Exception:
            return None

    # ---------------------------
    # Helpers: JSON scanning
    # ---------------------------
    def _find_phone_in_json(self, obj: Any, debug: bool = False) -> Optional[str]:
        priority_keys = (
            "phone",
            "phoneNumber",
            "phone_number",
            "mobile",
            "mobileNumber",
            "contactNumber",
            "contact_number",
            "tel",
            "telephone",
            "msisdn",
        )

        if isinstance(obj, dict):
            for k in priority_keys:
                if k in obj:
                    phone = self._coerce_and_validate_phone(obj.get(k))
                    if phone:
                        return phone
            for v in obj.values():
                phone = self._find_phone_in_json(v, debug=debug)
                if phone:
                    return phone

        elif isinstance(obj, list):
            for v in obj:
                phone = self._find_phone_in_json(v, debug=debug)
                if phone:
                    return phone

        elif isinstance(obj, str):
            return self._first_valid_phone_in_text(obj)

        return None

    def _find_raw_phone_like_value(self, obj: Any) -> Optional[str]:
        """
        If the API returns something in a phone field that fails strict AU validation
        (e.g. short IDs), return it so debug logs can show what it was.
        """
        if isinstance(obj, dict):
            for k in ("phone", "phoneNumber", "phone_number", "contactNumber", "mobile"):
                if k in obj and obj[k] is not None:
                    v = obj[k]
                    if isinstance(v, (int, float)):
                        return str(int(v))
                    return str(v)
            for v in obj.values():
                r = self._find_raw_phone_like_value(v)
                if r:
                    return r
        elif isinstance(obj, list):
            for v in obj:
                r = self._find_raw_phone_like_value(v)
                if r:
                    return r
        return None

    def _find_token_in_json(self, obj: Any) -> Optional[str]:
        """
        Look for bbToken/token-like strings inside JSON (for logging / token-assisted endpoints).
        """
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(k, str) and self._re_token_key.search(k):
                    if isinstance(v, str) and 16 <= len(v) <= 512:
                        # prefer bbToken specifically if present
                        if k.lower() == "bbtoken":
                            return v
                        # otherwise keep scanning, but we can return a first decent one
                        return v
                tok = self._find_token_in_json(v)
                if tok:
                    return tok
        elif isinstance(obj, list):
            for v in obj:
                tok = self._find_token_in_json(v)
                if tok:
                    return tok
        return None

    # ---------------------------
    # Helpers: AU phone validation
    # ---------------------------
    def _first_valid_phone_in_text(self, text: str) -> Optional[str]:
        if not text:
            return None
        text = self._strip_base64(text)
        if len(text) > 2_000_000:
            text = text[:2_000_000]

        for m in self._re_candidate.finditer(text):
            cand = m.group(0)
            phone = self._normalize_au_phone(cand)
            if phone:
                return phone
        return None

    def _coerce_and_validate_phone(self, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            v = str(int(v))
        elif not isinstance(v, str):
            v = str(v)
        return self._normalize_au_phone(v)

    def _normalize_au_phone(self, raw: str) -> Optional[str]:
        if not raw:
            return None

        s = raw.strip()

        # throw away obvious junk
        if len(s) > 200:
            return None
        if self._re_blacklist.search(s):
            return None

        # Remove common noise
        s = re.sub(r"[\(\)\[\]\{\}]", " ", s)
        s = re.sub(r"[^\d\+]", " ", s)  # keep digits and +
        s = re.sub(r"\s+", " ", s).strip()

        # +61 formats
        if s.startswith("+"):
            s2 = s.replace(" ", "").replace("(0)", "")
            if not s2.startswith("+61"):
                return None
            digits = re.sub(r"[^\d]", "", s2)  # drop +
            if not digits.startswith("61"):
                return None
            rest = digits[2:]
            if len(rest) == 9 and rest[0] in "23478":
                return f"+61{rest}"
            if len(rest) == 10 and rest.startswith("0") and rest[1] in "23478":
                return f"+61{rest[1:]}"
            return None

        digits = re.sub(r"[^\d]", "", s)
        if not digits:
            return None

        # 13/1300/1800
        if digits.startswith("13") and len(digits) == 6:
            return digits
        if digits.startswith("1300") and len(digits) == 10:
            return digits
        if digits.startswith("1800") and len(digits) == 10:
            return digits

        # Mobile
        if digits.startswith("04") and len(digits) == 10:
            return digits

        # Landline
        if len(digits) == 10 and digits[0] == "0" and digits[1] in "2378":
            return digits

        # Be conservative: do not accept 7/8 digit bare numbers (often IDs)
        return None

    # ---------------------------
    # Helpers: category id
    # ---------------------------
    def _extract_category_id(self, soup: BeautifulSoup) -> Optional[str]:
        html = self._strip_base64(str(soup))
        for pat in (
            r"categoryId[\"']?\s*:\s*(\d+)",
            r"categoryId=(\d+)",
            r"\"categoryId\"\s*:\s*(\d+)",
        ):
            m = re.search(pat, html)
            if m:
                return m.group(1)
        return None

    def _extract_category_id_from_scrapfly(self, scrape_result: Optional[Dict[str, Any]]) -> Optional[str]:
        if not scrape_result or not isinstance(scrape_result, dict):
            return None
        resp = scrape_result.get("response")
        if not isinstance(resp, dict):
            return None
        cat = self._find_first_int_key(resp, ("categoryId", "category_id"))
        return str(cat) if cat is not None else None

    def _find_first_int_key(self, obj: Any, keys: Tuple[str, ...]) -> Optional[int]:
        if isinstance(obj, dict):
            for k in keys:
                if k in obj:
                    try:
                        return int(obj[k])
                    except Exception:
                        pass
            for v in obj.values():
                found = self._find_first_int_key(v, keys)
                if found is not None:
                    return found
        elif isinstance(obj, list):
            for v in obj:
                found = self._find_first_int_key(v, keys)
                if found is not None:
                    return found
        return None

    # ---------------------------
    # Helpers: misc
    # ---------------------------
    def _strip_base64(self, text: str) -> str:
        return re.sub(r"data:image\/[a-zA-Z]+;base64,[A-Za-z0-9+/=]+", "", text)

    def _compact_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace("\u00a0", " ")
        return re.sub(r"\s+", " ", text).strip()

    def _as_int(self, v: Any) -> Optional[int]:
        try:
            return int(v)
        except Exception:
            return None

    def _is_gumtree_au(self, url: str) -> bool:
        return "gumtree.com.au" in (url or "").lower()
