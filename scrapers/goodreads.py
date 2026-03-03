"""
Goodreads 爬虫
网站: https://www.goodreads.com/
"""
import re
from typing import Optional, List
from bs4 import BeautifulSoup

from models import BookInfo
from scrapers.base import BaseScraper
from utils import clean_text, logger, random_delay


class GoodreadsScraper(BaseScraper):
    """Goodreads 网站爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.goodreads.com"

    def search_by_isbn(self, isbn: str) -> Optional[BookInfo]:
        """通过ISBN搜索书籍"""
        # Goodreads 搜索会自动重定向到书籍页面
        url = f"{self.base_url}/search?q={isbn}"
        logger.info(f"Goodreads: 搜索ISBN {isbn}")

        response = self._fetch_response(url)
        if not response:
            return None

        final_url = response.url
        soup = BeautifulSoup(response.text, 'lxml')

        # 检查是否直接重定向到书籍页面
        if '/book/show/' in final_url:
            logger.info(f"Goodreads: 直接找到书籍页面")
            return self._parse_book_page(soup, isbn, final_url)

        # 如果在搜索结果页面，查找书籍链接
        book_link = soup.select_one('a.bookTitle')
        if book_link:
            book_url = self.base_url + book_link.get('href', '')
            random_delay(1, 2)
            return self.get_book_details(book_url, isbn)

        logger.warning(f"Goodreads: 未找到ISBN {isbn}")
        return None

    def get_book_details(self, url: str, isbn: str = None) -> Optional[BookInfo]:
        """获取书籍详情"""
        logger.info(f"Goodreads: 获取详情 {url}")
        soup = self.fetch_page(url)
        if not soup:
            return None
        return self._parse_book_page(soup, isbn, url)

    def _parse_book_page(self, soup: BeautifulSoup, isbn: str, url: str) -> Optional[BookInfo]:
        """解析书籍页面"""
        try:
            book = BookInfo(isbn=isbn or "")
            book.source_urls['goodreads'] = url

            # 书名
            title_elem = soup.select_one('h1.Text__title1')
            if not title_elem:
                title_elem = soup.select_one('h1#bookTitle')
            if title_elem:
                book.title = clean_text(title_elem.get_text())

            # 作者
            author_elem = soup.select_one('a.ContributorLink')
            if not author_elem:
                author_elem = soup.select_one('a.authorName')
            if author_elem:
                book.author = clean_text(author_elem.get_text())

            # 封面图片
            cover_elem = soup.select_one('img.ResponsiveImage')
            if not cover_elem:
                cover_elem = soup.select_one('#coverImage')
            if not cover_elem:
                cover_elem = soup.select_one('img.bookCover')
            if cover_elem:
                book.cover_url = cover_elem.get('src') or cover_elem.get('data-src')

            # 书籍详情 - 在页面中搜索各种信息
            details_section = soup.find('div', {'data-testid': 'contentContainer'})
            page_text = soup.get_text()

            # 简介
            desc_elem = soup.select_one('div.BookPageMetadataSection__description')
            if desc_elem:
                book.description = clean_text(desc_elem.get_text())
            else:
                desc_elem = soup.select_one('#description')
                if desc_elem:
                    book.description = clean_text(desc_elem.get_text())

            # 从页面文本中提取信息
            # 页数
            pages_match = re.search(r'(\d+)\s*pages', page_text, re.IGNORECASE)
            if pages_match:
                book.pages = int(pages_match.group(1))

            # 出版商
            publisher_match = re.search(r'Published\s*(?:by\s*)?([A-Za-z0-9\s&.,]+?)(?:\n|$|\d{4})', page_text)
            if publisher_match:
                book.publisher = clean_text(publisher_match.group(1))

            # 尝试从详情区域获取更多信息
            details = soup.find_all('div', class_='BookDetails')
            for detail in details:
                detail_text = detail.get_text()
                # 装帧
                if 'hardcover' in detail_text.lower():
                    book.binding = '精装'
                elif 'paperback' in detail_text.lower():
                    book.binding = '平装'

            # 从ProductDetails提取
            self._extract_from_product_details(soup, book)

            logger.info(f"Goodreads: 成功获取 '{book.title}'")
            return book

        except Exception as e:
            logger.error(f"Goodreads: 解析页面失败: {e}")
            return None

    def _extract_from_product_details(self, soup: BeautifulSoup, book: BookInfo):
        """从产品详情区域提取信息"""
        # 查找所有详情行
        detail_rows = soup.find_all('div', {'data-testid': 'contentContainer'})

        for row in detail_rows:
            text = row.get_text().lower()
            full_text = row.get_text()

            # 装帧
            if 'format' in text or 'binding' in text:
                if 'hardcover' in text:
                    book.binding = '精装'
                elif 'paperback' in text:
                    book.binding = '平装'

            # 页数
            if 'pages' in text:
                match = re.search(r'(\d+)\s*pages', full_text, re.IGNORECASE)
                if match:
                    book.pages = int(match.group(1))

            # 尺寸
            if 'dimensions' in text or 'size' in text:
                dim_match = re.search(r'([\d.]+\s*[xX×]\s*[\d.]+\s*(?:[xX×]\s*[\d.]+)?)', full_text)
                if dim_match:
                    book.dimensions = dim_match.group(1)

        # 尝试从script标签中提取JSON数据
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and '"@type":"Book"' in script.string:
                try:
                    # 尝试提取JSON-LD数据
                    import json
                    json_match = re.search(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                                          str(script), re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        if not book.title:
                            book.title = data.get('name')
                        if not book.author:
                            author_data = data.get('author', {})
                            book.author = author_data.get('name')
                        if not book.description:
                            book.description = data.get('description')
                except:
                    pass
