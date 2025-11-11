import scrapy
import xml.etree.ElementTree as ET
from urllib import robotparser
import re

class DanTriSpider(scrapy.Spider):
    name = "dantri"
    allowed_domains = ["dantri.com.vn"]

    rss_feeds = [
        "https://dantri.com.vn/rss/home.rss",
        "https://dantri.com.vn/rss/xa-hoi.rss",
        "https://dantri.com.vn/rss/kinh-doanh.rss",
        "https://dantri.com.vn/rss/the-thao.rss",
        "https://dantri.com.vn/rss/giai-tri.rss",
        "https://dantri.com.vn/rss/giao-duc.rss",
        "https://dantri.com.vn/rss/suc-khoe.rss",
        "https://dantri.com.vn/rss/du-lich.rss",
        "https://dantri.com.vn/rss/phap-luat.rss",
        "https://dantri.com.vn/rss/the-gioi.rss",
        "https://dantri.com.vn/rss/o-to-xe-may.rss",
        "https://dantri.com.vn/rss/nhip-song-tre.rss",
        "https://dantri.com.vn/rss/tinh-yeu-gioi-tinh.rss",
        "https://dantri.com.vn/rss/cong-dong.rss",
    ]

    custom_settings = {
        "FEEDS": {"data_dantri.csv": {"format": "csv", "encoding": "utf-8-sig"}},
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
        # Xuất CSV theo thứ tự cột cố định
        "FEED_EXPORT_FIELDS": ["stt", "source", "category", "title", "content", "link", "label"],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.counter = 1
        self.rp = robotparser.RobotFileParser()
        self.rp.set_url("https://dantri.com.vn/robots.txt")
        self.rp.read()

    def start_requests(self):
        for feed in self.rss_feeds:
            yield scrapy.Request(feed, callback=self.parse_rss)

    def parse_rss(self, response):
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            self.logger.error(f"RSS feed không parse được: {response.url}")
            return

        # category lấy từ URL RSS
        category = response.url.split("/")[-1].replace(".rss", "")
        for item in root.findall(".//item"):
            title = item.findtext("title")
            link = item.findtext("link")

            if link and self.rp.can_fetch("*", link):
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
            else:
                self.logger.info(f"Skip {link} vì robots.txt không cho phép")

    async def parse_article(self, response):
        title = response.meta.get("title") or response.css("title::text").get(default="").strip()
        category = response.meta.get("category", "home")

        paragraphs = response.css(
            "div.singular-content p::text, article p::text, div.fck_detail p::text"
        ).getall()
        if not paragraphs:
            paragraphs = response.css("p::text").getall()

        content = " ".join(p.strip() for p in paragraphs if p.strip())

        remove_patterns = [
            r"(?i)GALLERY.*",
            r"(?i)This is a modal window.*",
            r"(?i)Bắt đầu cửa sổ hộp thoại.*",
            r"(?i)Kết thúc cửa sổ hộp thoại.*",
            r"(?i)Click để xem chi tiết.*",
            r"(?i)Ảnh:.*",
            r"(?i)Video:.*",
        ]
        for pattern in remove_patterns:
            content = re.sub(pattern, "", content)
        content = re.sub(r"\s+", " ", content).strip()
        if len(content) < 30:
            return
        content = content[:5000]

        yield {
            "stt": self.counter,
            "source": "Dân Trí",       # <--- thêm cột source cố định
            "category": category,       # <--- lấy từ RSS feed
            "title": title,
            "content": content,
            "link": response.meta.get("link", response.url),
            "label": 1,
        }
        self.counter += 1
