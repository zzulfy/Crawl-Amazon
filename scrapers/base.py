"""
爬虫基类
"""
from abc import ABC, abstractmethod
from typing import Optional, List
import requests
from bs4 import BeautifulSoup

from models import BookInfo
from utils import get_headers, create_session, random_delay, logger, get_proxies


class BaseScraper(ABC):
    """爬虫基类"""

    def __init__(self):
        self.session = create_session()
        self.base_url = ""

    @abstractmethod
    def search_by_isbn(self, isbn: str) -> Optional[BookInfo]:
        """通过ISBN搜索书籍"""
        pass

    @abstractmethod
    def get_book_details(self, url: str) -> Optional[BookInfo]:
        """获取书籍详情"""
        pass

    def fetch_page(self, url: str, referer: Optional[str] = None) -> Optional[BeautifulSoup]:
        """获取页面内容"""
        try:
            headers = get_headers(referer)
            proxies = get_proxies()
            response = self.session.get(url, headers=headers, proxies=proxies, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"请求失败 {url}: {e}")
            return None

    def _fetch_response(self, url: str, referer: Optional[str] = None) -> Optional[requests.Response]:
        """获取响应对象（包含重定向后的URL）"""
        try:
            headers = get_headers(referer)
            proxies = get_proxies()
            response = self.session.get(url, headers=headers, proxies=proxies, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response
        except requests.RequestException as e:
            logger.error(f"请求失败 {url}: {e}")
            return None

    def close(self):
        """关闭Session"""
        self.session.close()
