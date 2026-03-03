"""
代理池管理
支持文件加载、API获取、轮换策略、健康检查
"""
import os
import time
import random
import threading
import logging
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import requests

from .config import ProxyConfig

logger = logging.getLogger(__name__)


@dataclass
class ProxyItem:
    """代理项"""
    url: str  # 完整代理URL: http://user:pass@host:port
    protocol: str  # http, https, socks5
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None

    # 状态信息
    fail_count: int = 0
    success_count: int = 0
    last_used: Optional[datetime] = None
    last_check: Optional[datetime] = None
    is_alive: bool = True
    response_time: float = 0.0  # 响应时间(秒)

    def to_proxies_dict(self) -> Dict[str, str]:
        """转换为 requests 使用的 proxies 字典"""
        return {
            'http': self.url,
            'https': self.url,
        }

    def __str__(self):
        return f"{self.protocol}://{self.host}:{self.port}"


class ProxyPool:
    """代理池管理器"""

    def __init__(self, config: ProxyConfig = None):
        self.config = config or ProxyConfig()
        self.proxies: List[ProxyItem] = []
        self.current_index = 0
        self.lock = threading.Lock()
        self._initialized = False

        # 统计信息
        self.stats = {
            'total_requests': 0,
            'success_requests': 0,
            'failed_requests': 0,
            'proxy_rotations': 0,
        }

    def initialize(self) -> bool:
        """初始化代理池"""
        if self._initialized:
            return True

        logger.info("正在初始化代理池...")

        # 1. 从文件加载代理
        if os.path.exists(self.config.proxy_file):
            self._load_from_file(self.config.proxy_file)

        # 2. 从 API 获取代理
        if self.config.api_url:
            self._fetch_from_api()

        if not self.proxies:
            logger.warning("代理池为空！请配置代理文件或API")
            return False

        # 3. 健康检查
        if self.config.health_check_enabled:
            self._health_check_all()

        self._initialized = True
        logger.info(f"代理池初始化完成，有效代理: {len(self.get_alive_proxies())}/{len(self.proxies)}")
        return True

    def _load_from_file(self, filepath: str) -> int:
        """从文件加载代理"""
        count = 0
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # 跳过注释和空行
                    if not line or line.startswith('#'):
                        continue

                    proxy = self._parse_proxy_line(line)
                    if proxy:
                        self.proxies.append(proxy)
                        count += 1
                    else:
                        logger.warning(f"无法解析代理 (行 {line_num}): {line}")

            logger.info(f"从文件加载了 {count} 个代理")
        except Exception as e:
            logger.error(f"加载代理文件失败: {e}")

        return count

    def _parse_proxy_line(self, line: str) -> Optional[ProxyItem]:
        """解析代理行"""
        try:
            # 格式: protocol://user:pass@host:port 或 protocol://host:port
            from urllib.parse import urlparse
            parsed = urlparse(line)

            if not parsed.scheme or not parsed.hostname or not parsed.port:
                # 尝试简单格式: host:port
                if ':' in line and '://' not in line:
                    parts = line.split(':')
                    if len(parts) == 2:
                        return ProxyItem(
                            url=f"http://{line}",
                            protocol="http",
                            host=parts[0],
                            port=int(parts[1]),
                        )
                return None

            protocol = parsed.scheme
            host = parsed.hostname
            port = parsed.port
            username = parsed.username
            password = parsed.password

            return ProxyItem(
                url=line,
                protocol=protocol,
                host=host,
                port=port,
                username=username,
                password=password,
            )
        except Exception as e:
            logger.debug(f"解析代理失败: {line}, 错误: {e}")
            return None

    def _fetch_from_api(self) -> int:
        """从 API 获取代理"""
        if not self.config.api_url:
            return 0

        count = 0
        try:
            # 构建 API URL
            api_url = self.config.api_url
            if self.config.api_key:
                if '?' in api_url:
                    api_url += f"&key={self.config.api_key}"
                else:
                    api_url += f"?key={self.config.api_key}"

            logger.info(f"从 API 获取代理: {api_url}")
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # 解析 API 响应（需要根据具体 API 格式调整）
            proxies_data = self._parse_api_response(data)

            for proxy_data in proxies_data:
                proxy = self._parse_proxy_line(proxy_data)
                if proxy:
                    self.proxies.append(proxy)
                    count += 1

            logger.info(f"从 API 获取了 {count} 个代理")
        except Exception as e:
            logger.error(f"从 API 获取代理失败: {e}")

        return count

    def _parse_api_response(self, data) -> List[str]:
        """解析 API 响应，返回代理 URL 列表

        支持多种常见格式:
        1. ["http://ip:port", ...]
        2. {"data": [{"ip": "x.x.x.x", "port": 8080}, ...]}
        3. {"proxies": ["http://ip:port", ...]}
        """
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            # 尝试常见的字段名
            for key in ['data', 'proxies', 'proxy_list', 'list']:
                if key in data:
                    items = data[key]
                    if isinstance(items, list):
                        # 检查是否是字典格式
                        if items and isinstance(items[0], dict):
                            result = []
                            for item in items:
                                ip = item.get('ip') or item.get('host')
                                port = item.get('port')
                                protocol = item.get('protocol', 'http')
                                if ip and port:
                                    result.append(f"{protocol}://{ip}:{port}")
                            return result
                        return items

        return []

    def get_proxy(self) -> Optional[ProxyItem]:
        """获取一个代理"""
        if not self.config.enabled:
            return None

        if not self._initialized:
            self.initialize()

        alive_proxies = self.get_alive_proxies()
        if not alive_proxies:
            logger.warning("没有可用的代理")
            return None

        with self.lock:
            if self.config.strategy == 'random':
                proxy = random.choice(alive_proxies)
            else:  # round_robin
                proxy = alive_proxies[self.current_index % len(alive_proxies)]
                self.current_index += 1

            proxy.last_used = datetime.now()
            self.stats['proxy_rotations'] += 1

        logger.debug(f"使用代理: {proxy}")
        return proxy

    def get_proxies_dict(self) -> Optional[Dict[str, str]]:
        """获取代理字典（用于 requests）"""
        proxy = self.get_proxy()
        if proxy:
            return proxy.to_proxies_dict()
        return None

    def report_success(self, proxy: ProxyItem, response_time: float = 0):
        """报告代理使用成功"""
        with self.lock:
            proxy.fail_count = 0
            proxy.success_count += 1
            proxy.is_alive = True
            if response_time > 0:
                proxy.response_time = response_time
            self.stats['success_requests'] += 1
            self.stats['total_requests'] += 1

        logger.debug(f"代理成功: {proxy}")

    def report_failure(self, proxy: ProxyItem, error: str = ""):
        """报告代理使用失败"""
        with self.lock:
            proxy.fail_count += 1
            proxy.is_alive = proxy.fail_count < self.config.max_fails
            self.stats['failed_requests'] += 1
            self.stats['total_requests'] += 1

        logger.warning(f"代理失败 ({proxy.fail_count}/{self.config.max_fails}): {proxy}, 错误: {error}")

        if not proxy.is_alive:
            logger.warning(f"代理已禁用: {proxy}")

    def get_alive_proxies(self) -> List[ProxyItem]:
        """获取存活的代理列表"""
        return [p for p in self.proxies if p.is_alive]

    def _health_check_all(self):
        """对所有代理进行健康检查"""
        logger.info(f"开始健康检查 {len(self.proxies)} 个代理...")

        alive_count = 0
        for proxy in self.proxies:
            if self._check_proxy(proxy):
                alive_count += 1

        logger.info(f"健康检查完成，存活代理: {alive_count}/{len(self.proxies)}")

    def _check_proxy(self, proxy: ProxyItem) -> bool:
        """检查单个代理是否可用"""
        try:
            start_time = time.time()
            response = requests.get(
                self.config.health_check_url,
                proxies=proxy.to_proxies_dict(),
                timeout=self.config.health_check_timeout,
            )
            response_time = time.time() - start_time

            if response.status_code == 200:
                proxy.is_alive = True
                proxy.fail_count = 0
                proxy.response_time = response_time
                proxy.last_check = datetime.now()
                logger.debug(f"代理检查通过: {proxy} ({response_time:.2f}s)")
                return True
        except Exception as e:
            logger.debug(f"代理检查失败: {proxy}, 错误: {e}")

        proxy.is_alive = False
        proxy.last_check = datetime.now()
        return False

    def reload(self) -> bool:
        """重新加载代理池"""
        with self.lock:
            self.proxies.clear()
            self.current_index = 0
            self._initialized = False

        return self.initialize()

    def add_proxy(self, proxy_url: str) -> bool:
        """手动添加代理"""
        proxy = self._parse_proxy_line(proxy_url)
        if proxy:
            with self.lock:
                self.proxies.append(proxy)
            logger.info(f"添加代理: {proxy}")
            return True
        return False

    def remove_proxy(self, proxy_url: str) -> bool:
        """移除代理"""
        with self.lock:
            for i, proxy in enumerate(self.proxies):
                if proxy.url == proxy_url:
                    self.proxies.pop(i)
                    logger.info(f"移除代理: {proxy_url}")
                    return True
        return False

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            **self.stats,
            'total_proxies': len(self.proxies),
            'alive_proxies': len(self.get_alive_proxies()),
            'strategy': self.config.strategy,
        }

    def __len__(self):
        return len(self.proxies)

    def __str__(self):
        return f"ProxyPool(proxies={len(self.proxies)}, alive={len(self.get_alive_proxies())})"


# 全局代理池实例
_proxy_pool: Optional[ProxyPool] = None


def get_proxy_pool(config: ProxyConfig = None) -> ProxyPool:
    """获取全局代理池实例"""
    global _proxy_pool
    if _proxy_pool is None:
        _proxy_pool = ProxyPool(config)
    return _proxy_pool


def reset_proxy_pool():
    """重置全局代理池"""
    global _proxy_pool
    _proxy_pool = None
