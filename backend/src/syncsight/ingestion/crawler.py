"""Polite crawler for company websites, newsroom feeds and career pages (MES signals).

Safeguards (see ARCHITECTURE.md, D16):
- robots.txt is honoured per RFC 9309 (4xx: allowed; 5xx or unreachable: nothing allowed)
- at most one request per host every `HOST_DELAY` seconds, at most `MAX_PAGES` per site
- public pages only: no login, no forms, no query strings beyond the link as published
- page text is scanned in memory and dropped; only URL, title, date, labels and a short
  snippet of matching pages are returned
"""

import contextlib
import re
import time
import urllib.robotparser
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlsplit

import httpx2
from defusedxml import ElementTree

from syncsight.ingestion import http
from syncsight.ingestion.keywords import scan

ROBOTS_AGENT = "SyncSight"
HOST_DELAY = 2.0
MAX_PAGES = 25
MAX_BYTES = 2_000_000
NEWS = re.compile(
    r"news|press|presse|media|medien|aktuell|actualit|notizie|stampa|stories|insights|blog", re.I
)
CAREER = re.compile(r"career|karriere|jobs?\b|stellen|emploi|lavora|join-us|arbeiten-bei", re.I)
_FEED_TYPES = {"application/rss+xml", "application/atom+xml"}
_SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class Link:
    url: str
    text: str


@dataclass
class Page:
    url: str
    title: str | None = None
    text: str = ""
    links: list[Link] = field(default_factory=list)
    feeds: list[str] = field(default_factory=list)
    published_on: date | None = None


@dataclass(frozen=True)
class Hit:
    url: str
    kind: str  # feed | news | career | page
    title: str | None
    published_on: date | None
    labels: frozenset[str]
    snippet: str


class _Extractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page = Page(base_url)
        self._skip = 0
        self._in_title = False
        self._link: str | None = None
        self._link_text: list[str] = []
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "a" and a.get("href"):
            self._link, self._link_text = urljoin(self.page.url, a["href"]), []
        elif tag == "link" and a.get("type") in _FEED_TYPES and a.get("href"):
            self.page.feeds.append(urljoin(self.page.url, a["href"]))
        elif tag == "meta" and a.get("property") == "article:published_time":
            self._set_date(a.get("content"))
        elif tag == "time":
            self._set_date(a.get("datetime"))

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag == "a" and self._link:
            self.page.links.append(Link(self._link, " ".join(self._link_text).strip()))
            self._link = None

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._in_title:
            self.page.title = (self.page.title or "") + data.strip()
            return
        self._text.append(data)
        if self._link:
            self._link_text.append(data.strip())

    def _set_date(self, value: str | None) -> None:
        if self.page.published_on is None and value and (m := _DATE.search(value)):
            with contextlib.suppress(ValueError):
                self.page.published_on = date.fromisoformat(m.group(1))

    def result(self) -> Page:
        self.page.text = re.sub(r"\s+", " ", " ".join(self._text))
        return self.page


def parse_html(url: str, html: str) -> Page:
    extractor = _Extractor(url)
    extractor.feed(html)
    return extractor.result()


def parse_feed(xml: bytes) -> list[tuple[str, str, str, date | None]]:
    """(link, title, summary, date) for RSS 2.0 and Atom items."""
    root = ElementTree.fromstring(xml)
    items = []
    for item in root.iter():
        tag = item.tag.rsplit("}", 1)[-1]
        if tag not in ("item", "entry"):
            continue
        fields = {child.tag.rsplit("}", 1)[-1]: child for child in item}
        link = fields.get("link")
        href = (link.get("href") or link.text or "").strip() if link is not None else ""
        title = (fields["title"].text or "") if "title" in fields else ""
        summary = next(
            (fields[k].text or "" for k in ("description", "summary", "content") if k in fields), ""
        )
        stamp = next(
            (fields[k].text or "" for k in ("pubDate", "published", "updated") if k in fields), ""
        )
        items.append((href, title.strip(), re.sub(r"<[^>]+>", " ", summary), _feed_date(stamp)))
    return items


class Robots:
    """robots.txt per host, cached, interpreted per RFC 9309."""

    def __init__(self, client: httpx2.Client) -> None:
        self._client = client
        self._parsers: dict[str, urllib.robotparser.RobotFileParser | bool] = {}

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._parsers:
            self._parsers[host] = self._load(host)
        rules = self._parsers[host]
        return rules if isinstance(rules, bool) else rules.can_fetch(ROBOTS_AGENT, url)

    def _load(self, host: str) -> urllib.robotparser.RobotFileParser | bool:
        try:
            response = self._client.get(f"{host}/robots.txt", timeout=15)
        except httpx2.HTTPError:  # unreachable, redirect loop, …: treat as disallowed
            return False
        if response.status_code >= 500:
            return False
        if response.status_code >= 400:
            return True
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser


class Fetcher:
    """GET with robots check, per-host delay and size limit."""

    def __init__(self, client: httpx2.Client, delay: float = HOST_DELAY) -> None:
        self.client = client
        self.robots = Robots(client)
        self.delay = delay
        self._last: dict[str, float] = {}

    def get(self, url: str) -> httpx2.Response | None:
        if not url.startswith(("http://", "https://")) or not self.robots.allowed(url):
            return None
        host = urlsplit(url).netloc
        wait = self._last.get(host, 0) + self.delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last[host] = time.monotonic()
        try:
            response = http.request(self.client, "GET", url, attempts=2, backoff=self.delay)
        except httpx2.HTTPError:
            return None
        if len(response.content) > MAX_BYTES:
            return None
        return response


def crawl_site(fetcher: Fetcher, home_url: str, max_pages: int = MAX_PAGES) -> list[Hit]:
    """Homepage, its feeds, news and career sections and their child pages; keyword hits."""
    hits: dict[str, Hit] = {}
    seen: set[str] = set()

    def visit(url: str, kind: str) -> Page | None:
        url = urldefrag(url).url
        if url in seen or len(seen) >= max_pages:
            return None
        seen.add(url)
        response = fetcher.get(url)
        if response is None or "html" not in response.headers.get("content-type", ""):
            return None
        page = parse_html(str(response.url), response.text)
        if match := scan(f"{page.title or ''} {page.text}"):
            hits[page.url] = Hit(
                page.url, kind, page.title, page.published_on, match.labels, match.snippet
            )
        return page

    home = visit(home_url, "page")
    if home is None:
        return []
    site = _registrable(home.url)
    for feed_url in home.feeds[:3]:
        hits.update({h.url: h for h in _feed_hits(fetcher, feed_url, seen, max_pages)})
    for pattern, kind, limit in ((NEWS, "news", 3), (CAREER, "career", 3)):
        sections = [
            link for link in home.links
            if pattern.search(f"{link.url} {link.text}")
            and (_registrable(link.url) == site or kind == "career")
        ][:limit]  # fmt: skip
        for section in sections:
            page = visit(section.url, kind)
            if page is None:
                continue
            section_host = urlsplit(page.url).netloc
            children = [
                link.url for link in page.links
                if urlsplit(link.url).netloc == section_host
                and len(urlsplit(link.url).path) > len(urlsplit(page.url).path)
            ]  # fmt: skip
            for child in children[:8]:
                visit(child, kind)
    return list(hits.values())


def _feed_hits(fetcher: Fetcher, url: str, seen: set[str], max_pages: int) -> Iterator[Hit]:
    if url in seen or len(seen) >= max_pages:
        return
    seen.add(url)
    response = fetcher.get(url)
    if response is None:
        return
    try:
        items = parse_feed(response.content)
    except ElementTree.ParseError:
        return
    for link, title, summary, published in items[:50]:
        if link and (match := scan(f"{title} {summary}")):
            yield Hit(link, "feed", title or None, published, match.labels, match.snippet)


def _registrable(url: str) -> str:
    """'jobs.example.ch' -> 'example.ch' (good enough for .ch/.com style domains)."""
    host = urlsplit(url).netloc.lower().split(":")[0]
    return ".".join(host.split(".")[-2:])


def _feed_date(value: str) -> date | None:
    if m := _DATE.search(value):
        return date.fromisoformat(m.group(1))
    try:
        return parsedate_to_datetime(value).date()
    except (TypeError, ValueError):
        return None
