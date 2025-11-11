import scrapy
import xml.etree.ElementTree as ET

counter = 1

class BaoChinhPhuSpider(scrapy.Spider):
    name = "baochinhphu"
    allowed_domains = ["baochinhphu.vn"]

    # Nguồn RSS của Báo Chính Phủ (đa chuyên mục)
    rss_feeds = [
        "https://baochinhphu.vn/thoi-su.rss",
        "https://baochinhphu.vn/kinh-te.rss",
        "https://baochinhphu.vn/quoc-te.rss",
        "https://baochinhphu.vn/xa-hoi.rss",
        "https://baochinhphu.vn/van-hoa.rss",
        "https://baochinhphu.vn/giao-duc.rss",
        "https://baochinhphu.vn/y-te.rss",
        "https://baochinhphu.vn/khoa-hoc-cong-nghe.rss",
        "https://baochinhphu.vn/du-lich.rss",
    ]

    custom_settings = {
    "FEED_EXPORT_ENCODING": "utf-8-sig",
    "FEEDS": {
        "data_baochinhphu.csv": {"format": "csv", "encoding": "utf-8-sig"},
    },
    "DOWNLOAD_DELAY": 0.3,
    "PLAYWRIGHT_BROWSER_TYPE": "chromium",
    "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
    "LOG_LEVEL": "INFO",
}


    def start_requests(self):
        for feed in self.rss_feeds:
            yield scrapy.Request(feed, callback=self.parse_rss)

    def parse_rss(self, response):
        root = ET.fromstring(response.text)
        category = response.url.split('/')[-1].replace('.rss', '')
        for item in root.findall('.//item'):
            title = item.findtext('title')
            link = item.findtext('link')
            if not link:
                continue
            yield scrapy.Request(
                link,
                callback=self.parse_article,
                meta={
                    "playwright": True,
                    "title": title,
                    "link": link,
                    "category": category
                }
            )

    async def parse_article(self, response):
        global counter
        title = response.meta.get("title") or response.css("title::text").get(default="").strip()
        category = response.meta.get("category", "tin-tuc")

        # Lấy đoạn văn bản trong nội dung bài viết
        paragraphs = response.css(
            "div.detail-content p::text, article p::text, div.article-content p::text"
        ).getall()

        if not paragraphs:
            paragraphs = response.css("p::text").getall()

        content = " ".join(p.strip() for p in paragraphs if p.strip())[:5000]
        if not content or len(content) < 50:
            return

        yield {
            "stt": counter,
            "source": "Báo Chính Phủ",
            "category": category,
            "title": title.strip(),
            "content": content.strip(),
            "link": response.meta.get("link", response.url),
            "label": 1
        }

        counter += 1
