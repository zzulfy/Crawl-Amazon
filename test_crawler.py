#!/usr/bin/env python3
"""
爬虫测试程序
测试三个网站的爬虫是否能正常工作
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import BookInfo
from scrapers import GoodreadsScraper, AbeBooksScraper, AmazonUKScraper
from utils import logger


def test_scraper(scraper_class, name: str, isbn: str):
    """测试单个爬虫"""
    print(f"\n{'='*60}")
    print(f"测试 {name}")
    print(f"{'='*60}")

    scraper = scraper_class()
    try:
        book = scraper.search_by_isbn(isbn)
        if book:
            print(f"✓ 爬取成功!")
            print(f"  书名: {book.title}")
            print(f"  作者: {book.author}")
            print(f"  出版商: {book.publisher}")
            print(f"  装帧: {book.binding}")
            print(f"  页数: {book.pages}")
            print(f"  价格: {book.used_price_gb}")
            print(f"  封面: {book.cover_url[:50] + '...' if book.cover_url and len(book.cover_url) > 50 else book.cover_url}")
            print(f"  来源: {book.source_urls}")
            return True
        else:
            print(f"✗ 爬取失败 - 未找到书籍")
            return False
    except Exception as e:
        print(f"✗ 爬取出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        scraper.close()


def test_all():
    """测试所有爬虫"""
    # 测试用的ISBN
    test_isbn = "9781845614652"

    print(f"\n开始测试爬虫程序")
    print(f"测试ISBN: {test_isbn}")

    results = {}

    # 测试 Amazon UK
    results['Amazon UK'] = test_scraper(AmazonUKScraper, "Amazon UK", test_isbn)

    # 测试 Goodreads
    results['Goodreads'] = test_scraper(GoodreadsScraper, "Goodreads", test_isbn)

    # 测试 AbeBooks
    results['AbeBooks'] = test_scraper(AbeBooksScraper, "AbeBooks UK", test_isbn)

    # 汇总结果
    print(f"\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")
    for name, success in results.items():
        status = "✓ 成功" if success else "✗ 失败"
        print(f"  {name}: {status}")

    success_count = sum(results.values())
    print(f"\n总计: {success_count}/{len(results)} 成功")

    return all(results.values())


def test_single_site(site: str, isbn: str):
    """测试单个网站"""
    site = site.lower()

    if site in ['amazon', 'amazon_uk', 'amazon.co.uk']:
        return test_scraper(AmazonUKScraper, "Amazon UK", isbn)
    elif site in ['goodreads', 'goodreads.com']:
        return test_scraper(GoodreadsScraper, "Goodreads", isbn)
    elif site in ['abebooks', 'abebooks_uk', 'abebooks.co.uk']:
        return test_scraper(AbeBooksScraper, "AbeBooks UK", isbn)
    else:
        print(f"未知网站: {site}")
        print("支持的网站: amazon, goodreads, abebooks")
        return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='测试爬虫程序')
    parser.add_argument('isbn', nargs='?', default='9781845614652', help='要测试的ISBN')
    parser.add_argument('--site', '-s', help='只测试指定网站 (amazon/goodreads/abebooks)')

    args = parser.parse_args()

    if args.site:
        test_single_site(args.site, args.isbn)
    else:
        test_all()
