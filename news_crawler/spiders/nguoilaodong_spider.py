import scrapy
import xml.etree.ElementTree as ET
from urllib import robotparser
import html
import re

class NLDSpider(scrapy.Spider):
    name = "nguoilaodong"
    allowed_domains = ["nld.com.vn"]

    # RSS feed của Báo Người Lao Động
    rss_feeds = [
        "https://nld.com.vn/rss/home.rss",
        "https://nld.com.vn/rss/chinh-tri.rss",
        "https://nld.com.vn/rss/kinh-te.rss",
        "https://nld.com.vn/rss/xa-hoi.rss",
        "https://nld.com.vn/rss/the-thao.rss",
        "https://nld.com.vn/rss/giai-tri.rss",
        "https://nld.com.vn/rss/phap-luat.rss",
        "https://nld.com.vn/rss/van-hoa.rss",
        "https://nld.com.vn/rss/giao-duc.rss",
        "https://nld.com.vn/rss/suc-khoe.rss",
    ]

    custom_settings = {
        "FEEDS": {"data_nld.csv": {"format": "csv", "encoding": "utf-8-sig"}},
        "FEED_EXPORT_ENCODING": "utf-8-sig",
        "DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS": 4,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1,
        "AUTOTHROTTLE_MAX_DELAY": 8,
    }

    def __init__(self):
        super().__init__()
        self.counter = 0  # Đếm số thứ tự bài viết
        self.rp = robotparser.RobotFileParser()
        try:
            self.rp.set_url("https://nld.com.vn/robots.txt")
            self.rp.read()
        except Exception as e:
            self.logger.warning(f"Không tải được robots.txt: {e}")

    def start_requests(self):
        for feed in self.rss_feeds:
            yield scrapy.Request(feed, callback=self.parse_rss)

    def parse_rss(self, response):
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            self.logger.warning(f"Lỗi parse RSS: {response.url}")
            return

        category = response.url.split("/")[-1].replace(".rss", "")
        for item in root.findall(".//item"):
            title = item.findtext("title")
            link = item.findtext("link")

            if not link:
                continue

            if not self.rp.can_fetch("*", link):
                self.logger.info(f"Bỏ qua (robots.txt cấm): {link}")
                continue

            yield scrapy.Request(
                link,
                callback=self.parse_article,
                meta={"title": title, "link": link, "category": category},
            )


    def parse_article(self, response):
        title = response.meta.get("title") or response.css("title::text").get(default="").strip()
        category = response.meta.get("category", "nguoilaodong")

        # 1) Tìm container chính của bài — ưu tiên selector cụ thể
        container = response.css(
            "div.detail-content, div.article-body, div.article-content, article, div.main-article"
        )
        if container:
            # chọn tất cả <p> bên trong container
            paragraph_nodes = container.xpath(".//p")
        else:
            # fallback: mọi <p> trong trang
            paragraph_nodes = response.xpath("//p")

        # 2) danh sách class/id/selector rác (các thẻ có class này sẽ bị loại)
        blacklist_class_substrings = [
            "pay", "subscribe", "subscription", "modal", "popup", "ads", "advert",
            "related", "recommend", "share", "social", "comment", "footer", "header",
            "breadcrumb", "promo", "payment", "paywall", "login", "dang-nhap", "vip"
        ]

        # 3) những cụm từ (tiếng Việt/tiếng Anh) mà nếu xuất hiện trong đoạn thì loại
        blacklist_phrases = [
            "bạn chưa đăng nhập", "hãy đăng nhập", "thanh toán", "gói đọc báo",
            "tải ứng dụng", "đồng bộ gói", "số tài khoản", "liên hệ quảng cáo",
            "quét zalo", "yêu cầu xuất hóa đơn", "bạn không thể gửi bình luận",
            "để đọc", "mời bạn", "để an toàn", "đăng ký tài khoản", "mua gói",
            "this is a modal window", "bắt đầu cửa sổ hộp thoại", "kết thúc cửa sổ hộp thoại"
        ]

        paragraphs = []
        for p in paragraph_nodes:
            # 4) nếu thẻ p là con của thẻ có class/id rác -> skip
            ancestor_classes = " ".join(p.xpath("ancestor-or-self::*[ @class ]/@class").getall() or [])
            ancestor_ids = " ".join(p.xpath("ancestor-or-self::*[ @id ]/@id").getall() or [])
            combined = (ancestor_classes + " " + ancestor_ids).lower()

            skip = False
            for bad in blacklist_class_substrings:
                if bad in combined:
                    skip = True
                    break
            if skip:
                continue

            # 5) lấy text thô của <p> (bao gồm text trong các node con)
            text = " ".join(p.xpath(".//text()").getall()).strip()
            if not text:
                continue

            text_lower = text.lower()

            # 6) nếu chứa 1 trong các cụm rác -> skip
            if any(phrase in text_lower for phrase in blacklist_phrases):
                continue

            # 7) loại bỏ đoạn ngắn vô nghĩa (số điện thoại, 1 từ, ký tự lẻ)
            if len(re.sub(r"\s+", "", text)) < 15:
                continue

            # 8) loại bỏ mẫu thường thấy của thông tin footer, contact hay donation bằng regex
            if re.search(r"tên tài khoản|ngân hàng|nội dung chuyển khoản|liên hệ quảng cáo|trụ sở chính", text_lower):
                continue

            # 9) cuối cùng decode HTML entity và chặn các ký tự thừa
            text = html.unescape(text)
            text = re.sub(r"\s+", " ", text).strip()

            paragraphs.append(text)

        content = " ".join(paragraphs)
        content = content[:5000]

        if not content or len(content) < 30:
            # logger nếu muốn debug
            self.logger.info(f"Bỏ bài (quá ngắn hoặc toàn rác): {response.url}")
            return

        self.counter += 1
        yield {
            "stt": self.counter,
            "source": "Người Lao Động",
            "category": category,
            "title": html.unescape(title),
            "content": content,
            "link": response.meta.get("link", response.url),
            "label": 1,
        }

