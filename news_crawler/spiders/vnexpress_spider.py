import scrapy
from bs4 import BeautifulSoup

counter = 1

class VNExpressSpider(scrapy.Spider):
    name = "vnexpress"
    allowed_domains = ["vnexpress.net"]

    # Liệt kê các chuyên mục cần cào
    categories = [
        "thoi-su",
        "kinh-doanh",
        "the-gioi",
        "giai-tri",
        "the-thao",
        "phap-luat",
        "giao-duc",
        "suc-khoe",
        "du-lich",
        "khoa-hoc",
        "so-hoa",
        "doi-song",
    ]

    
    start_urls = [
        f"https://vnexpress.net/{cat}-p{i}" 
        for cat in categories 
        for i in range(1, 50)
    ]

    custom_settings = {
        "FEED_EXPORT_ENCODING": "utf-8-sig",
        "FEED_EXPORT_FIELDS": ["stt", "source", "category", "title", "content", "link", "label"],
        "DOWNLOAD_DELAY": 0.3,
        "CONCURRENT_REQUESTS": 8,
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "FEEDS": {
            "data_vnexpress.csv": {"format": "csv", "encoding": "utf-8-sig"},
        },
    }

    def parse(self, response):
        # Lấy category từ URL
        category = response.url.split("/")[-1].split("-p")[0]
        
        # Duyệt từng bài viết trong trang
        for link in response.css("h3.title-news a::attr(href)").getall():
            # Bỏ qua các link trùng hoặc dạng video
            if "video" in link or "interactive" in link:
                continue
            yield scrapy.Request(
                link,
                callback=self.parse_article,
                meta={"category": category},
            )

    def parse_article(self, response):
        global counter
        soup = BeautifulSoup(response.text, "html.parser")

        # Lấy nội dung
        paragraphs = [p.get_text(strip=True) for p in soup.select("p.Normal")]
        content = " ".join(paragraphs).strip()

        # Lọc bài rác, bài ngắn
        if not content or len(content) < 50:
            return

        title = soup.title.string.strip() if soup.title else ""

        yield {
            "stt": counter,
            "source": "VNExpress",                  
            "category": response.meta.get("category", ""),  
            "title": title,
            "content": content[:5000],
            "link": response.url,
            "label": 1,
        }

        counter += 1
