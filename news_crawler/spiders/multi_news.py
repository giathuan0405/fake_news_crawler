import scrapy
from itertools import count


class MultiNewsSpider(scrapy.Spider):
    name = "multi_news"

    custom_settings = {
        "FEED_EXPORT_ENCODING": "utf-8-sig",
    }

    # Bộ đếm STT an toàn (thread-safe)
    counter = count(start=1)

    # === Nhân Dân ===
    nhandan_categories = [
        "https://nhandan.vn/chinhtri",
        "https://nhandan.vn/kinhte",
        "https://nhandan.vn/vanhoa",
        "https://nhandan.vn/thoisu",
        "https://nhandan.vn/quocte",
        "https://nhandan.vn/xahoi",
        "https://nhandan.vn/thethao",
    ]

    # === Tuổi Trẻ ===
    tuoitre_categories = [
        "https://tuoitre.vn/thoi-su.htm",
        "https://tuoitre.vn/the-gioi.htm",
        "https://tuoitre.vn/kinh-doanh.htm",
        "https://tuoitre.vn/cong-nghe.htm",
        "https://tuoitre.vn/van-hoa.htm",
        "https://tuoitre.vn/giai-tri.htm",
        "https://tuoitre.vn/the-thao.htm",
        "https://tuoitre.vn/giao-duc.htm",
    ]

    # === VNExpress ===
    vnexpress_categories = [
        "https://vnexpress.net/thoi-su",
        "https://vnexpress.net/the-gioi",
        "https://vnexpress.net/kinh-doanh",
        "https://vnexpress.net/the-thao",
        "https://vnexpress.net/giai-tri",
        "https://vnexpress.net/giao-duc",
        "https://vnexpress.net/doi-song",
    ]

    def start_requests(self):
        # Nhân Dân (~3000 bài)
        for url in self.nhandan_categories:
            for page in range(1, 80):
                yield scrapy.Request(f"{url}?page={page}", callback=self.parse_nhandan)

        # Tuổi Trẻ (~3000 bài)
        for url in self.tuoitre_categories:
            for page in range(1, 80):
                yield scrapy.Request(f"{url}?page={page}", callback=self.parse_tuoitre)

        # VNExpress (~3000 bài)
        for url in self.vnexpress_categories:
            for page in range(1, 80):
                yield scrapy.Request(f"{url}-p{page}", callback=self.parse_vnexpress)

    # ======== PARSER: NHÂN DÂN ========
    def parse_nhandan(self, response):
        for link in response.css("article.story a::attr(href)").getall():
            if link.startswith("http"):
                yield scrapy.Request(link, callback=self.parse_article,
                                     cb_kwargs={'category': "Nhân Dân"})

    # ======== PARSER: TUỔI TRẺ ========
    def parse_tuoitre(self, response):
        for link in response.css("h3.box-category-link-title a::attr(href), h3.title-news a::attr(href)").getall():
            if link.startswith("http"):
                yield scrapy.Request(link, callback=self.parse_article,
                                     cb_kwargs={'category': "Tuổi Trẻ"})

    # ======== PARSER: VNEXPRESS ========
    def parse_vnexpress(self, response):
        for link in response.css("h3.title-news a::attr(href)").getall():
            if link.startswith("http"):
                yield scrapy.Request(link, callback=self.parse_article,
                                     cb_kwargs={'category': "VNExpress"})

    # ======== PARSER CHUNG ========
    def parse_article(self, response, category):
        title = response.css("title::text").get(default="").strip()
        content = " ".join(response.css("p::text").getall()).strip()

        if len(content) < 100:
            return  # bỏ bài ngắn

        yield {
            "stt": next(self.counter),
            "category": category,
            "title": title,
            "content": content[:1000],
            "link": response.url,
            "label": 1,
        }
