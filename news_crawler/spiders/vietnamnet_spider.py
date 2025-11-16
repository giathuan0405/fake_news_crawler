import scrapy
from scrapy_playwright.page import PageMethod


class VietnamnetSpider(scrapy.Spider):
    name = "vietnamnet"
    allowed_domains = ["vietnamnet.vn"]

    custom_settings = {
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True},
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",

        "FEEDS": {
            "data_vietnamnet.csv": {
                "format": "csv",
                "overwrite": True,
                "encoding": "utf-8-sig",
                "fields": ["stt", "source", "category", "title", "content", "link", "label"],
            }
        },
    }

    
    start_urls = [
        "https://vietnamnet.vn/thoi-su/",
        "https://vietnamnet.vn/thoi-tiet/",
        "https://vietnamnet.vn/giai-tri/",
        "https://vietnamnet.vn/the-gioi/",
        "https://vietnamnet.vn/kinh-doanh/",
        "https://vietnamnet.vn/giao-duc/",
        "https://vietnamnet.vn/suc-khoe/",
        "https://vietnamnet.vn/cong-nghe/",
        "https://vietnamnet.vn/doi-song/",
        "https://vietnamnet.vn/phap-luat/",
        "https://vietnamnet.vn/oto-xe-may/",
        "https://vietnamnet.vn/the-thao/",
    ]

    def __init__(self):
        self.count = 0

    def parse(self, response):
        # Lấy category từ URL chuyên mục
        category = response.url.strip("/").split("/")[-1]

        # Lấy link bài viết
        links = response.css("h3 a::attr(href), article a::attr(href)").getall()
        links = list(set(links))

        for link in links:
            if self.count >= 500:
                return

            if not link.startswith("http"):
                link = response.urljoin(link)

            yield scrapy.Request(
                link,
                callback=self.parse_article,
                cb_kwargs={"category": category},
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod(
                            "wait_for_selector",
                            "article, div.content-detail, div.article-content",
                            timeout=8000
                        )
                    ]
                }
            )

        # Phân trang
        next_page = response.css("a[rel='next']::attr(href), a.next::attr(href)").get()
        if next_page and self.count < 500:
            next_page = response.urljoin(next_page)
            yield scrapy.Request(
                next_page,
                callback=self.parse,
                cb_kwargs={"category": category}
            )

    def parse_article(self, response, category):
        if self.count >= 500:
            return
        
        self.count += 1

        title = response.css("h1::text").get()

        # Nhiều selector vì Vietnamnet dùng nhiều layout
        selectors = [
            "article p::text",
            "div.content-detail p::text",
            "div.article-content p::text",
            "div.maincontent p::text",
            "div#maincontent p::text",
        ]

        content = ""
        for sel in selectors:
            tmp = response.css(sel).getall()
            if tmp:
                content = " ".join(tmp).strip()
                break

        yield {
            "stt": self.count,
            "source": "vietnamnet",
            "category": category,
            "title": title,
            "content": content,
            "link": response.url,
            "label": 1,
        }
