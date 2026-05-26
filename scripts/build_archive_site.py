#!/usr/bin/env python3
"""构建 GitHub Pages 静态归档站（索引页 + 搜索索引）。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from convert_today import (  # noqa: E402
    ARCHIVE_DIR,
    build_search_index,
    generate_index_html,
    generate_robots_txt,
    generate_sitemap,
)


def main() -> int:
    if not ARCHIVE_DIR.exists():
        print(f'归档目录不存在: {ARCHIVE_DIR}', file=sys.stderr)
        return 1

    ok, urls = generate_index_html()
    if not ok:
        print('生成 archive/index.html 失败', file=sys.stderr)
        return 1

    if not build_search_index():
        print('生成 search-index.json 失败', file=sys.stderr)
        return 1

    generate_sitemap(urls, base_url='')
    generate_robots_txt(base_url='')

    nojekyll = ARCHIVE_DIR / '.nojekyll'
    nojekyll.touch(exist_ok=True)

    print(f'归档站构建完成: {ARCHIVE_DIR}')
    print(f'  - index.html')
    print(f'  - search-index.json')
    print(f'  - .nojekyll')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
