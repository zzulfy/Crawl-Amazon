# 书籍信息爬虫

从 Goodreads、AbeBooks UK、Amazon UK 爬取书籍信息的Python程序。

## 功能特点

- 支持通过ISBN爬取三个网站的书籍信息
- 自动合并多来源数据，获取最完整的信息
- 检测同码不同款的情况
- 自动下载封面图片
- 导出为JSON、CSV、Excel格式

## 爬取的信息

- 封面图片
- 书名
- 作者
- 出版者
- 装帧（精装/平装）
- 二手书售价
- 尺寸
- 重量
- 页码
- 简介

## 安装

```bash
# 创建虚拟环境（可选）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 命令行使用

```bash
# 爬取单个ISBN
python main.py 9781845614652

# 爬取多个ISBN
python main.py 9781845614652 9780710507389

# 从文件读取ISBN列表
python main.py -f isbns.txt

# 指定输出目录
python main.py 9781845614652 -o my_output

# 跳过同码不同款检查
python main.py 9781845614652 --skip-edition-check

# 详细日志
python main.py 9781845614652 -v
```

### ISBN文件格式

`isbns.txt` 文件支持以下格式：

```
# 每行一个ISBN
9781845614652
9780710507389

# 或逗号分隔
9781845614652,9780710507389
```

### 作为库使用

```python
from main import BookCrawler

crawler = BookCrawler(output_dir='output')

# 爬取单个ISBN
book = crawler.crawl_single_isbn('9781845614652')
print(book.title, book.author)

# 批量爬取
isbns = ['9781845614652', '9780710507389']
results = crawler.crawl_isbns(isbns)

# 保存结果
crawler.save_results(results)

crawler.close()
```

## 输出文件

程序会在输出目录生成以下文件：

- `books_YYYYMMDD_HHMMSS.json` - JSON格式结果
- `books_YYYYMMDD_HHMMSS.csv` - CSV格式结果
- `books_YYYYMMDD_HHMMSS.xlsx` - Excel格式结果
- `covers/` - 封面图片目录

## 注意事项

1. 请遵守网站的robots.txt和使用条款
2. 程序内置了延迟机制，避免请求过于频繁
3. 某些网站可能有反爬虫机制，如遇到问题可以：
   - 增加延迟时间
   - 使用代理
   - 降低请求频率

## 同码不同款说明

同一个ISBN可能对应多个不同版本的书籍（例如精装和平装版本）。程序会检测这种情况并给出警告。

示例：`9781845614652` 和 `9780710507389` 这两个ISBN可能存在同码不同款的情况。

## 许可证

MIT License
