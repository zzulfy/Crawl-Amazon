#!/usr/bin/env python3
"""
Selenium 版本爬虫 - 可以处理 JavaScript 渲染的页面
使用方法: python main.py --selenium 9781845614652
安装依赖: pip install selenium webdriver-manager
"""
import re
import time
from typing import Optional, Dict

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

import subprocess


class SeleniumCrawler:
    """基于 Selenium 的爬虫"""

    def __init__(self, headless=True):
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium未安装，请运行: pip install selenium webdriver-manager")

        self.driver = None
        self.headless = headless
        self.base_urls = {
            'amazon_uk': 'https://www.amazon.co.uk',
            'abebooks': 'https://www.abebooks.co.uk',
            'goodreads': 'https://www.goodreads.com'
        }

    def _init_driver(self):
        """初始化浏览器"""
        if self.driver:
            return

        options = Options()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--lang=en-US')

        # 查找系统中的 chromedriver
        chromedriver_paths = [
            '/usr/bin/chromedriver',           # 系统 apt 安装
            '/snap/bin/chromium.chromedriver', # snap 安装
            '/usr/lib/chromium-browser/chromedriver',  # 某些系统路径
        ]

        chromedriver_path = None
        for path in chromedriver_paths:
            try:
                result = subprocess.run(['test', '-x', path], capture_output=True)
                if result.returncode == 0:
                    chromedriver_path = path
                    break
            except:
                continue

        try:
            if chromedriver_path:
                service = Service(executable_path=chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                # 尝试不指定路径，让 selenium 自动查找
                self.driver = webdriver.Chrome(options=options)
        except Exception as e:
            print(f"初始化浏览器失败: {e}")
            print("请确保已安装 Chrome/Chromium 浏览器")
            print("Ubuntu/Debian: sudo apt install chromium-browser chromium-chromedriver")
            raise

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def scrape_amazon_uk(self, isbn: str) -> Optional[Dict]:
        """爬取 Amazon UK"""
        from models import BookInfo
        from utils import clean_text

        self._init_driver()

        # 先搜索
        search_url = f"{self.base_urls['amazon_uk']}/s?k={isbn}&i=stripbooks"
        print(f"Amazon UK (Selenium): 搜索 {isbn}")

        try:
            self.driver.get(search_url)
            time.sleep(3)

            book = BookInfo(isbn=isbn)

            # 查找第一个产品
            products = self.driver.find_elements(By.CSS_SELECTOR, '[data-component-type="s-search-result"]')
            if not products:
                print("  未找到产品")
                return None

            # 点击第一个产品
            try:
                link = products[0].find_element(By.CSS_SELECTOR, 'a.a-link-normal')
                product_url = link.get_attribute('href')
                link.click()
                time.sleep(3)
            except:
                print("  无法点击产品")
                return None

            # 提取信息
            try:
                title = self.driver.find_element(By.ID, 'productTitle')
                book.title = title.text.strip()
            except:
                pass

            try:
                author = self.driver.find_element(By.CSS_SELECTOR, '.contributorNameID')
                book.author = author.text.strip()
            except:
                try:
                    author = self.driver.find_element(By.CSS_SELECTOR, '#bylineInfo a')
                    book.author = author.text.strip()
                except:
                    pass

            try:
                price = self.driver.find_element(By.CSS_SELECTOR, '.a-price .a-offscreen')
                book.used_price_gb = price.text.strip()
            except:
                try:
                    price = self.driver.find_element(By.CSS_SELECTOR, '.a-color-price')
                    book.used_price_gb = price.text.strip()
                except:
                    pass

            try:
                cover = self.driver.find_element(By.ID, 'landingImage')
                book.cover_url = cover.get_attribute('src')
            except:
                pass

            # 提取产品详情
            try:
                details = self.driver.find_elements(By.CSS_SELECTOR, '#detailBullets_feature_div li')
                for li in details:
                    text = li.text
                    if ':' in text:
                        key, value = text.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()

                        if 'publisher' in key:
                            match = re.match(r'([^;(\d]+)', value)
                            if match:
                                book.publisher = match.group(1).strip()
                        elif 'paperback' in key or 'hardcover' in key:
                            book.binding = '平装' if 'paperback' in key else '精装'
                        elif 'pages' in key or 'print length' in key:
                            match = re.search(r'(\d+)', value)
                            if match:
                                book.pages = int(match.group(1))
                        elif 'dimensions' in key:
                            book.dimensions = value
                        elif 'weight' in key:
                            book.weight = value
            except:
                pass

            # 提取简介
            try:
                desc = self.driver.find_element(By.CSS_SELECTOR, '#bookDescription_feature_div')
                book.description = desc.text.strip()[:500]
            except:
                pass

            book.source_urls['amazon_uk'] = self.driver.current_url
            print(f"  书名: {book.title}")
            print(f"  作者: {book.author}")
            print(f"  价格: {book.used_price_gb}")

            return book

        except Exception as e:
            print(f"Amazon UK (Selenium) 错误: {e}")
            return None

    def scrape_abebooks(self, isbn: str) -> Optional[Dict]:
        """爬取 AbeBooks UK"""
        from models import BookInfo

        self._init_driver()

        url = f"{self.base_urls['abebooks']}/servlet/SearchResults?kn={isbn}&sts=t"
        print(f"AbeBooks (Selenium): 搜索 {isbn}")

        try:
            self.driver.get(url)
            time.sleep(4)

            book = BookInfo(isbn=isbn)

            # 查找搜索结果
            results = self.driver.find_elements(By.CSS_SELECTOR, '[data-cy="listing-item"]')
            if not results:
                results = self.driver.find_elements(By.CSS_SELECTOR, '.result-item')

            if not results:
                print("  未找到结果")
                return None

            # 获取第一个结果
            result = results[0]

            try:
                title = result.find_element(By.CSS_SELECTOR, 'a.title, [data-cy="listing-title"]')
                book.title = title.text.strip()
            except:
                pass

            try:
                author = result.find_element(By.CSS_SELECTOR, '.author, [data-cy="listing-author"]')
                author_text = author.text.strip()
                # 去掉 "by " 前缀
                author_text = re.sub(r'^by\s+', '', author_text, flags=re.IGNORECASE)
                book.author = author_text
            except:
                pass

            try:
                price = result.find_element(By.CSS_SELECTOR, '.price, [data-cy="listing-price"]')
                book.used_price_gb = price.text.strip()
            except:
                pass

            try:
                cover = result.find_element(By.CSS_SELECTOR, 'img')
                book.cover_url = cover.get_attribute('src')
            except:
                pass

            book.source_urls['abebooks'] = url
            print(f"  书名: {book.title}")
            print(f"  作者: {book.author}")
            print(f"  价格: {book.used_price_gb}")

            return book

        except Exception as e:
            print(f"AbeBooks (Selenium) 错误: {e}")
            return None

    def scrape_goodreads(self, isbn: str) -> Optional[Dict]:
        """爬取 Goodreads"""
        from models import BookInfo

        self._init_driver()

        url = f"{self.base_urls['goodreads']}/search?q={isbn}"
        print(f"Goodreads (Selenium): 搜索 {isbn}")

        try:
            self.driver.get(url)
            time.sleep(3)

            book = BookInfo(isbn=isbn)

            # 检查是否重定向到书籍页面
            if '/book/show/' in self.driver.current_url:
                book.source_urls['goodreads'] = self.driver.current_url
            else:
                # 查找搜索结果
                try:
                    book_link = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'a.bookTitle'))
                    )
                    book_link.click()
                    time.sleep(3)
                    book.source_urls['goodreads'] = self.driver.current_url
                except:
                    print("  未找到书籍")
                    return None

            # 提取信息
            try:
                title = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="bookTitle"]')
                book.title = title.text.strip()
            except:
                try:
                    title = self.driver.find_element(By.CSS_SELECTOR, 'h1#bookTitle')
                    book.title = title.text.strip()
                except:
                    pass

            try:
                author = self.driver.find_element(By.CSS_SELECTOR, 'a.ContributorLink')
                book.author = author.text.strip()
            except:
                try:
                    author = self.driver.find_element(By.CSS_SELECTOR, 'a.authorName')
                    book.author = author.text.strip()
                except:
                    pass

            try:
                cover = self.driver.find_element(By.CSS_SELECTOR, 'img.ResponsiveImage')
                book.cover_url = cover.get_attribute('src')
            except:
                try:
                    cover = self.driver.find_element(By.ID, 'coverImage')
                    book.cover_url = cover.get_attribute('src')
                except:
                    pass

            # 提取页数
            try:
                page_text = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="pagesFormat"]').text
                match = re.search(r'(\d+)\s*pages', page_text, re.IGNORECASE)
                if match:
                    book.pages = int(match.group(1))
            except:
                pass

            # 提取简介
            try:
                desc = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="description"]')
                book.description = desc.text.strip()[:500]
            except:
                pass

            print(f"  书名: {book.title}")
            print(f"  作者: {book.author}")

            return book

        except Exception as e:
            print(f"Goodreads (Selenium) 错误: {e}")
            return None

    def scrape_all(self, isbn: str) -> Dict:
        """爬取所有网站"""
        from models import BookInfo

        book = BookInfo(isbn=isbn)

        # Amazon
        amazon_book = self.scrape_amazon_uk(isbn)
        if amazon_book:
            book = book.merge(amazon_book)

        time.sleep(2)

        # Goodreads（始终调用以获取source_url）
        gr_book = self.scrape_goodreads(isbn)
        if gr_book:
            book = book.merge(gr_book)
        time.sleep(2)

        # AbeBooks
        abe_book = self.scrape_abebooks(isbn)
        if abe_book:
            if abe_book.used_price_gb and not book.used_price_gb:
                book.used_price_gb = abe_book.used_price_gb
            book = book.merge(abe_book)

        return book


def check_selenium_available():
    """检查 Selenium 是否可用"""
    return SELENIUM_AVAILABLE


if __name__ == '__main__':
    if not SELENIUM_AVAILABLE:
        print("请先安装依赖: pip install selenium")
        exit(1)

    import sys
    isbn = sys.argv[1] if len(sys.argv) > 1 else "9780743273565"

    crawler = SeleniumCrawler(headless=True)
    try:
        book = crawler.scrape_all(isbn)
        print("\n结果:")
        print(book.to_json())
    finally:
        crawler.close()
