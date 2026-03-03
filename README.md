# 书籍信息爬虫

从 Goodreads、AbeBooks UK、Amazon UK 爬取书籍信息的 Python 程序。

## 功能特点

- 支持通过 ISBN 爬取三个网站的书籍信息
- 自动合并多来源数据，获取最完整的信息
- 支持普通模式和 Selenium 模式（可处理 JS 渲染页面）
- 记录所有数据来源 URL（`source_urls` 字段）
- 检测同码不同款的情况
- 自动下载封面图片
- 导出为 JSON、CSV、Excel 格式

## 爬取的信息

| 字段 | 说明 |
|------|------|
| isbn | ISBN 书号 |
| title | 书名 |
| author | 作者 |
| publisher | 出版商 |
| binding | 装帧（精装/平装） |
| pages | 页数 |
| dimensions | 尺寸 |
| weight | 重量 |
| description | 简介 |
| cover_url | 封面图片 URL |
| local_cover_path | 本地封面路径 |
| used_price_gb | 二手书价格（英镑） |
| source_urls | 数据来源 URL（goodreads, abebooks, amazon_uk） |

## 安装

```bash
# 克隆仓库
git clone https://github.com/zzulfy/Crawl-Amazon.git
cd Crawl-Amazon

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# Selenium 模式（可选，用于 JS 渲染页面）
pip install selenium

# Ubuntu/Debian 安装 Chromium（Selenium 模式需要）
sudo apt update && sudo apt install -y chromium-browser chromium-chromedriver
```

## 使用方法

### 普通模式

```bash
# 爬取单个 ISBN
python main.py 9781845614652

# 爬取多个 ISBN
python main.py 9781845614652 9780710507389

# 从文件读取 ISBN 列表
python main.py -f isbns.txt

# 指定输出目录
python main.py 9781845614652 -o my_output

# 跳过同码不同款检查
python main.py 9781845614652 --skip-edition-check

# 详细日志
python main.py 9781845614652 -v
```

### Selenium 模式（处理 JS 渲染页面）

```bash
# 使用 Selenium 模式
python main.py --selenium 9781845614652

# 显示浏览器窗口（调试用）
python main.py --selenium --no-headless 9781845614652

# 不下载封面图片
python main.py --selenium --no-cover 9781845614652
```

### ISBN 文件格式

`isbns.txt` 文件支持以下格式：

```
# 每行一个 ISBN
9781845614652
9780710507389

# 或逗号分隔
9781845614652,9780710507389
```

### 作为库使用

```python
from main import BookCrawler

crawler = BookCrawler(output_dir='output')

# 爬取单个 ISBN
book = crawler.crawl_single_isbn('9781845614652')
print(book.title, book.author)
print(book.source_urls)  # 数据来源

# 批量爬取
isbns = ['9781845614652', '9780710507389']
results = crawler.crawl_isbns(isbns)

# 保存结果
crawler.save_results(results)

crawler.close()
```

## 输出文件

程序会在输出目录生成以下文件：

```
output/
├── book_9781845614652.json    # JSON 格式结果
├── book_9781845614652.csv     # CSV 格式结果
├── book_9781845614652.xlsx    # Excel 格式结果
└── covers/
    └── 9781845614652.jpg      # 封面图片
```

### 输出示例

```json
{
  "9781845614652": {
    "isbn": "9781845614652",
    "title": "The Selfish Giant",
    "author": "Oscar Wilde",
    "publisher": "Floris Books",
    "binding": "平装",
    "pages": 32,
    "dimensions": "22.23 x 0.64 x 29.21 cm",
    "weight": "386 g",
    "description": "...",
    "cover_url": "https://...",
    "local_cover_path": "output/covers/9781845614652.jpg",
    "used_price_gb": null,
    "source_urls": {
      "goodreads": "https://www.goodreads.com/book/show/...",
      "abebooks": null,
      "amazon_uk": "https://www.amazon.co.uk/..."
    }
  }
}
```

## 数据来源说明

| 来源 | URL | 说明 |
|------|-----|------|
| Amazon UK | amazon.co.uk | 信息最全面，主要数据源 |
| Goodreads | goodreads.com | 补充评分、简介等信息 |
| AbeBooks | abebooks.co.uk | 二手书价格（需要 Selenium 模式） |

`source_urls` 字段会显示每个来源的 URL，如果该网站没有找到数据则显示 `null`。

## 代理配置

如需使用代理，编辑 `utils.py` 文件：

```python
PROXIES = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890',
}
```

## 注意事项

1. 请遵守网站的 robots.txt 和使用条款
2. 程序内置了延迟机制，避免请求过于频繁
3. 某些网站可能有反爬虫机制，如遇到问题可以：
   - 增加延迟时间
   - 使用代理
   - 使用 Selenium 模式

## 许可证

MIT License
