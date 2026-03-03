"""
数据模型定义
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List
import json


@dataclass
class BookInfo:
    """书籍信息数据类"""
    isbn: str  # ISBN书号
    title: Optional[str] = None  # 书名
    author: Optional[str] = None  # 作者
    publisher: Optional[str] = None  # 出版者
    binding: Optional[str] = None  # 装帧（精装/平装）
    cover_url: Optional[str] = None  # 封面图片URL
    local_cover_path: Optional[str] = None  # 本地封面路径
    pages: Optional[int] = None  # 页码
    dimensions: Optional[str] = None  # 尺寸
    weight: Optional[str] = None  # 重量
    description: Optional[str] = None  # 简介
    used_price_gb: Optional[str] = None  # 二手书售价(英镑)
    used_price_cny: Optional[str] = None  # 二手书售价(人民币)
    source_urls: dict = field(default_factory=dict)  # 数据来源URL

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def is_complete(self) -> bool:
        """检查信息是否完整"""
        required_fields = ['title', 'author', 'publisher']
        return all(getattr(self, f) for f in required_fields)

    def merge(self, other: 'BookInfo') -> 'BookInfo':
        """合并另一个BookInfo的信息（用于多源数据合并）"""
        for key in self.to_dict():
            if not getattr(self, key) and getattr(other, key):
                setattr(self, key, getattr(other, key))
        # 合并来源URL
        self.source_urls.update(other.source_urls)
        return self


@dataclass
class ISBNRecord:
    """ISBN记录，用于处理同码不同款"""
    isbn: str
    editions: List[BookInfo] = field(default_factory=list)

    def add_edition(self, book: BookInfo):
        """添加一个版本"""
        self.editions.append(book)

    def has_multiple_editions(self) -> bool:
        """是否有多个版本（同码不同款）"""
        return len(self.editions) > 1

    def get_primary_edition(self) -> Optional[BookInfo]:
        """获取主要版本（信息最完整的）"""
        if not self.editions:
            return None
        return max(self.editions, key=lambda b: sum(1 for v in b.to_dict().values() if v))
