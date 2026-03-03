"""
爬虫模块
"""
from .goodreads import GoodreadsScraper
from .abebooks import AbeBooksScraper
from .amazon import AmazonUKScraper

__all__ = ['GoodreadsScraper', 'AbeBooksScraper', 'AmazonUKScraper']
