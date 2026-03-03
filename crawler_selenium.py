#!/usr/bin/env python3
"""
使用Selenium的爬虫 - 可以处理JavaScript渲染的页面
需要安装: pip install selenium webdriver-manager
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
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("警告: Selenium未安装，请运行: pip install selenium webdriver-manager")


class SeleniumCrawler:
    """基于Selenium的爬虫"""

    def __init__(self, headless=True):
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium未安装")

        self.driver = None
        self.headless = headless

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

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def scrape_abebooks(self, isbn: str) -> Optional[Dict]:
        """爬取AbeBooks"""
        self._init_driver()

        url = f"https://www.abebooks.co.uk/servlet/SearchResults?kn={isbn}&sts=t"
        print(f"AbeBooks: {url}")

        try:
            self.driver.get(url)
            time.sleep(3)  # 等待页面加载

            books = []

            # 查找搜索结果
            results = self.driver.find_elements(By.CSS_SELECTOR, '[data-cy="listing-item"]')
            if not results:
                results = self.driver.find_elements(By.CSS_SELECTOR, '.result-item')

            for result in results[:5]:
                try:
                    book = {'isbn': isbn, 'source': 'abebooks'}

                    # 书名
                    title_elem = result.find_element(By.CSS_SELECTOR, 'a.title, [data-cy="listing-title"]')
                    book['title'] = title_elem.text.strip() if title_elem else None

                    # 价格
                    price_elem = result.find_element(By.CSS_SELECTOR, '.price, [data-cy="listing-price"]')
                    book['price'] = price_elem.text.strip() if price_elem else None

                    # 作者
                    try:
                        author_elem = result.find_element(By.CSS_SELECTOR, '.author, [data-cy="listing-author"]')
                        book['author'] = author_elem.text.strip() if author_elem else None
                    except:
                        pass

                    if book.get('title') or book.get('price'):
                        books.append(book)
                        print(f"  找到: {book.get('title', 'N/A')[:50]} - {book.get('price', 'N/A')}")

                except Exception as e:
                    continue

            return {'books': books} if books else None

        except Exception as e:
            print(f"AbeBooks错误: {e}")
            return None

    def scrape_amazon_uk(self, isbn: str) -> Optional[Dict]:
        """爬取Amazon UK"""
        self._init_driver()

        url = f"https://www.amazon.co.uk/s?k={isbn}&i=stripbooks"
        print(f"Amazon UK: {url}")

        try:
            self.driver.get(url)
            time.sleep(3)

            book = {'isbn': isbn, 'source': 'amazon_uk'}

            # 查找第一个产品
            try:
                product = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-component-type="s-search-result"]'))
                )

                # 点击产品
                link = product.find_element(By.CSS_SELECTOR, 'a.a-link-normal')
                link.click()
                time.sleep(3)

                # 提取信息
                try:
                    title = self.driver.find_element(By.ID, 'productTitle')
                    book['title'] = title.text.strip()
                except:
                    pass

                try:
                    author = self.driver.find_element(By.CSS_SELECTOR, '.contributorNameID, .author a')
                    book['author'] = author.text.strip()
                except:
                    pass

                try:
                    price = self.driver.find_element(By.CSS_SELECTOR, '.a-price .a-offscreen')
                    book['price'] = price.text.strip()
                except:
                    pass

                print(f"  书名: {book.get('title')}")
                print(f"  作者: {book.get('author')}")
                print(f"  价格: {book.get('price')}")

                return book

            except Exception as e:
                print(f"  未找到产品: {e}")
                return None

        except Exception as e:
            print(f"Amazon UK错误: {e}")
            return None


def test_selenium():
    """测试Selenium爬虫"""
    if not SELENIUM_AVAILABLE:
        print("请先安装Selenium: pip install selenium webdriver-manager")
        return

    crawler = SeleniumCrawler(headless=True)

    try:
        isbn = "9780743273565"  # The Great Gatsby

        print("="*60)
        print("Selenium爬虫测试")
        print("="*60)

        # 测试AbeBooks
        print("\n--- AbeBooks ---")
        result = crawler.scrape_abebooks(isbn)
        if result:
            print(f"找到 {len(result['books'])} 本书")

        # 测试Amazon
        print("\n--- Amazon UK ---")
        result = crawler.scrape_amazon_uk(isbn)

    finally:
        crawler.close()


if __name__ == '__main__':
    test_selenium()
