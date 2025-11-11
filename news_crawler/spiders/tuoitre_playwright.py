import scrapy
import xml.etree.ElementTree as ET

counter = 1

class TuoiTrePlaywrightSpider(scrapy.Spider):
    name = "tuoitre"
    allowed_domains = ["tuoitre.vn"]

    # Nhiều RSS feed
    rss_feeds = [
        "https://tuoitre.vn/rss/thoi-su.rss",
        "https://tuoitre.vn/rss/the-gioi.rss",
        "https://tuoitre.vn/rss/kinh-doanh.rss",
        "https://tuoitre.vn/rss/giai-tri.rss",
        "https://tuoitre.vn/rss/the-thao.rss",
        "https://tuoitre.vn/rss/giao-duc.rss",
        "https://tuoitre.vn/rss/suc-khoe.rss",
        "https://tuoitre.vn/rss/cong-nghe.rss",
        "https://tuoitre.vn/rss/du-lich.rss",
    ]

    custom_settings = {
        "FEED_EXPORT_ENCODING": "utf-8-sig",
        "DOWNLOAD_DELAY": 0.2,
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "LOG_LEVEL": "INFO",
        "FEEDS": {
            "data_tuoitre.csv": {"format": "csv", "encoding": "utf-8-sig"},
        },
        # Xuất CSV theo thứ tự cột cố định
        "FEED_EXPORT_FIELDS": ["stt", "source", "category", "title", "content", "link", "label"],
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
        category = response.meta.get("category", "tuoitre")

        # Lấy nội dung bài
        paragraphs = response.css("div.content.fck p::text, div#main-detail-body p::text").getall()
        if not paragraphs:
            paragraphs = response.css("p::text").getall()
        content = " ".join(p.strip() for p in paragraphs if p.strip())

        if not content or len(content) < 50:
            return
        content = content[:5000]

        yield {
            "stt": counter,
            "source": "Tuổi Trẻ",        # <--- cột source cố định
            "category": category,         # <--- category từ RSS
            "title": title,
            "content": content,
            "link": response.meta.get("link", response.url),
            "label": 1
        }
        counter += 1
