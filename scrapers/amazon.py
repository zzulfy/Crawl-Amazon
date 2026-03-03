"""
Amazon UK 爬虫
网站: https://www.amazon.co.uk/
"""
import re
from typing import Optional, List
from bs4 import BeautifulSoup

from models import BookInfo
from scrapers.base import BaseScraper
from utils import clean_text, parse_price, logger, random_delay


class AmazonUKScraper(BaseScraper):
    """Amazon UK 网站爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.amazon.co.uk"

    def search_by_isbn(self, isbn: str) -> Optional[BookInfo]:
        """通过ISBN搜索书籍"""
        # Amazon可以直接通过ISBN访问
        url = f"{self.base_url}/dp/{isbn}"
        logger.info(f"Amazon UK: 搜索ISBN {isbn}")

        soup = self.fetch_page(url)
        if not soup:
            # 尝试搜索
            return self._search_isbn(isbn)

        return self._parse_product_page(soup, isbn, url)

    def _search_isbn(self, isbn: str) -> Optional[BookInfo]:
        """通过搜索页查找ISBN"""
        search_url = f"{self.base_url}/s?k={isbn}&i=stripbooks"
        logger.info(f"Amazon UK: 搜索页查找 {isbn}")

        soup = self.fetch_page(search_url)
        if not soup:
            return None

        # 查找第一个结果
        result = soup.select_one('div[data-component-type="s-search-result"]')
        if result:
            link = result.select_one('a.a-link-normal.s-no-outline')
            if link:
                href = link.get('href', '')
                if href.startswith('/'):
                    product_url = self.base_url + href
                else:
                    product_url = href
                random_delay(1, 2)
                soup = self.fetch_page(product_url)
                if soup:
                    return self._parse_product_page(soup, isbn, product_url)

        return None

    def get_book_details(self, url: str, isbn: str = None) -> Optional[BookInfo]:
        """获取书籍详情"""
        logger.info(f"Amazon UK: 获取详情 {url}")
        soup = self.fetch_page(url)
        if not soup:
            return None
        return self._parse_product_page(soup, isbn, url)

    def _parse_product_page(self, soup: BeautifulSoup, isbn: str, url: str) -> Optional[BookInfo]:
        """解析产品页面"""
        try:
            book = BookInfo(isbn=isbn or "")
            book.source_urls['amazon_uk'] = url

            # 书名
            title_elem = soup.select_one('span#productTitle')
            if not title_elem:
                title_elem = soup.select_one('h1.a-size-large')
            if title_elem:
                book.title = clean_text(title_elem.get_text())

            # 作者
            author_elem = soup.select_one('span.author a.a-link-normal')
            if not author_elem:
                author_elem = soup.select_one('a.contributorNameID')
            if not author_elem:
                authors = soup.select('span.author a')
                if authors:
                    # 获取第一个作者
                    for a in authors:
                        text = clean_text(a.get_text())
                        if text and text not in ['(Goodreads Author)', 'et al.']:
                            author_elem = a
                            break
            if author_elem:
                book.author = clean_text(author_elem.get_text())

            # 封面图片
            cover_elem = soup.select_one('img#landingImage')
            if not cover_elem:
                cover_elem = soup.select_one('img#imgBlkFront')
            if not cover_elem:
                cover_elem = soup.select_one('#imageBlock img')
            if cover_elem:
                # 尝试获取高清图片
                data_old = cover_elem.get('data-old-hires')
                if data_old:
                    book.cover_url = data_old
                else:
                    book.cover_url = cover_elem.get('src')

            # 从产品详情表格提取信息
            detail_rows = soup.select('table#productDetails_techSections tr, table#productDetails_detailBullets_sections1 tr')
            if not detail_rows:
                # 尝试其他选择器
                detail_rows = soup.select('#detailBullets_feature_div li')

            details_dict = {}
            for row in detail_rows:
                if row.name == 'tr':
                    th = row.select_one('th')
                    td = row.select_one('td')
                    if th and td:
                        key = clean_text(th.get_text())
                        value = clean_text(td.get_text())
                        if key and value:
                            details_dict[key.lower()] = value
                elif row.name == 'li':
                    text = row.get_text()
                    if ':' in text:
                        parts = text.split(':', 1)
                        key = clean_text(parts[0])
                        value = clean_text(parts[1]) if len(parts) > 1 else ''
                        if key and value:
                            details_dict[key.lower()] = value

            # 从详情字典提取信息
            for key, value in details_dict.items():
                key_lower = key.lower()

                # 出版商
                if 'publisher' in key_lower or 'publisher:' == key_lower:
                    # 清理出版日期
                    pub_match = re.match(r'([^;(\d]+)', value)
                    if pub_match:
                        book.publisher = clean_text(pub_match.group(1))
                    else:
                        book.publisher = value

                # 装帧
                if 'hardcover' in key_lower or 'hardback' in key_lower:
                    book.binding = '精装'
                elif 'paperback' in key_lower:
                    book.binding = '平装'
                elif key_lower in ['product dimensions', 'dimensions']:
                    # 从尺寸信息中可能包含装帧
                    book.dimensions = value

                # 页数
                if 'print length' in key_lower or 'pages' in key_lower:
                    match = re.search(r'(\d+)', value)
                    if match:
                        book.pages = int(match.group(1))

                # 尺寸
                if 'product dimensions' in key_lower or 'dimensions' in key_lower:
                    book.dimensions = value

                # 重量
                if 'item weight' in key_lower or 'weight' in key_lower:
                    book.weight = value

                # ISBN
                if 'isbn-13' in key_lower:
                    if not book.isbn:
                        book.isbn = value.replace('-', '')
                elif 'isbn-10' in key_lower:
                    pass  # 优先使用ISBN-13

            # 简介描述
            desc_elem = soup.select_one('div#bookDescription_feature_div noscript')
            if desc_elem:
                book.description = clean_text(desc_elem.get_text())
            else:
                desc_elem = soup.select_one('div#productDescription p')
                if desc_elem:
                    book.description = clean_text(desc_elem.get_text())
                else:
                    # 尝试editorial reviews
                    desc_elem = soup.select_one('div#editorialReviews div.content')
                    if desc_elem:
                        book.description = clean_text(desc_elem.get_text())

            # 二手书价格 - 从Amazon Marketplace获取
            used_price = self._get_used_price(soup)
            if used_price:
                book.used_price_gb = used_price

            # 尝试从feature bullets获取更多信息
            bullets = soup.select('#feature-bullets li')
            for bullet in bullets:
                text = bullet.get_text().lower()
                if 'pages' in text:
                    match = re.search(r'(\d+)\s*pages', text)
                    if match and not book.pages:
                        book.pages = int(match.group(1))

            logger.info(f"Amazon UK: 成功获取 '{book.title}'")
            return book

        except Exception as e:
            logger.error(f"Amazon UK: 解析页面失败: {e}")
            return None

    def _get_used_price(self, soup: BeautifulSoup) -> Optional[str]:
        """获取二手书价格"""
        # 查找used & new价格
        used_elem = soup.select_one('span#usedBuyPrice')
        if used_elem:
            return clean_text(used_elem.get_text())

        # 查找more buying choices
        buying_choices = soup.select_one('div#moreBuyingChoices_feature_div')
        if buying_choices:
            price_elem = buying_choices.select_one('span.a-color-price')
            if price_elem:
                return clean_text(price_elem.get_text())

        # 从offer listing获取
        offer_elem = soup.select_one('span.olp-padding-block span.a-color-price')
        if offer_elem:
            return clean_text(offer_elem.get_text())

        return None

    def check_multiple_editions(self, isbn: str) -> List[BookInfo]:
        """检查是否有多个版本（同码不同款）"""
        editions = []

        # 搜索该ISBN的所有结果
        search_url = f"{self.base_url}/s?k={isbn}&i=stripbooks"
        soup = self.fetch_page(search_url)
        if not soup:
            return editions

        # 获取所有搜索结果
        results = soup.select('div[data-component-type="s-search-result"]')

        for result in results[:5]:  # 最多检查前5个结果
            link = result.select_one('a.a-link-normal.s-no-outline')
            if link:
                href = link.get('href', '')
                if '/dp/' in href:
                    product_url = self.base_url + href
                    random_delay(1, 2)
                    book = self.get_book_details(product_url, isbn)
                    if book:
                        editions.append(book)

        return editions
