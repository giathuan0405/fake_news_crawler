import scrapy
import xml.etree.ElementTree as ET
from urllib import robotparser
from urllib.parse import urljoin
import html   # 👈 thêm dòng này

class ThanhNienSpider(scrapy.Spider):
    name = "thanhnien"
    allowed_domains = ["thanhnien.vn"]

    rss_feeds = [
        "https://thanhnien.vn/rss/home.rss",
        "https://thanhnien.vn/rss/xa-hoi.rss",
        "https://thanhnien.vn/rss/kinh-te.rss",
        "https://thanhnien.vn/rss/the-thao.rss",
        "https://thanhnien.vn/rss/giai-tri.rss",
        "https://thanhnien.vn/rss/the-gioi.rss",
        "https://thanhnien.vn/rss/giao-duc.rss",
        "https://thanhnien.vn/rss/suc-khoe.rss",
    ]

    custom_settings = {
        "FEEDS": {"data_thanhnien.csv": {"format": "csv", "encoding": "utf-8-sig"}},
        "FEED_EXPORT_ENCODING": "utf-8-sig",
        "DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS": 4,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1,
        "AUTOTHROTTLE_MAX_DELAY": 8,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.counter = 1
        self.rp = robotparser.RobotFileParser()
        try:
            self.rp.set_url("https://thanhnien.vn/robots.txt")
            self.rp.read()
        except Exception as e:
            self.logger.warning(f"Không tải được robots.txt: {e}")
            self.rp = robotparser.RobotFileParser()
            self.rp.parse([])

    def start_requests(self):
        for feed in self.rss_feeds:
            yield scrapy.Request(feed, callback=self.parse_rss, errback=self.errback_log)

    def errback_log(self, failure):
        self.logger.error(repr(failure))

    def parse_rss(self, response):
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            self.logger.error(f"RSS feed không parse được: {response.url}")
            return

        category = response.url.split("/")[-1].replace(".rss", "")
        for item in root.findall(".//item"):
            title = item.findtext("title")
            link = item.findtext("link")

            if not link:
                continue

            link = urljoin(response.url, link)
            try:
                allowed = self.rp.can_fetch("*", link)
            except Exception:
                allowed = True
            if not allowed:
                continue

            yield scrapy.Request(
                link,
                callback=self.parse_article,
                meta={"playwright": True, "title": title, "link": link, "category": category},
                errback=self.errback_log,
            )

    async def parse_article(self, response):
        title = response.meta.get("title") or response.css("title::text").get(default="").strip()
        category = response.meta.get("category", "thanhnien")

        paragraphs = response.css(
            "div.article-body p::text, div.article-body p *::text, div.detail-content p::text, div.detail-content p *::text, article p::text, div.body p::text, div[itemprop='articleBody'] p::text"
        ).getall()
        if not paragraphs:
            paragraphs = response.css("p::text").getall()

        content = " ".join(p.strip() for p in paragraphs if p and p.strip())
        content = html.unescape(content)   # 👈 decode HTML entities
        title = html.unescape(title)       # 👈 decode tiêu đề

        content = content[:5000]
        if not content or len(content) < 30:
            return

        yield {
            "stt": self.counter,
            "source": "Thanh Niên",
            "category": category,
            "title": title,
            "content": content,
            "link": response.meta.get("link", response.url),
            "label": 1,
        }
        self.counter += 1
