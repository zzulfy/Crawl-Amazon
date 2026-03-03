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

            # 书名 - 多种选择器
            title_elem = soup.select_one('span#productTitle')
            if not title_elem:
                title_elem = soup.select_one('h1.a-size-large')
            if not title_elem:
                title_elem = soup.select_one('#title span.a-size-large')
            if not title_elem:
                # 尝试从页面标题提取
                page_title = soup.select_one('title')
                if page_title:
                    title_text = page_title.get_text()
                    if 'Amazon' in title_text:
                        title_text = title_text.split(':')[0].strip()
                    if title_text and len(title_text) > 3:
                        book.title = clean_text(title_text)
            if title_elem:
                book.title = clean_text(title_elem.get_text())

            # 作者 - 多种选择器
            author_elem = soup.select_one('a.contributorNameID')
            if not author_elem:
                author_elem = soup.select_one('span.author a.a-link-normal')
            if not author_elem:
                author_elem = soup.select_one('#bylineInfo a.a-link-normal')
            if not author_elem:
                # 尝试从bylineInfo提取
                byline = soup.select_one('#bylineInfo')
                if byline:
                    author_match = re.search(r'by\s+([^,\n]+)', byline.get_text())
                    if author_match:
                        book.author = clean_text(author_match.group(1))
            if author_elem:
                book.author = clean_text(author_elem.get_text())

            # 封面图片
            cover_elem = soup.select_one('img#landingImage')
            if not cover_elem:
                cover_elem = soup.select_one('img#imgBlkFront')
            if not cover_elem:
                cover_elem = soup.select_one('#imageBlock img')
            if not cover_elem:
                cover_elem = soup.select_one('#main-image-container img')
            if cover_elem:
                data_old = cover_elem.get('data-old-hires')
                if data_old:
                    book.cover_url = data_old
                else:
                    book.cover_url = cover_elem.get('src')

            # 产品详情 - 多种方式
            details_dict = self._extract_details(soup)

            # 从详情字典提取信息
            for key, value in details_dict.items():
                key_lower = key.lower()

                # 出版商
                if 'publisher' in key_lower:
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

                # 页数
                if 'print length' in key_lower or 'number of pages' in key_lower or key_lower == 'pages':
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
                    if not book.isbn or len(book.isbn) != 13:
                        book.isbn = value.replace('-', '')
                    elif 'isbn-10' in key_lower:
                        pass

            # 简介描述 - 多种选择器
            desc_elem = soup.select_one('div#bookDescription_feature_div noscript')
            if not desc_elem:
                desc_elem = soup.select_one('div#productDescription p')
            if not desc_elem:
                desc_elem = soup.select_one('div#editorialReviews div.content')
            if not desc_elem:
                desc_elem = soup.select_one('[data-feature-name="bookDescription"]')
            if desc_elem:
                book.description = clean_text(desc_elem.get_text())

            # 价格 - 多种选择器
            price = self._get_price(soup)
            if price:
                book.used_price_gb = price

            logger.info(f"Amazon UK: 成功获取 '{book.title}'")
            return book

        except Exception as e:
            logger.error(f"Amazon UK: 解析页面失败: {e}")
            return None

    def _extract_details(self, soup: BeautifulSoup) -> dict:
        """提取产品详情"""
        details_dict = {}

        # 方法1: 表格形式
        detail_rows = soup.select('table#productDetails_techSections tr, table#productDetails_detailBullets_sections1 tr')
        for row in detail_rows:
            th = row.select_one('th')
            td = row.select_one('td')
            if th and td:
                key = clean_text(th.get_text())
                value = clean_text(td.get_text())
                if key and value:
                    details_dict[key.lower()] = value

        # 方法2: 列表形式
        if not details_dict:
            detail_bullets = soup.select('#detailBullets_feature_div li, .a-box-inner li')
            for li in detail_bullets:
                text = li.get_text()
                if ':' in text:
                    parts = text.split(':', 1)
                    key = clean_text(parts[0])
                    value = clean_text(parts[1]) if len(parts) > 1 else ''
                    if key and value:
                        details_dict[key.lower()] = value

        # 方法3: a-box 形式
        if not details_dict:
            boxes = soup.select('.a-box-group .a-box')
            for box in boxes:
                label = box.select_one('.a-size-base')
                value = box.select_one('.a-size-base.a-text-bold, .a-span9')
                if label and value:
                    key = clean_text(label.get_text())
                    val = clean_text(value.get_text())
                    if key and val:
                        details_dict[key.lower()] = val

        # 方法4: 从页面文本中提取
        page_text = soup.get_text()
        if not details_dict.get('publisher'):
            pub_match = re.search(r'Publisher\s*[:：]\s*([^;\n\(]+)', page_text)
            if pub_match:
                details_dict['publisher'] = clean_text(pub_match.group(1))

        if not details_dict.get('pages'):
            pages_match = re.search(r'(\d+)\s*pages', page_text, re.IGNORECASE)
            if pages_match:
                details_dict['pages'] = pages_match.group(1)

        return details_dict

    def _get_price(self, soup: BeautifulSoup) -> Optional[str]:
        """获取价格"""
        # 新书价格
        price_elem = soup.select_one('span.a-price span.a-offscreen')
        if price_elem:
            return clean_text(price_elem.get_text())

        # 二手价格
        price_elem = soup.select_one('span#usedBuyPrice')
        if price_elem:
            return clean_text(price_elem.get_text())

        # 其他价格选择器
        price_elem = soup.select_one('.a-color-price')
        if price_elem:
            price_text = clean_text(price_elem.get_text())
            if '£' in price_text or '$' in price_text:
                return price_text

        # 从页面文本提取
        html_text = str(soup)
        price_match = re.search(r'£[\d,.]+', html_text)
        if price_match:
            return price_match.group()

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
