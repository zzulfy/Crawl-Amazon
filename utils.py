"""
工具函数模块
"""
import os
import re
import time
import random
import logging
from typing import Optional
from urllib.parse import urljoin, quote
import requests
from fake_useragent import UserAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建UserAgent实例
_ua = None

# 全局代理池实例
_proxy_pool = None


def get_user_agent() -> str:
    """获取随机User-Agent"""
    global _ua
    if _ua is None:
        try:
            _ua = UserAgent()
        except:
            _ua = None
    if _ua:
        try:
            return _ua.random
        except:
            pass
    # 备用User-Agent列表
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    ]
    return random.choice(user_agents)


def get_headers(referer: Optional[str] = None) -> dict:
    """获取请求头"""
    headers = {
        'User-Agent': get_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    if referer:
        headers['Referer'] = referer
    return headers


# ============================================
# 代理设置（如果需要翻墙访问，请取消注释并修改）
# ============================================
PROXIES = {
    # 'http': 'http://127.0.0.1:7890',
    # 'https': 'http://127.0.0.1:7890',
}

# 代理池配置（优先使用代理池）
PROXY_POOL_ENABLED = False


def init_proxy_pool(config=None):
    """初始化代理池"""
    global _proxy_pool, PROXY_POOL_ENABLED
    try:
        from proxy import ProxyPool, ProxyConfig
        if config is None:
            config = ProxyConfig(enabled=True)
        _proxy_pool = ProxyPool(config)
        if _proxy_pool.initialize():
            PROXY_POOL_ENABLED = True
            logger.info(f"代理池已启用: {_proxy_pool}")
        else:
            logger.warning("代理池初始化失败，将使用默认设置")
    except Exception as e:
        logger.warning(f"代理池初始化异常: {e}")


def get_proxies() -> Optional[dict]:
    """获取代理设置（优先使用代理池）"""
    global _proxy_pool, PROXY_POOL_ENABLED

    # 优先使用代理池
    if PROXY_POOL_ENABLED and _proxy_pool:
        proxies_dict = _proxy_pool.get_proxies_dict()
        if proxies_dict:
            return proxies_dict

    # 使用静态代理配置
    if PROXIES and any(PROXIES.values()):
        return PROXIES
    return None


def get_current_proxy():
    """获取当前使用的代理对象"""
    global _proxy_pool, PROXY_POOL_ENABLED
    if PROXY_POOL_ENABLED and _proxy_pool:
        return _proxy_pool.get_proxy()
    return None


def report_proxy_success(proxy, response_time: float = 0):
    """报告代理使用成功"""
    global _proxy_pool, PROXY_POOL_ENABLED
    if PROXY_POOL_ENABLED and _proxy_pool and proxy:
        _proxy_pool.report_success(proxy, response_time)


def report_proxy_failure(proxy, error: str = ""):
    """报告代理使用失败"""
    global _proxy_pool, PROXY_POOL_ENABLED
    if PROXY_POOL_ENABLED and _proxy_pool and proxy:
        _proxy_pool.report_failure(proxy, error)


def get_proxy_pool_stats():
    """获取代理池统计信息"""
    global _proxy_pool, PROXY_POOL_ENABLED
    if PROXY_POOL_ENABLED and _proxy_pool:
        return _proxy_pool.get_stats()
    return None


def clean_text(text: Optional[str]) -> Optional[str]:
    """清理文本（去除多余空格、换行等）"""
    if not text:
        return None
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 规范化空白字符
    text = re.sub(r'\s+', ' ', text)
    return text.strip() if text.strip() else None


def extract_isbn10(isbn: str) -> Optional[str]:
    """从字符串中提取ISBN-10"""
    # 移除所有非数字和X
    cleaned = re.sub(r'[^0-9Xx]', '', isbn)
    if len(cleaned) == 10:
        return cleaned.upper()
    elif len(cleaned) == 13:
        # ISBN-13转ISBN-10
        return isbn13_to_isbn10(cleaned)
    return None


def extract_isbn13(isbn: str) -> Optional[str]:
    """从字符串中提取ISBN-13"""
    cleaned = re.sub(r'[^0-9]', '', isbn)
    if len(cleaned) == 13:
        return cleaned
    elif len(cleaned) == 10:
        # ISBN-10转ISBN-13
        return isbn10_to_isbn13(cleaned)
    return None


def isbn10_to_isbn13(isbn10: str) -> str:
    """ISBN-10转换为ISBN-13"""
    isbn10 = re.sub(r'[^0-9Xx]', '', isbn10)
    if len(isbn10) != 10:
        return isbn10
    # ISBN-13前缀
    prefix = '978'
    base = prefix + isbn10[:9]
    # 计算校验位
    check = 0
    for i, digit in enumerate(base):
        check += int(digit) * (1 if i % 2 == 0 else 3)
    check = (10 - (check % 10)) % 10
    return base + str(check)


def isbn13_to_isbn10(isbn13: str) -> Optional[str]:
    """ISBN-13转换为ISBN-10"""
    isbn13 = re.sub(r'[^0-9]', '', isbn13)
    if len(isbn13) != 13 or not isbn13.startswith('978'):
        return None
    base = isbn13[3:12]
    # 计算校验位
    check = 0
    for i, digit in enumerate(base):
        check += int(digit) * (10 - i)
    check = 11 - (check % 11)
    if check == 10:
        check = 'X'
    elif check == 11:
        check = '0'
    else:
        check = str(check)
    return base + check


def parse_price(price_str: Optional[str]) -> Optional[float]:
    """解析价格字符串，返回浮点数"""
    if not price_str:
        return None
    # 匹配数字和小数点
    match = re.search(r'[\d,]+\.?\d*', price_str.replace(',', ''))
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def download_image(url: str, save_path: str, session: Optional[requests.Session] = None) -> bool:
    """下载图片到本地"""
    try:
        headers = get_headers()
        if session:
            response = session.get(url, headers=headers, timeout=30)
        else:
            response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"图片已保存: {save_path}")
        return True
    except Exception as e:
        logger.error(f"下载图片失败 {url}: {e}")
        return False


def random_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    """随机延迟"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


def create_session() -> requests.Session:
    """创建带有重试功能的Session"""
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        max_retries=3,
        pool_connections=10,
        pool_maxsize=10
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session
