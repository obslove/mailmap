from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None

from mailmap.domains import domain_from_url, is_infrastructure_domain, looks_like_tracking_domain

URL_RE = re.compile(r"https?://[^\s<>'\")]+", re.IGNORECASE)

TRACKING_QUERY_KEYS = ("url", "u", "redirect", "redirect_url", "target", "dest", "destination")


class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        attributes = dict(attrs)
        href = attributes.get("href")
        if href:
            self.urls.append(href)

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text.append(data.strip())


def clean_text(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", value or "").strip()
    return html.unescape(collapsed)


def unwrap_tracking_url(url: str) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    for key in TRACKING_QUERY_KEYS:
        if key in params and params[key]:
            candidate = unquote(params[key][0])
            if candidate.startswith("http://") or candidate.startswith("https://"):
                return candidate
    return url


def extract_urls_from_text(text: str) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for raw in URL_RE.findall(text or ""):
        normalized = unwrap_tracking_url(raw.rstrip(").,;"))
        if normalized not in seen:
            seen.add(normalized)
            results.append(normalized)
    return results


def extract_from_html(html_body: str) -> tuple[str, list[str]]:
    if not html_body.strip():
        return "", []
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html_body, "html.parser")
        urls: list[str] = []
        seen: set[str] = set()
        for tag in soup.find_all(href=True):
            href = unwrap_tracking_url(tag.get("href", ""))
            if href.startswith("http://") or href.startswith("https://"):
                if href not in seen:
                    seen.add(href)
                    urls.append(href)
        text = clean_text(soup.get_text(" ", strip=True))
        return text, urls
    parser = _LinkExtractor()
    parser.feed(html_body)
    seen: set[str] = set()
    urls = []
    for raw in parser.urls:
        href = unwrap_tracking_url(raw)
        if href.startswith("http://") or href.startswith("https://"):
            if href not in seen:
                seen.add(href)
                urls.append(href)
    return clean_text(" ".join(parser.text)), urls


def meaningful_link_domains(urls: list[str]) -> list[str]:
    domains: list[str] = []
    seen: set[str] = set()
    for url in urls:
        domain = domain_from_url(url)
        if not domain:
            continue
        if is_infrastructure_domain(domain):
            continue
        if looks_like_tracking_domain(domain):
            continue
        if domain not in seen:
            seen.add(domain)
            domains.append(domain)
    return domains
