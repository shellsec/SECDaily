import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
ARCHIVE_DIR = BASE_DIR / 'archive'


def generate_index_html():
    """生成索引页面（使用 convert_today 的美化模板）"""
    from convert_today import generate_index_html as generate_archive_index, build_search_index
    generate_archive_index()
    build_search_index()


def main():
    from convert_today import convert_md_to_html

    if len(sys.argv) > 1:
        md_file = Path(sys.argv[1])
        if not md_file.exists():
            print(f"错误: 文件 {md_file} 不存在")
            return

        print(f"开始转换指定Markdown文件: {md_file}")
        html_file = md_file.with_suffix('.html')
        convert_md_to_html(md_file, html_file)
        print(f"转换完成: {html_file}")
    else:
        print("开始转换所有Markdown文件为HTML...")

        for md_file in ARCHIVE_DIR.rglob('*.md'):
            if md_file.name.startswith('AISummary'):
                continue
            html_file = md_file.with_suffix('.html')
            print(f"转换: {md_file} -> {html_file}")
            convert_md_to_html(md_file, html_file)

        generate_index_html()
        print("索引文件已生成: archive/index.html")
        print("所有文件转换完成!")


if __name__ == '__main__':
    main()
