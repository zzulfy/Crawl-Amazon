#!/usr/bin/env python3
"""
调试测试程序 - 查看实际返回内容
"""
import requests
import re

TEST_ISBN = "9781845614652"

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


def test_amazon_debug(isbn):
    """调试 Amazon UK"""
    print("\n" + "="*60)
    print("测试 Amazon UK (调试模式)")
    print("="*60)

    # 尝试搜索页面
    search_url = f"https://www.amazon.co.uk/s?k={isbn}&i=stripbooks"
    print(f"搜索URL: {search_url}")

    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            # 保存HTML用于调试
            with open('/tmp/amazon_search.html', 'w', encoding='utf-8') as f:
                f.write(resp.text)
            print("已保存HTML到 /tmp/amazon_search.html")

            # 尝试多种方式提取书名
            # 方法1: 产品标题
            title_match = re.search(r'<span class="a-text-normal"[^>]*>([^<]{10,})</span>', resp.text)
            if title_match:
                print(f"✓ 书名(方法1): {title_match.group(1).strip()[:100]}")

            # 方法2: 搜索结果标题
            titles = re.findall(r'<h2[^>]*>.*?<a[^>]*>.*?<span[^>]*>([^<]{5,})</span>', resp.text, re.DOTALL)
            if titles:
                print(f"✓ 找到 {len(titles)} 个标题")
                for i, t in enumerate(titles[:3]):
                    print(f"   {i+1}. {t.strip()[:80]}")

            # 检查是否有结果
            if 'did not match any products' in resp.text:
                print("! 没有找到匹配的产品")

            # 查找产品链接
            links = re.findall(r'/dp/([A-Z0-9]{10})', resp.text)
            if links:
                print(f"✓ 找到产品ASIN: {links[0]}")
                # 访问产品页面
                asin = links[0]
                product_url = f"https://www.amazon.co.uk/dp/{asin}"
                print(f"\n访问产品页面: {product_url}")
                resp2 = requests.get(product_url, headers=HEADERS, timeout=15)
                if resp2.status_code == 200:
                    title_match = re.search(r'<span id="productTitle"[^>]*>([^<]+)</span>', resp2.text)
                    if title_match:
                        print(f"✓ 产品标题: {title_match.group(1).strip()}")

                    # 作者
                    author_match = re.search(r'class="contributorNameID"[^>]*>([^<]+)</a>', resp2.text)
                    if not author_match:
                        author_match = re.search(r'<span class="author[^"]*"[^>]*>\s*<a[^>]*>([^<]+)</a>', resp2.text)
                    if author_match:
                        print(f"✓ 作者: {author_match.group(1).strip()}")

                    # 价格
                    price_match = re.search(r'£[\d,.]+', resp2.text)
                    if price_match:
                        print(f"✓ 价格: {price_match.group()}")

        return True
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_abebooks_debug(isbn):
    """调试 AbeBooks UK"""
    print("\n" + "="*60)
    print("测试 AbeBooks UK (调试模式)")
    print("="*60)

    url = f"https://www.abebooks.co.uk/servlet/SearchResults?kn={isbn}&sts=t"
    print(f"URL: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            # 保存HTML
            with open('/tmp/abebooks.html', 'w', encoding='utf-8') as f:
                f.write(resp.text)
            print("已保存HTML到 /tmp/abebooks.html")

            # 提取结果
            # 方法1: 查找书籍链接和标题
            book_matches = re.findall(r'<a[^>]*href="/book-search/title/[^"]*"[^>]*>([^<]+)</a>', resp.text)
            if book_matches:
                print(f"✓ 找到 {len(book_matches)} 个书籍")
                for i, t in enumerate(book_matches[:3]):
                    print(f"   {i+1}. {t.strip()[:80]}")

            # 方法2: 价格
            prices = re.findall(r'£[\d,.]+', resp.text)
            if prices:
                print(f"✓ 价格示例: {prices[:5]}")

            # 方法3: 查找结果容器
            result_count = re.search(r'(\d+)\s*results?', resp.text, re.IGNORECASE)
            if result_count:
                print(f"✓ 搜索结果数: {result_count.group(1)}")

            # 检查是否没结果
            if 'did not match' in resp.text.lower() or '0 results' in resp.text.lower():
                print("! 没有找到结果")

        return True
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def test_goodreads_debug(isbn):
    """调试 Goodreads"""
    print("\n" + "="*60)
    print("测试 Goodreads (调试模式)")
    print("="*60)

    # Goodreads有时会阻止请求，尝试不同的URL
    urls = [
        f"https://www.goodreads.com/search?q={isbn}",
        f"https://www.goodreads.com/isbn/{isbn}",
    ]

    for url in urls:
        print(f"尝试: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            print(f"状态码: {resp.status_code}")

            if resp.status_code == 200:
                # 检查是否被重定向
                if resp.url != url:
                    print(f"重定向到: {resp.url}")

                # 提取书名
                title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', resp.text)
                if title_match:
                    print(f"✓ 书名: {title_match.group(1).strip()[:100]}")

                # 保存HTML
                with open('/tmp/goodreads.html', 'w', encoding='utf-8') as f:
                    f.write(resp.text)
                print("已保存HTML到 /tmp/goodreads.html")
                return True
            elif resp.status_code == 403:
                print("! 被阻止 (403 Forbidden)")
            elif resp.status_code == 500:
                print("! 服务器错误 (500)")

        except Exception as e:
            print(f"✗ 错误: {e}")

    return False


def main():
    print("="*60)
    print("调试测试程序")
    print(f"测试ISBN: {TEST_ISBN}")
    print("="*60)

    test_amazon_debug(TEST_ISBN)
    test_abebooks_debug(TEST_ISBN)
    test_goodreads_debug(TEST_ISBN)


if __name__ == '__main__':
    main()
