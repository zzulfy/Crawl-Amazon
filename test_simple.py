#!/usr/bin/env python3
"""
简单测试程序 - 只使用requests测试网站访问
"""
import requests
import re

# 测试用的ISBN
TEST_ISBN = "9781845614652"

# 随机User-Agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# ============================================
# 代理设置（如果需要翻墙，请取消注释并修改端口）
# ============================================
PROXIES = {
    # 'http': 'http://127.0.0.1:7890',
    # 'https': 'http://127.0.0.1:7890',
}


def test_amazon(isbn):
    """测试 Amazon UK"""
    print("\n" + "="*60)
    print("测试 Amazon UK")
    print("="*60)

    url = f"https://www.amazon.co.uk/dp/{isbn}"
    print(f"URL: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, proxies=PROXIES if any(PROXIES.values()) else None, timeout=15)
        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            # 提取书名
            title_match = re.search(r'<span id="productTitle"[^>]*>([^<]+)</span>', resp.text)
            if title_match:
                print(f"✓ 书名: {title_match.group(1).strip()}")
            else:
                print("✗ 未找到书名")

            # 检查是否被重定向到搜索页
            if 's?k=' in resp.url or 'search' in resp.url.lower():
                print("! 被重定向到搜索页")

            # 提取作者
            author_match = re.search(r'<span class="author[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>', resp.text, re.DOTALL)
            if author_match:
                print(f"✓ 作者: {author_match.group(1).strip()}")

            return True
        elif resp.status_code == 404:
            print("✗ 页面不存在 (404)")
        elif resp.status_code == 503:
            print("✗ 服务不可用 (503) - 可能被反爬虫拦截")
        else:
            print(f"✗ 状态码: {resp.status_code}")

        return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def test_goodreads(isbn):
    """测试 Goodreads"""
    print("\n" + "="*60)
    print("测试 Goodreads")
    print("="*60)

    url = f"https://www.goodreads.com/search?q={isbn}"
    print(f"URL: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, proxies=PROXIES if any(PROXIES.values()) else None, timeout=15)
        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            # 提取书名
            title_match = re.search(r'<a[^>]*class="bookTitle"[^>]*>([^<]+)</a>', resp.text)
            if not title_match:
                title_match = re.search(r'<h1[^>]*data-testid="bookTitle"[^>]*>([^<]+)</h1>', resp.text)
            if title_match:
                print(f"✓ 书名: {title_match.group(1).strip()}")
            else:
                print("! 未在搜索结果中找到书名，尝试直接访问...")

                # 尝试直接访问ISBN页面
                direct_url = f"https://www.goodreads.com/isbn/{isbn}"
                resp2 = requests.get(direct_url, headers=HEADERS, proxies=PROXIES if any(PROXIES.values()) else None, timeout=15)
                if resp2.status_code == 200:
                    title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', resp2.text)
                    if title_match:
                        print(f"✓ 书名 (直接访问): {title_match.group(1).strip()}")

            return True
        else:
            print(f"✗ 状态码: {resp.status_code}")

        return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def test_abebooks(isbn):
    """测试 AbeBooks UK"""
    print("\n" + "="*60)
    print("测试 AbeBooks UK")
    print("="*60)

    url = f"https://www.abebooks.co.uk/servlet/SearchResults?kn={isbn}&sts=t"
    print(f"URL: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, proxies=PROXIES if any(PROXIES.values()) else None, timeout=15)
        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            # 提取书名
            title_match = re.search(r'<a[^>]*class="title"[^>]*>([^<]+)</a>', resp.text)
            if not title_match:
                title_match = re.search(r'<h3[^>]*>.*?<a[^>]*>([^<]+)</a>', resp.text, re.DOTALL)
            if title_match:
                print(f"✓ 书名: {title_match.group(1).strip()}")
            else:
                print("! 未找到书名")

            # 提取价格
            price_match = re.search(r'£[\d,.]+', resp.text)
            if price_match:
                print(f"✓ 价格: {price_match.group()}")

            return True
        else:
            print(f"✗ 状态码: {resp.status_code}")

        return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def main():
    print("="*60)
    print("简单爬虫测试")
    print(f"测试ISBN: {TEST_ISBN}")
    if any(PROXIES.values()):
        print(f"使用代理: {PROXIES}")
    print("="*60)

    results = {}

    # 测试各网站
    results['Amazon UK'] = test_amazon(TEST_ISBN)
    results['Goodreads'] = test_goodreads(TEST_ISBN)
    results['AbeBooks'] = test_abebooks(TEST_ISBN)

    # 汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    for name, success in results.items():
        status = "✓ 可访问" if success else "✗ 失败"
        print(f"  {name}: {status}")

    success_count = sum(results.values())
    print(f"\n总计: {success_count}/{len(results)} 成功")


if __name__ == '__main__':
    main()
