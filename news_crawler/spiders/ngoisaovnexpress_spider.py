import scrapy
import xml.etree.ElementTree as ET
import re

class NgoiSaoSpider(scrapy.Spider):
    name = "ngoisao"
    allowed_domains = ["ngoisao.vnexpress.net"]

    rss_feeds = [
    "https://ngoisao.vnexpress.net/rss/giai-tri.rss",
    "https://ngoisao.vnexpress.net/rss/the-thao.rss",
    "https://ngoisao.vnexpress.net/rss/thoi-trang.rss",
    "https://ngoisao.vnexpress.net/rss/doi-song.rss",
    "https://ngoisao.vnexpress.net/rss/sao-viet.rss",
    "https://ngoisao.vnexpress.net/rss/am-nhac.rss",
    "https://ngoisao.vnexpress.net/rss/phim.rss",
    "https://ngoisao.vnexpress.net/rss/hoa-hau.rss"
    ]


    custom_settings = {
        "FEEDS": {"data_ngoisao.csv": {"format": "csv", "encoding": "utf-8-sig"}},
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
        "FEED_EXPORT_FIELDS": ["stt", "source", "category", "title", "content", "link", "label"],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.counter = 1

    def start_requests(self):
        for feed in self.rss_feeds:
            yield scrapy.Request(feed, callback=self.parse_rss)

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
            if link:
                yield scrapy.Request(
                    link,
                    callback=self.parse_article,
                    meta={
                        "playwright": True,
                        "title": title,
                        "link": link,
                        "category": category,
                    },
                )

    async def parse_article(self, response):
        if self.counter > 500:
            return

        title = response.meta.get("title") or response.css("h1.title-detail::text").get(default="").strip()
        category = response.meta.get("category", "giai-tri")

        paragraphs = response.css("p::text").getall()
        content = " ".join(p.strip() for p in paragraphs if p.strip())

        content = re.sub(r"\s+", " ", content).strip()
        if len(content) < 50:
            return

        # Loại bỏ bài quảng cáo/thông báo
        ban_bao_patterns = [
            r"Chúng tôi xin thông báo",
            r"Đường dây nóng",
            r"Xin trân trọng cảm ơn",
            r"Đặt mua các ấn phẩm",
        ]
        for pattern in ban_bao_patterns:
            if re.search(pattern, content, re.I):
                return

        content = content[:5000]

        yield {
            "stt": self.counter,
            "source": "Ngoi Sao",
            "category": category,
            "title": title,
            "content": content,
            "link": response.meta.get("link", response.url),
            "label": 1,
        }
        self.counter += 1
