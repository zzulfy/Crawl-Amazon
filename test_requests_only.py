#!/usr/bin/env python3
"""
简化版爬虫测试 - 只使用requests（不需要bs4）
"""
import requests
import re
import json

# 测试ISBN
TEST_ISBN = "9781845614652"

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


def clean_text(text):
    """清理文本"""
    if not text:
        return None
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text else None


def scrape_goodreads(isbn):
    """爬取 Goodreads"""
    print("\n" + "="*60)
    print("Goodreads 爬虫")
    print("="*60)

    book = {
        'isbn': isbn,
        'source': 'goodreads',
        'title': None,
        'author': None,
        'cover_url': None,
        'pages': None,
        'publisher': None,
        'binding': None,
        'description': None,
    }

    # 尝试直接访问ISBN页面
    url = f"https://www.goodreads.com/isbn/{isbn}"
    print(f"URL: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            print(f"最终URL: {resp.url}")

            # 书名
            title_match = re.search(r'data-testid="bookTitle"[^>]*>([^<]+)<', resp.text)
            if not title_match:
                title_match = re.search(r'<h1[^>]*class="Text__title1"[^>]*>([^<]+)<', resp.text)
            if title_match:
                book['title'] = clean_text(title_match.group(1))
                print(f"✓ 书名: {book['title']}")

            # 作者
            author_match = re.search(r'class="ContributorLink"[^>]*>([^<]+)<', resp.text)
            if not author_match:
                author_match = re.search(r'class="authorName"[^>]*>([^<]+)<', resp.text)
            if author_match:
                book['author'] = clean_text(author_match.group(1))
                print(f"✓ 作者: {book['author']}")

            # 封面
            cover_match = re.search(r'<img[^>]*class="ResponsiveImage"[^>]*src="([^"]+)"', resp.text)
            if not cover_match:
                cover_match = re.search(r'id="coverImage"[^>]*src="([^"]+)"', resp.text)
            if cover_match:
                book['cover_url'] = cover_match.group(1)
                print(f"✓ 封面: {book['cover_url'][:60]}...")

            # 页数
            pages_match = re.search(r'(\d+)\s*pages', resp.text, re.IGNORECASE)
            if pages_match:
                book['pages'] = int(pages_match.group(1))
                print(f"✓ 页数: {book['pages']}")

            # 装帧
            if 'hardcover' in resp.text.lower():
                book['binding'] = '精装'
            elif 'paperback' in resp.text.lower():
                book['binding'] = '平装'
            if book['binding']:
                print(f"✓ 装帧: {book['binding']}")

            # 简介
            desc_match = re.search(r'data-testid="description"[^>]*>.*?<span[^>]*>([^<]{50,})', resp.text, re.DOTALL)
            if desc_match:
                book['description'] = clean_text(desc_match.group(1))[:200]
                print(f"✓ 简介: {book['description'][:100]}...")

            return book
        else:
            print(f"✗ 状态码: {resp.status_code}")
            return None

    except Exception as e:
        print(f"✗ 错误: {e}")
        return None


def scrape_abebooks(isbn):
    """爬取 AbeBooks UK"""
    print("\n" + "="*60)
    print("AbeBooks UK 爬虫")
    print("="*60)

    book = {
        'isbn': isbn,
        'source': 'abebooks',
        'title': None,
        'author': None,
        'used_price': None,
    }

    url = f"https://www.abebooks.co.uk/servlet/SearchResults?kn={isbn}&sts=t"
    print(f"URL: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            # 检查是否有结果
            if '0 results' in resp.text.lower() or 'did not match' in resp.text.lower():
                print("! 没有找到结果")
                return book

            # 提取价格
            prices = re.findall(r'£([\d,.]+)', resp.text)
            if prices:
                book['used_price'] = f"£{prices[0]}"
                print(f"✓ 二手书价格: {book['used_price']}")

            # 书名 - 从搜索结果提取
            title_match = re.search(r'<a[^>]*class="title"[^>]*>([^<]+)</a>', resp.text)
            if title_match:
                book['title'] = clean_text(title_match.group(1))
                print(f"✓ 书名: {book['title']}")

            return book
        else:
            print(f"✗ 状态码: {resp.status_code}")
            return None

    except Exception as e:
        print(f"✗ 错误: {e}")
        return None


def scrape_amazon_uk(isbn):
    """爬取 Amazon UK"""
    print("\n" + "="*60)
    print("Amazon UK 爬虫")
    print("="*60)

    book = {
        'isbn': isbn,
        'source': 'amazon_uk',
        'title': None,
        'author': None,
        'cover_url': None,
        'publisher': None,
        'binding': None,
        'pages': None,
        'price': None,
    }

    # 先搜索
    search_url = f"https://www.amazon.co.uk/s?k={isbn}&i=stripbooks"
    print(f"搜索URL: {search_url}")

    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        print(f"状态码: {resp.status_code}")

        if resp.status_code in [200, 202]:
            # 提取产品ASIN
            asin_match = re.search(r'/dp/([A-Z0-9]{10})', resp.text)
            if asin_match:
                asin = asin_match.group(1)
                product_url = f"https://www.amazon.co.uk/dp/{asin}"
                print(f"产品URL: {product_url}")

                # 获取产品页面
                resp2 = requests.get(product_url, headers=HEADERS, timeout=15)
                print(f"产品页状态码: {resp2.status_code}")

                if resp2.status_code == 200:
                    # 书名
                    title_match = re.search(r'id="productTitle"[^>]*>([^<]+)<', resp2.text)
                    if title_match:
                        book['title'] = clean_text(title_match.group(1))
                        print(f"✓ 书名: {book['title']}")

                    # 作者
                    author_match = re.search(r'class="contributorNameID"[^>]*>([^<]+)<', resp2.text)
                    if not author_match:
                        author_match = re.search(r'class="author"[^>]*>.*?<a[^>]*>([^<]+)<', resp2.text, re.DOTALL)
                    if author_match:
                        book['author'] = clean_text(author_match.group(1))
                        print(f"✓ 作者: {book['author']}")

                    # 封面
                    cover_match = re.search(r'id="landingImage"[^>]*src="([^"]+)"', resp2.text)
                    if cover_match:
                        book['cover_url'] = cover_match.group(1)
                        print(f"✓ 封面: {book['cover_url'][:60]}...")

                    # 价格
                    price_match = re.search(r'£([\d,.]+)', resp2.text)
                    if price_match:
                        book['price'] = f"£{price_match.group(1)}"
                        print(f"✓ 价格: {book['price']}")

                    # 产品详情
                    details = {}
                    # 提取详情表格
                    detail_matches = re.findall(r'<th[^>]*>([^<]+)</th>\s*<td[^>]*>([^<]+)</td>', resp2.text)
                    for key, value in detail_matches:
                        details[key.strip().lower()] = value.strip()

                    if 'publisher' in details:
                        book['publisher'] = details['publisher']
                        print(f"✓ 出版商: {book['publisher']}")

                    if 'print length' in details:
                        pages_match = re.search(r'(\d+)', details['print length'])
                        if pages_match:
                            book['pages'] = int(pages_match.group(1))
                            print(f"✓ 页数: {book['pages']}")

                    # 装帧
                    if 'hardcover' in resp2.text.lower():
                        book['binding'] = '精装'
                    elif 'paperback' in resp2.text.lower():
                        book['binding'] = '平装'
                    if book['binding']:
                        print(f"✓ 装帧: {book['binding']}")

                    return book
            else:
                print("! 未找到产品ASIN")

        print("✗ 无法获取产品信息")
        return None

    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("="*60)
    print("简化版爬虫测试")
    print(f"测试ISBN: {TEST_ISBN}")
    print("="*60)

    results = {}

    # 测试各网站
    results['goodreads'] = scrape_goodreads(TEST_ISBN)
    results['abebooks'] = scrape_abebooks(TEST_ISBN)
    results['amazon_uk'] = scrape_amazon_uk(TEST_ISBN)

    # 汇总结果
    print("\n" + "="*60)
    print("爬取结果汇总")
    print("="*60)

    for source, book in results.items():
        if book:
            print(f"\n{source.upper()}:")
            print(f"  书名: {book.get('title')}")
            print(f"  作者: {book.get('author')}")
            if book.get('pages'):
                print(f"  页数: {book.get('pages')}")
            if book.get('publisher'):
                print(f"  出版商: {book.get('publisher')}")
            if book.get('binding'):
                print(f"  装帧: {book.get('binding')}")
            if book.get('used_price') or book.get('price'):
                print(f"  价格: {book.get('used_price') or book.get('price')}")

    # 保存为JSON
    output_file = '/tmp/book_info.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({k: v for k, v in results.items() if v}, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    main()
