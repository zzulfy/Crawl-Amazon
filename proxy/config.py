"""
代理池配置
"""
import os
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ProxyConfig:
    """代理池配置"""
    # 是否启用代理
    enabled: bool = False

    # 代理文件路径
    proxy_file: str = "proxies.txt"

    # API 配置（付费代理服务）
    api_url: Optional[str] = None
    api_key: Optional[str] = None

    # 轮换策略: round_robin | random | failover
    strategy: str = "round_robin"

    # 失败切换配置
    fail_switch: bool = True
    max_fails: int = 3  # 连续失败次数后移除代理

    # 健康检查配置
    health_check_enabled: bool = True
    health_check_interval: int = 300  # 秒
    health_check_url: str = "https://httpbin.org/ip"
    health_check_timeout: int = 10

    # 请求超时
    request_timeout: int = 30

    # 重试配置
    max_retries: int = 3
    retry_delay: float = 5.0

    @classmethod
    def from_env(cls) -> 'ProxyConfig':
        """从环境变量加载配置"""
        return cls(
            enabled=os.getenv('PROXY_ENABLED', 'false').lower() == 'true',
            proxy_file=os.getenv('PROXY_FILE', 'proxies.txt'),
            api_url=os.getenv('PROXY_API_URL'),
            api_key=os.getenv('PROXY_API_KEY'),
            strategy=os.getenv('PROXY_STRATEGY', 'round_robin'),
            fail_switch=os.getenv('PROXY_FAIL_SWITCH', 'true').lower() == 'true',
            max_fails=int(os.getenv('PROXY_MAX_FAILS', '3')),
        )

    @classmethod
    def from_dict(cls, data: dict) -> 'ProxyConfig':
        """从字典加载配置"""
        return cls(
            enabled=data.get('enabled', False),
            proxy_file=data.get('proxy_file', 'proxies.txt'),
            api_url=data.get('api_url'),
            api_key=data.get('api_key'),
            strategy=data.get('strategy', 'round_robin'),
            fail_switch=data.get('fail_switch', True),
            max_fails=data.get('max_fails', 3),
            health_check_enabled=data.get('health_check', {}).get('enabled', True),
            health_check_interval=data.get('health_check', {}).get('interval', 300),
            health_check_url=data.get('health_check', {}).get('test_url', 'https://httpbin.org/ip'),
            health_check_timeout=data.get('health_check', {}).get('timeout', 10),
        )
