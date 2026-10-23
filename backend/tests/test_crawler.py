from datetime import date

import httpx2

from syncsight.ingestion.crawler import Fetcher, crawl_site, parse_feed, parse_html

HOME = """<html><head><title>Alpenpharma</title>
<link rel="alternate" type="application/rss+xml" href="/feed.xml"></head>
<body><script>var MES = 1;</script>
<a href="/news">News</a> <a href="https://jobs.alpenpharma-careers.ch/">Karriere</a>
<a href="/private/report">Report</a></body></html>"""
NEWS = """<html><head><title>News</title></head><body>
<a href="/news/2026-new-plant">New plant</a> <a href="/about">About</a></body></html>"""
ARTICLE = """<html><head><title>Neues Werk</title>
<meta property="article:published_time" content="2026-05-04T08:00:00Z"></head>
<body>Kapazitätserweiterung: neues Produktionsgebäude mit Manufacturing Execution System.</body>
</html>"""
JOBS = """<html><head><title>Jobs</title></head><body><a href="/job/1">Job</a></body></html>"""
JOB = "<html><head><title>MES Engineer (m/w/d)</title></head><body>Werum PAS-X</body></html>"
FEED = b"""<rss><channel><item><title>Go-live of PharmaSuite in Visp</title>
<link>https://www.alpenpharma.ch/news/pharmasuite</link>
<pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate>
<description>Paperless manufacturing</description></item></channel></rss>"""
PAGES = {
    "https://www.alpenpharma.ch/": HOME,
    "https://www.alpenpharma.ch/news": NEWS,
    "https://www.alpenpharma.ch/news/2026-new-plant": ARTICLE,
    "https://www.alpenpharma.ch/private/report": "<html><body>MES secret</body></html>",
    "https://jobs.alpenpharma-careers.ch/": JOBS,
    "https://jobs.alpenpharma-careers.ch/job/1": JOB,
}


def _site(requested: list[str]) -> httpx2.Client:
    def handler(request: httpx2.Request) -> httpx2.Response:
        url = str(request.url)
        requested.append(url)
        if url.endswith("/robots.txt"):
            return httpx2.Response(200, text="User-agent: *\nDisallow: /private/\n")
        if url.endswith("/feed.xml"):
            return httpx2.Response(
                200, content=FEED, headers={"content-type": "application/rss+xml"}
            )
        if url in PAGES:
            return httpx2.Response(200, text=PAGES[url], headers={"content-type": "text/html"})
        return httpx2.Response(404)

    return httpx2.Client(transport=httpx2.MockTransport(handler))


def test_parse_html_skips_scripts_and_collects_links_and_feeds() -> None:
    page = parse_html("https://www.alpenpharma.ch/", HOME)

    assert page.title == "Alpenpharma"
    assert "MES" not in page.text
    assert page.feeds == ["https://www.alpenpharma.ch/feed.xml"]
    assert page.links[0].url == "https://www.alpenpharma.ch/news"
    assert parse_html("https://x.ch/a", ARTICLE).published_on == date(2026, 5, 4)


def test_parse_feed_reads_rss_items() -> None:
    [(link, title, summary, published)] = parse_feed(FEED)

    assert link == "https://www.alpenpharma.ch/news/pharmasuite"
    assert title == "Go-live of PharmaSuite in Visp"
    assert "Paperless" in summary
    assert published == date(2026, 6, 1)


def test_crawl_site_finds_signals_and_respects_robots() -> None:
    requested: list[str] = []

    hits = crawl_site(Fetcher(_site(requested), delay=0), "https://www.alpenpharma.ch/")

    by_url = {hit.url: hit for hit in hits}
    assert by_url["https://www.alpenpharma.ch/news/pharmasuite"].labels == {
        "mes", "vendor:PharmaSuite",
    }  # fmt: skip
    article = by_url["https://www.alpenpharma.ch/news/2026-new-plant"]
    assert (article.kind, article.labels) == ("news", frozenset({"mes", "expansion"}))
    assert article.published_on == date(2026, 5, 4)
    job = by_url["https://jobs.alpenpharma-careers.ch/job/1"]
    assert (job.kind, job.labels) == ("career", frozenset({"mes", "vendor:Körber PAS-X"}))
    assert "https://www.alpenpharma.ch/private/report" not in requested


def test_unreachable_robots_means_nothing_is_fetched() -> None:
    requested: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requested.append(str(request.url))
        return httpx2.Response(503)

    fetcher = Fetcher(httpx2.Client(transport=httpx2.MockTransport(handler)), delay=0)

    assert crawl_site(fetcher, "https://www.down.ch/") == []
    assert requested == ["https://www.down.ch/robots.txt"]
