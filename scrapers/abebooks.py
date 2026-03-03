"""
AbeBooks UK 爬虫
网站: https://www.abebooks.co.uk/
"""
import re
from typing import Optional, List
from bs4 import BeautifulSoup

from models import BookInfo
from scrapers.base import BaseScraper
from utils import clean_text, parse_price, logger, random_delay


class AbeBooksScraper(BaseScraper):
    """AbeBooks UK 网站爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.abebooks.co.uk"

    def search_by_isbn(self, isbn: str) -> Optional[BookInfo]:
        """通过ISBN搜索书籍"""
        # AbeBooks搜索URL
        url = f"{self.base_url}/servlet/SearchResults?kn={isbn}&sts=t"
        logger.info(f"AbeBooks: 搜索ISBN {isbn}")

        soup = self.fetch_page(url)
        if not soup:
            return None

        # 查找第一个结果（最相关的）
        result_item = soup.select_one('div.result-item')
        if not result_item:
            result_item = soup.select_one('article.book-item')
        if not result_item:
            result_item = soup.select_one('div.cf-result')

        if result_item:
            # 获取书籍详情链接
            link = result_item.select_one('a.title')
            if not link:
                link = result_item.select_one('a.book-title')
            if not link:
                link = result_item.select_one('h2 a, h3 a')

            if link:
                book_url = link.get('href', '')
                if book_url.startswith('/'):
                    book_url = self.base_url + book_url
                random_delay(1, 2)
                return self.get_book_details(book_url, isbn)

            # 如果没有详情链接，直接从搜索结果提取信息
            return self._parse_search_result(result_item, isbn, url)

        return None

    def get_book_details(self, url: str, isbn: str = None) -> Optional[BookInfo]:
        """获取书籍详情"""
        logger.info(f"AbeBooks: 获取详情 {url}")
        soup = self.fetch_page(url)
        if not soup:
            return None
        return self._parse_book_page(soup, isbn, url)

    def _parse_search_result(self, item: BeautifulSoup, isbn: str, url: str) -> Optional[BookInfo]:
        """从搜索结果项提取信息"""
        try:
            book = BookInfo(isbn=isbn or "")
            book.source_urls['abebooks'] = url

            # 书名
            title_elem = item.select_one('a.title')
            if not title_elem:
                title_elem = item.select_one('h2 a, h3 a')
            if title_elem:
                book.title = clean_text(title_elem.get_text())

            # 作者
            author_elem = item.select_one('p.author')
            if not author_elem:
                author_elem = item.select_one('span.author')
            if author_elem:
                author_text = author_elem.get_text()
                # 去掉"by "前缀
                author_text = re.sub(r'^by\s+', '', author_text, flags=re.IGNORECASE)
                book.author = clean_text(author_text)

            # 出版商
            publisher_elem = item.select_one('p.publisher')
            if not publisher_elem:
                publisher_elem = item.select_one('span.publisher')
            if publisher_elem:
                book.publisher = clean_text(publisher_elem.get_text())

            # 价格（二手书）
            price_elem = item.select_one('span.price')
            if not price_elem:
                price_elem = item.select_one('p.price')
            if price_elem:
                price_text = price_elem.get_text()
                book.used_price_gb = clean_text(price_text)

            # 封面
            img_elem = item.select_one('img.book-image')
            if not img_elem:
                img_elem = item.select_one('img.cover')
            if img_elem:
                book.cover_url = img_elem.get('src') or img_elem.get('data-src')

            logger.info(f"AbeBooks: 从搜索结果获取 '{book.title}'")
            return book

        except Exception as e:
            logger.error(f"AbeBooks: 解析搜索结果失败: {e}")
            return None

    def _parse_book_page(self, soup: BeautifulSoup, isbn: str, url: str) -> Optional[BookInfo]:
        """解析书籍详情页"""
        try:
            book = BookInfo(isbn=isbn or "")
            book.source_urls['abebooks'] = url

            # 书名
            title_elem = soup.select_one('h1.book-title')
            if not title_elem:
                title_elem = soup.select_one('h1[data-testid="book-title"]')
            if not title_elem:
                title_elem = soup.select_one('h1')
            if title_elem:
                book.title = clean_text(title_elem.get_text())

            # 作者
            author_elem = soup.select_one('span.author-name')
            if not author_elem:
                author_elem = soup.select_one('a.author-link')
            if not author_elem:
                # 尝试从页面文本中提取
                page_text = soup.get_text()
                author_match = re.search(r'by\s+([A-Za-z\s.]+?)(?:\n|$|Published)', page_text)
                if author_match:
                    book.author = clean_text(author_match.group(1))
            if author_elem:
                book.author = clean_text(author_elem.get_text())

            # 出版商
            publisher_elem = soup.select_one('span.publisher-name')
            if not publisher_elem:
                publisher_elem = soup.select_one('dd[data-testid="publisher"]')
            if publisher_elem:
                book.publisher = clean_text(publisher_elem.get_text())

            # 封面
            cover_elem = soup.select_one('img.book-cover')
            if not cover_elem:
                cover_elem = soup.select_one('img[data-testid="cover-image"]')
            if cover_elem:
                book.cover_url = cover_elem.get('src') or cover_elem.get('data-src')

            # 书籍详情
            details = soup.select('div.book-details dt, dd')
            details_dict = {}
            for i in range(0, len(details) - 1, 2):
                if details[i].name == 'dt' and details[i + 1].name == 'dd':
                    key = clean_text(details[i].get_text())
                    value = clean_text(details[i + 1].get_text())
                    if key and value:
                        details_dict[key.lower()] = value

            # 从详情字典提取信息
            for key, value in details_dict.items():
                if 'format' in key or 'binding' in key:
                    book.binding = value
                    if 'hardcover' in value.lower() or 'hardback' in value.lower():
                        book.binding = '精装'
                    elif 'paperback' in value.lower() or 'softcover' in value.lower():
                        book.binding = '平装'
                elif 'page' in key:
                    match = re.search(r'(\d+)', value)
                    if match:
                        book.pages = int(match.group(1))
                elif 'dimension' in key or 'size' in key:
                    book.dimensions = value
                elif 'weight' in key:
                    book.weight = value
                elif 'publisher' in key:
                    book.publisher = value

            # 简介
            desc_elem = soup.select_one('div.book-description')
            if not desc_elem:
                desc_elem = soup.select_one('div.synopsis')
            if desc_elem:
                book.description = clean_text(desc_elem.get_text())

            # 二手书价格列表
            prices = []
            price_elems = soup.select('span.item-price')
            for elem in price_elems[:5]:  # 只取前5个价格
                price = clean_text(elem.get_text())
                if price:
                    prices.append(price)

            if prices:
                book.used_price_gb = ', '.join(prices)

            logger.info(f"AbeBooks: 成功获取 '{book.title}'")
            return book

        except Exception as e:
            logger.error(f"AbeBooks: 解析页面失败: {e}")
            return None
