#!/usr/bin/env python3
"""
书籍信息爬虫主程序
从 Goodreads, AbeBooks UK, Amazon UK 爬取书籍信息
"""
import os
import sys
import json
import argparse
import logging
from typing import List, Dict, Optional
from datetime import datetime

from models import BookInfo, ISBNRecord
from scrapers import GoodreadsScraper, AbeBooksScraper, AmazonUKScraper
from utils import download_image, random_delay, logger, isbn13_to_isbn10, isbn10_to_isbn13


class BookCrawler:
    """书籍信息爬虫"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.covers_dir = os.path.join(output_dir, "covers")

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.covers_dir, exist_ok=True)

        # 初始化爬虫
        self.goodreads = GoodreadsScraper()
        self.abebooks = AbeBooksScraper()
        self.amazon = AmazonUKScraper()

    def crawl_single_isbn(self, isbn: str) -> BookInfo:
        """爬取单个ISBN的书籍信息"""
        # 标准化ISBN
        isbn = isbn.replace('-', '').strip()
        logger.info(f"开始爬取 ISBN: {isbn}")

        book = BookInfo(isbn=isbn)

        # 1. 首先从Amazon获取（信息最全面）
        logger.info("正在从 Amazon UK 获取信息...")
        try:
            amazon_book = self.amazon.search_by_isbn(isbn)
            if amazon_book:
                book = book.merge(amazon_book)
            else:
                book.source_urls['amazon_uk'] = None
            random_delay(2, 4)
        except Exception as e:
            logger.error(f"Amazon UK 爬取失败: {e}")
            book.source_urls['amazon_uk'] = None

        # 2. 从Goodreads获取补充信息（始终调用以获取source_url）
        logger.info("正在从 Goodreads 获取信息...")
        try:
            gr_book = self.goodreads.search_by_isbn(isbn)
            if gr_book:
                book = book.merge(gr_book)
            else:
                book.source_urls['goodreads'] = None
            random_delay(2, 4)
        except Exception as e:
            logger.error(f"Goodreads 爬取失败: {e}")
            book.source_urls['goodreads'] = None

        # 3. 从AbeBooks获取二手书价格和补充信息
        logger.info("正在从 AbeBooks 获取信息...")
        try:
            abe_book = self.abebooks.search_by_isbn(isbn)
            if abe_book:
                # 如果没有价格，或者需要补充信息
                if abe_book.used_price_gb and not book.used_price_gb:
                    book.used_price_gb = abe_book.used_price_gb
                book = book.merge(abe_book)
            else:
                book.source_urls['abebooks'] = None
            random_delay(2, 4)
        except Exception as e:
            logger.error(f"AbeBooks 爬取失败: {e}")
            book.source_urls['abebooks'] = None

        # 下载封面图片
        if book.cover_url and not book.local_cover_path:
            cover_filename = f"{isbn}.jpg"
            cover_path = os.path.join(self.covers_dir, cover_filename)
            if download_image(book.cover_url, cover_path):
                book.local_cover_path = cover_path

        return book

    def check_multiple_editions(self, isbn: str) -> List[BookInfo]:
        """检查是否存在同码不同款的情况"""
        logger.info(f"检查 ISBN {isbn} 是否存在多个版本...")
        editions = []

        # 从Amazon检查多版本
        try:
            amazon_editions = self.amazon.check_multiple_editions(isbn)
            editions.extend(amazon_editions)
        except Exception as e:
            logger.error(f"检查Amazon多版本失败: {e}")

        return editions

    def crawl_isbns(self, isbns: List[str], skip_edition_check: bool = False) -> Dict[str, BookInfo]:
        """爬取多个ISBN的书籍信息"""
        results = {}

        for i, isbn in enumerate(isbns, 1):
            logger.info(f"进度: {i}/{len(isbns)}")

            # 检查同码不同款
            if not skip_edition_check:
                editions = self.check_multiple_editions(isbn)
                if len(editions) > 1:
                    logger.warning(f"警告: ISBN {isbn} 存在 {len(editions)} 个不同版本!")
                    for j, ed in enumerate(editions, 1):
                        logger.warning(f"  版本{j}: {ed.title} - {ed.binding}")

            # 爬取主要信息
            book = self.crawl_single_isbn(isbn)
            results[isbn] = book

            # 输出进度
            self._print_book_summary(book)

            # 礼貌延迟
            if i < len(isbns):
                random_delay(3, 5)

        return results

    def _print_book_summary(self, book: BookInfo):
        """打印书籍摘要"""
        print("\n" + "=" * 60)
        print(f"ISBN: {book.isbn}")
        print(f"书名: {book.title or '未知'}")
        print(f"作者: {book.author or '未知'}")
        print(f"出版商: {book.publisher or '未知'}")
        print(f"装帧: {book.binding or '未知'}")
        print(f"页数: {book.pages or '未知'}")
        print(f"二手价格: {book.used_price_gb or '未知'}")
        # 显示数据来源状态
        status_str = ", ".join([
            f"{k}: {'✓' if v else '✗'}"
            for k, v in book.source_urls.items()
        ])
        print(f"数据来源: {status_str}")
        print("=" * 60 + "\n")

    def save_results(self, results: Dict[str, BookInfo], filename: str = None):
        """保存结果到文件"""
        if filename is None:
            # 使用 ISBN 作为文件名
            isbns = list(results.keys())
            if len(isbns) == 1:
                filename = f"book_{isbns[0]}"
            else:
                # 多个ISBN时，用第一个 + 数量
                filename = f"book_{isbns[0]}_{len(isbns)}books"

        # 保存JSON
        json_path = os.path.join(self.output_dir, f"{filename}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            data = {isbn: book.to_dict() for isbn, book in results.items()}
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"结果已保存到: {json_path}")

        # 保存CSV格式
        csv_path = os.path.join(self.output_dir, f"{filename}.csv")
        self._save_csv(results, csv_path)

        # 保存Excel格式
        try:
            xlsx_path = os.path.join(self.output_dir, f"{filename}.xlsx")
            self._save_excel(results, xlsx_path)
        except Exception as e:
            logger.warning(f"保存Excel失败: {e}")

    def _save_csv(self, results: Dict[str, BookInfo], filepath: str):
        """保存为CSV"""
        import csv

        fieldnames = ['isbn', 'title', 'author', 'publisher', 'binding',
                      'pages', 'dimensions', 'weight', 'used_price_gb',
                      'cover_url', 'local_cover_path', 'description']

        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for isbn, book in results.items():
                row = book.to_dict()
                writer.writerow(row)

        logger.info(f"CSV已保存到: {filepath}")

    def _save_excel(self, results: Dict[str, BookInfo], filepath: str):
        """保存为Excel"""
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment

        wb = Workbook()
        ws = wb.active
        ws.title = "书籍信息"

        # 表头
        headers = ['ISBN', '书名', '作者', '出版商', '装帧', '页数',
                   '尺寸', '重量', '二手价格(英镑)', '封面URL', '本地封面', '简介']
        ws.append(headers)

        # 设置表头样式
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')

        # 数据行
        for isbn, book in results.items():
            row = [
                book.isbn,
                book.title,
                book.author,
                book.publisher,
                book.binding,
                book.pages,
                book.dimensions,
                book.weight,
                book.used_price_gb,
                book.cover_url,
                book.local_cover_path,
                book.description
            ]
            ws.append(row)

        # 调整列宽
        column_widths = [15, 40, 20, 25, 10, 8, 15, 10, 15, 50, 30, 60]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[chr(64 + i)].width = width

        wb.save(filepath)
        logger.info(f"Excel已保存到: {filepath}")

    def close(self):
        """关闭所有爬虫"""
        self.goodreads.close()
        self.abebooks.close()
        self.amazon.close()


def print_book_summary(book: BookInfo):
    """打印书籍摘要（独立函数）"""
    print("\n" + "=" * 60)
    print(f"ISBN: {book.isbn}")
    print(f"书名: {book.title or '未知'}")
    print(f"作者: {book.author or '未知'}")
    print(f"出版商: {book.publisher or '未知'}")
    print(f"装帧: {book.binding or '未知'}")
    print(f"页数: {book.pages or '未知'}")
    print(f"二手价格: {book.used_price_gb or '未知'}")
    # 显示数据来源状态
    status_str = ", ".join([
        f"{k}: {'✓' if v else '✗'}"
        for k, v in book.source_urls.items()
    ])
    print(f"数据来源: {status_str}")
    print("=" * 60 + "\n")


def load_isbns_from_file(filepath: str) -> List[str]:
    """从文件加载ISBN列表"""
    isbns = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 支持逗号分隔
            if ',' in line:
                isbns.extend([x.strip() for x in line.split(',') if x.strip()])
            elif line:
                isbns.append(line)
    return isbns


def main():
    parser = argparse.ArgumentParser(
        description='书籍信息爬虫 - 从Goodreads, AbeBooks, Amazon UK爬取书籍信息'
    )
    parser.add_argument(
        'isbns',
        nargs='*',
        help='要爬取的ISBN书号（可以是多个，空格分隔）'
    )
    parser.add_argument(
        '-f', '--file',
        help='从文件读取ISBN列表（每行一个，或逗号分隔）'
    )
    parser.add_argument(
        '-o', '--output',
        default='output',
        help='输出目录（默认: output）'
    )
    parser.add_argument(
        '--skip-edition-check',
        action='store_true',
        help='跳过同码不同款检查'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细日志'
    )
    parser.add_argument(
        '--selenium',
        action='store_true',
        help='使用Selenium模式（可处理JS渲染页面，需要安装selenium和chromium-browser）'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Selenium模式下显示浏览器窗口（默认无头模式）'
    )
    parser.add_argument(
        '--no-cover',
        action='store_true',
        help='不下载封面图片'
    )

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 收集ISBN
    isbns = list(args.isbns)
    if args.file:
        file_isbns = load_isbns_from_file(args.file)
        isbns.extend(file_isbns)

    if not isbns:
        parser.print_help()
        print("\n示例用法:")
        print("  python main.py 9781845614652 9780710507389")
        print("  python main.py -f isbns.txt")
        print("  python main.py 9781845614652 -o my_output")
        print("  python main.py --selenium 9781845614652")
        sys.exit(1)

    # 去重
    isbns = list(dict.fromkeys(isbns))
    print(f"\n准备爬取 {len(isbns)} 个ISBN:")
    for isbn in isbns:
        print(f"  - {isbn}")
    print()

    # Selenium 模式
    if args.selenium:
        try:
            from crawler_selenium import SeleniumCrawler, check_selenium_available

            if not check_selenium_available():
                print("错误: Selenium 未安装")
                print("请运行: pip install selenium")
                sys.exit(1)

            print("使用 Selenium 模式（可处理 JS 渲染页面）")
            selenium_crawler = SeleniumCrawler(headless=not args.no_headless)

            try:
                results = {}
                for i, isbn in enumerate(isbns, 1):
                    print(f"\n进度: {i}/{len(isbns)}")
                    book = selenium_crawler.scrape_all(isbn)
                    results[isbn] = book
                    print_book_summary(book)

                    if i < len(isbns):
                        random_delay(3, 5)

                # 保存结果
                crawler = BookCrawler(output_dir=args.output)
                crawler.save_results(results)
                print(f"\n爬取完成! 成功: {sum(1 for b in results.values() if b.title)}/{len(results)}")

            finally:
                selenium_crawler.close()

        except ImportError as e:
            print(f"错误: {e}")
            print("请运行: pip install selenium webdriver-manager")
            sys.exit(1)

    else:
        # 普通模式
        crawler = BookCrawler(output_dir=args.output)
        try:
            results = crawler.crawl_isbns(isbns, skip_edition_check=args.skip_edition_check)
            crawler.save_results(results)

            # 打印统计
            print("\n爬取完成!")
            print(f"成功: {sum(1 for b in results.values() if b.title)}/{len(results)}")

        except KeyboardInterrupt:
            print("\n用户中断，正在保存已爬取的数据...")
            if 'results' in locals():
                crawler.save_results(results)
        finally:
            crawler.close()


if __name__ == '__main__':
    main()
