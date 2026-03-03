"""
代理池模块
"""
from .pool import ProxyPool, get_proxy_pool
from .config import ProxyConfig

__all__ = ['ProxyPool', 'get_proxy_pool', 'ProxyConfig']
