import os
import sys
import time
import json
import logging
import datetime
import re
import html as html_module
from pathlib import Path
import markdown
from jinja2 import Template

ARTICLE_LINK_RE = re.compile(r'^\s+-\s+\[(.+?)\]\((.+?)\)')
TOP_LEVEL_ITEM_RE = re.compile(r'^-\s+(.+)$')
SOURCE_H2_RE = re.compile(r'^##\s+(.+)$')

SITE_NAME = 'SECDaily'
SITE_TAGLINE = '每日安全资讯聚合与 AI 智能总结'
SITE_GITHUB_URL = 'https://github.com/shellsec/SECDaily'
DATE_MD_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
CVE_RE = re.compile(r'CVE-\d{4}-\d+', re.IGNORECASE)

# 导入HTML验证模块
try:
    from html_validator import validate_html_file
    HTML_VALIDATOR_AVAILABLE = True
    logging.info("HTML验证模块已加载")
except ImportError:
    HTML_VALIDATOR_AVAILABLE = False
    logging.warning("HTML验证模块未找到，将跳过HTML验证步骤")

# 配置路径
BASE_DIR = Path(__file__).parent
ARCHIVE_DIR = BASE_DIR / 'archive'
TEMPLATE_FILE = BASE_DIR / 'template.html'
INDEX_TEMPLATE_FILE = BASE_DIR / 'index_template.html'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "convert_today.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def ensure_template_exists():
    """确保模板文件存在，如果不存在则创建默认模板"""
    try:
        if TEMPLATE_FILE.exists():
            logger.info(f"模板文件已存在: {TEMPLATE_FILE}")
            return True
        
        logger.warning(f"模板文件不存在，将创建默认模板: {TEMPLATE_FILE}")
        
        # 创建一个基本的HTML模板
        default_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #2980b9;
            margin-top: 30px;
        }
        h3 {
            color: #3498db;
        }
        a {
            color: #2980b9;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .stats-line {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            margin: 20px 0;
            font-size: 0.9em;
            color: #666;
        }
        .stat-separator {
            margin: 0 10px;
        }
        footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #7f8c8d;
            font-size: 0.9em;
            text-align: center;
        }
        .archive-list {
            list-style-type: none;
            padding-left: 0;
        }
        .archive-list ul {
            padding-left: 20px;
        }
        .archive-list li {
            margin-bottom: 5px;
        }
        code {
            background-color: #f8f9fa;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: Consolas, Monaco, 'Andale Mono', monospace;
        }
        pre {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
        blockquote {
            border-left: 4px solid #3498db;
            padding-left: 15px;
            color: #555;
            margin-left: 0;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        img {
            max-width: 100%;
            height: auto;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
    </style>
</head>
<body>
    <header>
        <h1>{{ title }}</h1>
        <p>日期: {{ date }}</p>
    </header>
    
    <main>
        {{ content }}
    </main>
    
    <footer>
        <p>&copy; {{ year }} {{ site_name }}</p>
    </footer>
</body>
</html>
"""
        
        # 确保父目录存在
        TEMPLATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入默认模板
        with open(TEMPLATE_FILE, 'w', encoding='utf-8') as f:
            f.write(default_template)
        
        # 验证文件写入
        if not TEMPLATE_FILE.exists():
            error_msg = f"模板文件未成功创建: {TEMPLATE_FILE}"
            logger.error(error_msg)
            return False
            
        logger.info(f"成功创建默认模板文件: {TEMPLATE_FILE}")
        return True
        
    except Exception as e:
        logger.error(f"创建模板文件时出错: {e}")
        return False

def analyze_content(md_content):
    """分析Markdown内容生成统计数据"""
    try:
        logger.info("开始分析Markdown内容")
        
        if not md_content or not isinstance(md_content, str):
            logger.error(f"无效的内容格式: {type(md_content)}")
            return {
                'total_articles': 0,
                'sources': {'无效内容': 0},
                'keywords': {},
                'top_keywords': {'无效内容': 0},
                'tag_cloud': {'无效内容': 0}
            }
        
        lines = md_content.split('\n')
        stats = {
            'total_articles': 0,
            'sources': {},
            'keywords': {}
        }
        
        # 停用词列表和安全专业术语增强
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 
                     'were', 'be', 'been', 'being', 'in', 'on', 'at', 'to', 'for',
                     'of', 'by', 'with', 'about', 'from', 'as', 'into', 'like', 'through',
                     'after', 'over', 'between', 'out', 'against', 'during', 'without',
                     'before', 'under', 'around', 'among', '的', '了', '和', '与', '或',
                     '在', '是', '有', '被', '将', '把', '从', '对', '到', '为', '等',
                     'exploit', 'vulnerability', 'security', 'attack', 'remote', 'local'}
        
        # 安全相关关键词增强模式
        security_patterns = [
            r'CVE-\d{4}-\d+',  # CVE编号
            r'\b(?:SQLi|XSS|RCE|LFI|RFI|CSRF|SSRF)\b',  # 常见漏洞类型缩写
            r'\b(?:buffer overflow|privilege escalation|arbitrary code execution)\b',
            r'\b(?:windows|linux|wordpress|java|php|python)\b',  # 常见受影响产品
        ]
        
        current_source = ''
        try:
            import re
            line_count = len(lines)
            logger.info(f"开始处理 {line_count} 行内容")
            
            for i, line in enumerate(lines):
                try:
                    # 处理来源标题
                    if line.startswith('## '):
                        current_source = line[3:].strip()
                        if not current_source:
                            current_source = '未命名来源'
                        if current_source not in stats['sources']:
                            stats['sources'][current_source] = 0
                            logger.debug(f"发现新来源: {current_source}")
                    
                    # 处理文章链接 - 支持多种格式
                    elif line.strip().startswith('- '):
                        # 移除前导的- 和空格
                        article_line = line.strip()[2:].strip()
                        
                        # 检查是否是链接格式
                        if article_line.startswith('['):
                            stats['total_articles'] += 1
                            if current_source in stats['sources']:
                                stats['sources'][current_source] += 1
                            else:
                                # 如果没有明确的来源，使用默认来源
                                default_source = '未分类来源'
                                if default_source not in stats['sources']:
                                    stats['sources'][default_source] = 0
                                stats['sources'][default_source] += 1
                            
                            # 提取标题并分析关键词
                            try:
                                # 处理[title](url)格式
                                if '](' in article_line:
                                    title = article_line.split('](')[0][1:]
                                # 处理[title]格式
                                elif article_line.endswith(']'):
                                    title = article_line[1:-1]
                                else:
                                    title = article_line
                                
                                # 1. 提取显式TAG标记(格式: [TAG: xxx,yyy,zzz])
                                explicit_tags = []
                                if '[TAG:' in line:
                                    try:
                                        tag_part = line.split('[TAG:')[1].split(']')[0]
                                        explicit_tags = [t.strip().lower() for t in tag_part.split(',') if t.strip()]
                                        logger.debug(f"从文章中提取到显式标签: {explicit_tags}")
                                    except Exception as tag_err:
                                        logger.warning(f"提取TAG标记时出错: {tag_err}")
                                
                                # 2. 提取安全相关关键词
                                security_keywords = []
                                for pattern in security_patterns:
                                    try:
                                        matches = re.findall(pattern, title, re.IGNORECASE)
                                        security_keywords.extend(matches)
                                    except Exception as pattern_err:
                                        logger.warning(f"应用安全模式 '{pattern}' 时出错: {pattern_err}")
                                
                                if security_keywords:
                                    logger.debug(f"从文章中提取到安全关键词: {security_keywords}")
                                
                                # 3. 提取普通关键词
                                try:
                                    words = re.findall(r'\b\w+\b|[\u4e00-\u9fff]+', title.lower())
                                    filtered_words = [w for w in words if len(w) > 1 and w.lower() not in stop_words]
                                except Exception as word_err:
                                    logger.warning(f"提取普通关键词时出错: {word_err}")
                                    filtered_words = []
                                
                                # 合并所有关键词并统计
                                all_keywords = explicit_tags + security_keywords + filtered_words
                                
                                for word in all_keywords:
                                    if word and isinstance(word, str):
                                        word_lower = word.lower()
                                        stats['keywords'][word_lower] = stats['keywords'].get(word_lower, 0) + 1
                            
                            except Exception as e:
                                logger.error(f"处理文章标题和关键词时出错 (行 {i+1}): {e}")
                        # 处理普通文本格式
                        else:
                            stats['total_articles'] += 1
                            if current_source in stats['sources']:
                                stats['sources'][current_source] += 1
                            else:
                                # 如果没有明确的来源，使用默认来源
                                default_source = '未分类来源'
                                if default_source not in stats['sources']:
                                    stats['sources'][default_source] = 0
                                stats['sources'][default_source] += 1
                
                except Exception as line_err:
                    logger.warning(f"处理第 {i+1} 行时出错: {line_err}")
                    continue
            
            logger.info(f"内容处理完成，共找到 {stats['total_articles']} 篇文章，{len(stats['sources'])} 个来源")
            
            # 获取Top 5关键词（用于图表）
            try:
                if stats['keywords']:
                    top_keywords = sorted(stats['keywords'].items(), key=lambda x: x[1], reverse=True)[:5]
                    stats['top_keywords'] = dict(top_keywords)
                    logger.info(f"提取了 {len(stats['keywords'])} 个关键词，Top 5: {list(stats['top_keywords'].keys())}")
                    
                    # 获取Top 30关键词（用于标签云）
                    tag_cloud_keywords = sorted(stats['keywords'].items(), key=lambda x: x[1], reverse=True)[:30]
                    stats['tag_cloud'] = dict(tag_cloud_keywords)
                    logger.info(f"提取了 {len(stats['tag_cloud'])} 个标签云关键词")
                else:
                    stats['top_keywords'] = {'无关键词': 0}
                    stats['tag_cloud'] = {'无关键词': 0}
                    logger.warning("未能提取到任何关键词")
            except Exception as sort_err:
                logger.error(f"排序关键词时出错: {sort_err}")
                stats['top_keywords'] = {'排序错误': 0}
                stats['tag_cloud'] = {'排序错误': 0}
            
            # 确保至少有一个来源和关键词
            if not stats['sources']:
                stats['sources'] = {'未知来源': 0}
                logger.warning("未能识别任何来源")
            if not stats['top_keywords']:
                stats['top_keywords'] = {'无关键词': 0}
                logger.warning("未能提取任何关键词")
                
        except Exception as process_err:
            logger.error(f"处理内容时出错: {process_err}")
            stats = {
                'total_articles': 0,
                'sources': {'处理错误': 0},
                'keywords': {},
                'top_keywords': {'处理错误': 0},
                'tag_cloud': {'处理错误': 0}
            }
        
        return stats
            
    except Exception as e:
        logger.error(f"内容分析过程中发生严重错误: {e}")
        return {
            'total_articles': 0,
            'sources': {'分析错误': 0},
            'keywords': {},
            'top_keywords': {'分析错误': 0},
            'tag_cloud': {'分析错误': 0}
        }

def convert_md_to_html(md_file, html_file):
    """转换单个Markdown文件为HTML"""
    try:
        logger.info(f"开始转换文件: {md_file} -> {html_file}")
        
        # 检查模板文件是否存在
        if not TEMPLATE_FILE.exists():
            error_msg = f"模板文件不存在: {TEMPLATE_FILE}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # 读取Markdown文件
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            logger.info(f"成功读取Markdown文件: {md_file}")
        except Exception as e:
            logger.error(f"读取Markdown文件失败: {e}")
            raise
        
        # 提取资讯日期与页面标题
        report_date = md_file.stem
        if DATE_MD_RE.match(report_date):
            title = f'每日安全资讯（{report_date}）'
        else:
            title = report_date
        generated_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 结构化解析并生成统计
        try:
            sources = parse_md_sources(md_content)
            stats = compute_stats_from_sources(sources)
            logger.info(
                f"内容分析完成，共 {stats['total_articles']} 篇文章，"
                f"{stats['total_sources']} 个来源，{stats['cve_count']} 条 CVE"
            )
        except Exception as e:
            logger.error(f"内容分析失败: {e}")
            sources = []
            stats = {
                'total_articles': 0,
                'total_sources': 0,
                'cve_count': 0,
                'sources': {},
                'keywords': {},
                'top_keywords': {},
                'tag_cloud': {},
            }

        tag_cloud = build_tag_cloud(stats.get('tag_cloud', {}))

        stats_html = f'''<div class="stats-line">
    <span>{stats['total_articles']} 篇文章</span>
    <span class="stat-separator">|</span>
    <span>{stats['total_sources']} 个来源</span>
    <span class="stat-separator">|</span>
    <span>{stats['cve_count']} 条 CVE</span>
    <span class="stat-separator">|</span>
    <span>页面更新: {generated_at}</span>
</div>'''

        try:
            html_content = render_structured_html(sources)
            logger.info("结构化 HTML 渲染成功")
        except Exception as e:
            logger.error(f"结构化 HTML 渲染失败: {e}")
            html_content = f"<p>内容渲染失败: {html_module.escape(str(e))}</p>"
        
        # 尝试加载AI总结（需要先检查是否启用）
        ai_summary_html = None
        try:
            # 检查是否启用AI总结功能
            ai_enabled = False
            try:
                config_path = BASE_DIR / 'config.json'
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        ai_enabled = config.get('AISummary', {}).get('enabled', False)
                        logger.info(f"AI总结功能状态: {'启用' if ai_enabled else '禁用'}")
            except Exception as e:
                logger.warning(f"读取配置文件失败: {e}")
                # 如果读取失败，默认不启用
            
            # 只有在启用的情况下才加载AI总结
            if ai_enabled:
                # 从文件名提取日期 (格式: YYYY-MM-DD.md)
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', md_file.name)
                if date_match:
                    date_str = date_match.group(1)
                    # 查找对应的AISummary文件
                    summary_file = md_file.parent / f'AISummary{date_str}.md'
                    
                    if summary_file.exists():
                        logger.info(f"找到AI总结文件: {summary_file}")
                        with open(summary_file, 'r', encoding='utf-8') as f:
                            summary_content = f.read()
                        
                        # 跳过标题行,提取总结内容
                        lines = summary_content.split('\n')
                        # 找到第一个---分隔符后的内容
                        start_idx = 0
                        for i, line in enumerate(lines):
                            if line.strip() == '---':
                                start_idx = i + 1
                                break
                        
                        # 提取总结内容部分
                        summary_text = '\n'.join(lines[start_idx:]).strip()
                        
                        if summary_text:
                            # 将Markdown转换为HTML
                            ai_summary_html = markdown.markdown(summary_text)
                            logger.info("AI总结内容已加载并转换为HTML")
                        else:
                            logger.warning("AI总结文件存在但内容为空")
                    else:
                        logger.info(f"未找到AI总结文件: {summary_file}")
                else:
                    logger.warning(f"无法从文件名提取日期: {md_file.name}")
            else:
                logger.info("AI总结功能未启用，跳过加载AI总结")
        except Exception as e:
            logger.warning(f"加载AI总结时出错: {e}")
            # AI总结加载失败不影响主流程
            ai_summary_html = None
        
        # 使用模板渲染
        try:
            with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                template_content = f.read()
            template = Template(template_content)
            
            full_html = template.render(
                title=title,
                report_date=report_date,
                generated_at=generated_at,
                total_articles=stats['total_articles'],
                total_sources=stats['total_sources'],
                cve_count=stats['cve_count'],
                content=stats_html + html_content,
                ai_summary=ai_summary_html,
                tag_cloud=tag_cloud,
                year=datetime.datetime.now().year,
                site_name=SITE_NAME,
                site_tagline=SITE_TAGLINE,
                github_url=SITE_GITHUB_URL,
            )
            logger.info("模板渲染成功")
        except Exception as e:
            logger.error(f"模板渲染失败: {e}")
            # 创建一个简单的HTML作为备用
            full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
</head>
<body>
    <h1>{title}</h1>
    <p>资讯日期: {report_date}</p>
    <p>页面更新: {generated_at}</p>
    {stats_html}
    {html_content}
    <footer>
        <p>&copy; {datetime.datetime.now().year} {SITE_NAME}</p>
    </footer>
</body>
</html>"""
        
        # 确保目录存在
        try:
            html_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"确保目录存在: {html_file.parent}")
        except Exception as e:
            logger.error(f"创建目录失败: {e}")
            raise
        
        # 写入HTML文件并验证
        try:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(full_html)
            
            # 验证文件写入
            if not html_file.exists():
                error_msg = f"文件未成功创建: {html_file}"
                logger.error(error_msg)
                raise IOError(error_msg)
                
            with open(html_file, 'r', encoding='utf-8') as f:
                written_content = f.read()
            if len(written_content) < 100:  # 简单检查文件内容是否太短
                error_msg = f"文件内容可能不完整: {html_file}"
                logger.warning(error_msg)
            
            logger.info(f"成功写入HTML文件: {html_file}")
            return True
        except Exception as e:
            logger.error(f"写入HTML文件失败: {e}")
            raise
            
    except Exception as e:
        logger.error(f"转换过程中发生错误: {e}")
        return False

def find_today_file():
    """查找当天的Markdown文件，如果不存在则尝试查找最近的文件"""
    try:
        today = datetime.datetime.now()
        year_dir = ARCHIVE_DIR / str(today.year)
        today_str = today.strftime('%Y-%m-%d')
        
        logger.info(f"开始查找日期为 {today_str} 的文件")
        
        # 检查年份目录是否存在，如果不存在则创建
        try:
            if not year_dir.exists():
                logger.info(f"未找到当年目录，创建: {year_dir}")
                year_dir.mkdir(parents=True, exist_ok=True)
            else:
                logger.info(f"当年目录已存在: {year_dir}")
        except Exception as e:
            logger.error(f"创建年份目录时出错: {e}")
            raise
        
        md_file = year_dir / f"{today_str}.md"
        
        # 检查当天文件是否存在且有效
        if md_file.exists():
            try:
                # 验证文件是否可读且不为空
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if content:
                    logger.info(f"找到当天的有效文件: {md_file}")
                    return md_file
                else:
                    logger.warning(f"当天的文件存在但为空: {md_file}")
            except Exception as e:
                logger.error(f"读取当天文件时出错: {e}")
        else:
            logger.info(f"未找到当天的文件: {md_file}")
        
        # 尝试查找最近的文件（最多往前查找7天）
        logger.info("开始查找最近7天内的文件...")
        
        for i in range(1, 8):
            try:
                prev_date = today - datetime.timedelta(days=i)
                prev_year_dir = ARCHIVE_DIR / str(prev_date.year)
                prev_date_str = prev_date.strftime('%Y-%m-%d')
                
                # 如果跨年，检查并创建新的年份目录
                if not prev_year_dir.exists():
                    logger.info(f"跨年检查 - 创建年份目录: {prev_year_dir}")
                    prev_year_dir.mkdir(parents=True, exist_ok=True)
                
                prev_md_file = prev_year_dir / f"{prev_date_str}.md"
                
                if prev_md_file.exists():
                    try:
                        # 验证文件是否可读且不为空
                        with open(prev_md_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        if content:
                            logger.info(f"找到最近的有效文件: {prev_md_file} ({i}天前)")
                            return prev_md_file
                        else:
                            logger.warning(f"找到的文件为空: {prev_md_file}")
                    except Exception as e:
                        logger.error(f"读取文件时出错: {prev_md_file} - {e}")
                        continue
                else:
                    logger.debug(f"未找到{i}天前的文件: {prev_md_file}")
            
            except Exception as e:
                logger.error(f"查找{i}天前的文件时出错: {e}")
                continue
        
        logger.warning("未找到最近7天内的任何有效Markdown文件")
        return None
        
    except Exception as e:
        logger.error(f"查找文件过程中发生严重错误: {e}")
        return None

def parse_md_sources(md_content):
    """将 Markdown 日报解析为按来源分组的有序结构"""
    sources = []
    current_source = None

    def append_article(title, url):
        nonlocal current_source
        if not title or not url:
            return
        if current_source is None:
            current_source = {'name': '未分类', 'articles': []}
            sources.append(current_source)
        current_source['articles'].append({
            'title': title.strip(),
            'url': url.strip(),
            'has_cve': bool(CVE_RE.search(title)),
        })

    for line in md_content.split('\n'):
        if line.startswith('# '):
            continue

        h2_match = SOURCE_H2_RE.match(line)
        if h2_match:
            name = h2_match.group(1).strip() or '未命名来源'
            current_source = {'name': name, 'articles': []}
            sources.append(current_source)
            continue

        if line.startswith('  - '):
            article_match = ARTICLE_LINK_RE.match(line)
            if article_match:
                append_article(article_match.group(1), article_match.group(2))
            continue

        top_match = TOP_LEVEL_ITEM_RE.match(line)
        if top_match and not line.startswith('  '):
            content = top_match.group(1).strip()
            if content.startswith('[') and '](' in content:
                append_article(content.split('](')[0][1:], content.split('](')[1].rstrip(')'))
            elif content:
                current_source = {'name': content, 'articles': []}
                sources.append(current_source)

    return sources


def compute_stats_from_sources(sources):
    """基于结构化来源数据生成统计与标签云"""
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'in', 'on', 'at', 'to', 'for', 'of', 'by', 'with', 'about', 'from', 'as', 'into', 'like',
        'through', 'after', 'over', 'between', 'out', 'against', 'during', 'without', 'before',
        'under', 'around', 'among', '的', '了', '和', '与', '或', '在', '是', '有', '被', '将',
        '把', '从', '对', '到', '为', '等', 'exploit', 'vulnerability', 'security', 'attack',
        'remote', 'local',
    }
    security_patterns = [
        r'CVE-\d{4}-\d+',
        r'\b(?:SQLi|XSS|RCE|LFI|RFI|CSRF|SSRF)\b',
        r'\b(?:buffer overflow|privilege escalation|arbitrary code execution)\b',
        r'\b(?:windows|linux|wordpress|java|php|python)\b',
    ]

    stats = {
        'total_articles': 0,
        'total_sources': len(sources),
        'cve_count': 0,
        'sources': {},
        'keywords': {},
    }

    for source in sources:
        name = source['name']
        stats['sources'][name] = len(source['articles'])
        for article in source['articles']:
            stats['total_articles'] += 1
            if article.get('has_cve'):
                stats['cve_count'] += 1

            title = article['title']
            security_keywords = []
            for pattern in security_patterns:
                security_keywords.extend(re.findall(pattern, title, re.IGNORECASE))

            words = re.findall(r'\b\w+\b|[\u4e00-\u9fff]+', title.lower())
            filtered_words = [w for w in words if len(w) > 1 and w.lower() not in stop_words]

            for word in security_keywords + filtered_words:
                if word:
                    key = word.lower()
                    stats['keywords'][key] = stats['keywords'].get(key, 0) + 1

    if stats['keywords']:
        top_keywords = sorted(stats['keywords'].items(), key=lambda x: x[1], reverse=True)[:5]
        stats['top_keywords'] = dict(top_keywords)
        tag_cloud_keywords = sorted(stats['keywords'].items(), key=lambda x: x[1], reverse=True)[:30]
        stats['tag_cloud'] = dict(tag_cloud_keywords)
    else:
        stats['top_keywords'] = {}
        stats['tag_cloud'] = {}

    return stats


def source_section_id(index, name):
    slug = re.sub(r'[^\w\u4e00-\u9fff-]+', '-', name.strip()).strip('-')[:40]
    return f'source-{index}-{slug}' if slug else f'source-{index}'


def render_structured_html(sources):
    """将来源分组数据渲染为带 h2 目录的结构化 HTML"""
    if not sources:
        return '<p class="daily-empty">今日暂无安全资讯更新</p>'

    parts = ['<div class="daily-feed" id="dailyFeed">']
    for index, source in enumerate(sources):
        section_id = source_section_id(index, source['name'])
        safe_name = html_module.escape(source['name'])
        count = len(source['articles'])
        parts.append(
            f'<section class="source-section" data-source="{safe_name}" id="{section_id}">'
        )
        parts.append(
            f'<h2>{safe_name} <span class="source-count">{count}</span></h2>'
        )
        parts.append('<ul class="article-list">')
        for article in source['articles']:
            safe_title = html_module.escape(article['title'])
            safe_url = html_module.escape(article['url'], quote=True)
            title_attr = html_module.escape(article['title'], quote=True)
            source_attr = html_module.escape(source['name'], quote=True)
            cve_badge = '<span class="cve-badge">CVE</span> ' if article.get('has_cve') else ''
            search_text = html_module.escape(article['title'].lower())
            cve_flag = 'true' if article.get('has_cve') else 'false'
            parts.append(
                f'<li class="article-item{" is-cve" if article.get("has_cve") else ""}" '
                f'data-title="{search_text}">'
                f'<a class="article-link" href="{safe_url}" target="_blank" rel="noopener noreferrer">'
                f'{cve_badge}{safe_title}</a>'
                f'<span class="item-ai-jump">'
                f'<button type="button" class="item-ai-btn item-ai-chatgpt" data-ai="chatgpt" '
                f'data-article-title="{title_attr}" data-article-url="{safe_url}" '
                f'data-article-source="{source_attr}" data-article-cve="{cve_flag}" '
                f'aria-label="用 ChatGPT 分析此条">ChatGPT</button>'
                f'<button type="button" class="item-ai-btn item-ai-gemini" data-ai="gemini" '
                f'data-article-title="{title_attr}" data-article-url="{safe_url}" '
                f'data-article-source="{source_attr}" data-article-cve="{cve_flag}" '
                f'aria-label="用 Gemini 分析此条">Gemini</button>'
                f'<button type="button" class="item-ai-btn item-ai-deepseek" data-ai="deepseek" '
                f'data-article-title="{title_attr}" data-article-url="{safe_url}" '
                f'data-article-source="{source_attr}" data-article-cve="{cve_flag}" '
                f'aria-label="用 DeepSeek 分析此条">DeepSeek</button>'
                f'</span></li>'
            )
        parts.append('</ul></section>')
    parts.append('</div>')
    return '\n'.join(parts)


def build_tag_cloud(tag_cloud_raw):
    """将关键词频次映射为标签云尺寸"""
    tag_cloud = []
    if not tag_cloud_raw:
        return tag_cloud

    max_count = max(tag_cloud_raw.values())
    min_count = min(tag_cloud_raw.values())
    range_count = max_count - min_count if max_count > min_count else 1

    for keyword, count in tag_cloud_raw.items():
        if range_count > 0:
            normalized = int(((count - min_count) / range_count) * 5 + 1)
        else:
            normalized = 3
        normalized = max(1, min(6, normalized))
        tag_cloud.append({
            'keyword': keyword,
            'count': count,
            'size': normalized,
        })
    return tag_cloud


def parse_md_articles(md_content, date_str, page_path):
    """从 Markdown 日报中解析文章标题、来源与链接"""
    articles = []
    page = page_path.replace('\\', '/')
    for source in parse_md_sources(md_content):
        for article in source['articles']:
            articles.append({
                'title': article['title'],
                'url': article['url'],
                'source': source['name'],
                'date': date_str,
                'page': page,
            })
    return articles


def build_search_index():
    """扫描归档 Markdown，生成全站标题搜索索引"""
    try:
        logger.info('开始生成全站标题搜索索引')
        if not ARCHIVE_DIR.exists():
            logger.warning(f'归档目录不存在: {ARCHIVE_DIR}')
            return False

        index_entries = []
        for md_file in sorted(ARCHIVE_DIR.rglob('*.md')):
            if md_file.name.startswith('AISummary'):
                continue

            date_str = md_file.stem
            if not DATE_MD_RE.match(date_str):
                continue

            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    md_content = f.read()
            except Exception as e:
                logger.warning(f'读取 Markdown 失败，跳过: {md_file} - {e}')
                continue

            rel_page = md_file.with_suffix('.html').relative_to(ARCHIVE_DIR).as_posix()
            index_entries.extend(parse_md_articles(md_content, date_str, rel_page))

        index_entries.sort(key=lambda item: (item['date'], item['title']), reverse=True)

        index_file = ARCHIVE_DIR / 'search-index.json'
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump({
                'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total': len(index_entries),
                'articles': index_entries,
            }, f, ensure_ascii=False, indent=2)

        logger.info(f'搜索索引生成完成: {index_file}，共 {len(index_entries)} 条')
        return True
    except Exception as e:
        logger.error(f'生成搜索索引失败: {e}')
        return False


def generate_index_html():
    """生成美化的索引页面"""
    try:
        logger.info("开始生成归档索引页面")
        
        # 确保归档目录存在
        if not ARCHIVE_DIR.exists():
            logger.warning(f"归档目录不存在，创建目录: {ARCHIVE_DIR}")
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        
        # 获取所有年份目录
        try:
            years = sorted([d.name for d in ARCHIVE_DIR.iterdir() if d.is_dir()], reverse=True)
            logger.info(f"找到 {len(years)} 个年份目录")
            
            if not years:
                logger.warning("未找到任何年份目录")
                years = [str(datetime.datetime.now().year)]
        except Exception as e:
            logger.error(f"扫描年份目录时出错: {e}")
            years = [str(datetime.datetime.now().year)]
        
        # 生成索引内容
        try:
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            index_content = ""
            total_files = 0
            all_urls = []  # 用于生成sitemap
            all_articles = []  # 用于最近 N 天快捷入口
            recent_days = []
            
            for year in years:
                year_dir = ARCHIVE_DIR / year
                if not year_dir.exists():
                    logger.warning(f"年份目录不存在: {year_dir}")
                    year_dir.mkdir(parents=True, exist_ok=True)
                    continue
                
                try:
                    all_md_files = year_dir.glob('*.md')
                    md_files = sorted([f for f in all_md_files if not f.name.startswith('AISummary')], reverse=True)
                    if not md_files:
                        logger.info(f"年份 {year} 没有找到Markdown文件")
                        continue
                    
                    index_content += f'<div class="year-section" id="year-{year}">'
                    index_content += f'<div class="year-title">{year}年</div>'
                    index_content += f'<div class="article-grid">'
                    
                    for md_file in md_files:
                        html_file = md_file.with_suffix('.html')
                        rel_path = os.path.join(year, html_file.name)
                        date_str = md_file.stem
                        all_urls.append(rel_path)
                        
                        index_content += f'''<a href="{rel_path}" class="article-card" target="_blank" data-date="{date_str}">
                            <div class="article-date">{date_str}</div>
                            <div class="article-title">安全资讯日报</div>
                        </a>'''
                        total_files += 1
                        all_articles.append({
                            'date': date_str,
                            'path': rel_path.replace('\\', '/'),
                            'year': year,
                        })
                    
                    index_content += '</div></div>'
                except Exception as e:
                    logger.error(f"处理年份 {year} 时出错: {e}")
                    continue
            
            all_articles.sort(key=lambda x: x['date'], reverse=True)
            recent_days = all_articles[:7]
            logger.info(f"索引内容生成完成，共 {total_files} 个文件")
        except Exception as e:
            logger.error(f"生成索引内容时出错: {e}")
            index_content = f"<div class='content'><h1>安全资讯归档</h1><p>生成索引时出错: {str(e)}</p></div>"
            all_urls = []
            total_files = 0
            recent_days = []
        
        # 使用首页模板
        template_file = INDEX_TEMPLATE_FILE if INDEX_TEMPLATE_FILE.exists() else TEMPLATE_FILE
        if not template_file.exists():
            error_msg = f"模板文件不存在: {template_file}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # 使用模板渲染
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template = Template(f.read())
            
            latest_year = years[0] if years else str(datetime.datetime.now().year)
            full_html = template.render(
                title="安全资讯归档",
                content=index_content,
                total_files=total_files,
                total_years=len(years),
                latest_year=latest_year,
                update_time=current_time,
                year=datetime.datetime.now().year,
                recent_days=recent_days,
                years_list=years,
                site_name=SITE_NAME,
                site_tagline=SITE_TAGLINE,
                github_url=SITE_GITHUB_URL,
            )
            logger.info("模板渲染成功")
        except Exception as e:
            logger.error(f"渲染模板时出错: {e}")
            full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>安全资讯归档</title>
</head>
<body>
    {index_content}
    <footer>
        <p>&copy; {datetime.datetime.now().year} {SITE_NAME}</p>
    </footer>
</body>
</html>"""
        
        # 写入索引文件
        index_file = ARCHIVE_DIR / 'index.html'
        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(full_html)
            
            if not index_file.exists():
                raise IOError(f"索引文件未成功创建: {index_file}")
            
            logger.info(f"成功生成索引文件: {index_file}")
            return True, all_urls
        except Exception as e:
            logger.error(f"写入索引文件失败: {e}")
            raise
            
    except Exception as e:
        logger.error(f"生成索引页面时发生错误: {e}")
        return False, []


def generate_sitemap(urls, base_url=''):
    """生成sitemap.xml文件"""
    try:
        logger.info("开始生成sitemap.xml")
        
        current_time = datetime.datetime.now().strftime('%Y-%m-%d')
        
        sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        # 添加首页
        sitemap_content += f'  <url>\n'
        sitemap_content += f'    <loc>{base_url}index.html</loc>\n'
        sitemap_content += f'    <lastmod>{current_time}</lastmod>\n'
        sitemap_content += f'    <changefreq>daily</changefreq>\n'
        sitemap_content += f'    <priority>1.0</priority>\n'
        sitemap_content += f'  </url>\n'
        
        # 添加所有文章页面
        for url in urls:
            sitemap_content += f'  <url>\n'
            sitemap_content += f'    <loc>{base_url}{url}</loc>\n'
            sitemap_content += f'    <lastmod>{current_time}</lastmod>\n'
            sitemap_content += f'    <changefreq>weekly</changefreq>\n'
            sitemap_content += f'    <priority>0.8</priority>\n'
            sitemap_content += f'  </url>\n'
        
        sitemap_content += '</urlset>'
        
        # 写入sitemap.xml
        sitemap_file = ARCHIVE_DIR / 'sitemap.xml'
        with open(sitemap_file, 'w', encoding='utf-8') as f:
            f.write(sitemap_content)
        
        logger.info(f"成功生成sitemap.xml: {sitemap_file}")
        return True
    except Exception as e:
        logger.error(f"生成sitemap.xml失败: {e}")
        return False


def generate_robots_txt(base_url=''):
    """生成robots.txt文件"""
    try:
        logger.info("开始生成robots.txt")
        
        robots_content = f'User-agent: *\n'
        robots_content += f'Allow: /\n'
        robots_content += f'\n'
        robots_content += f'Sitemap: {base_url}sitemap.xml\n'
        
        # 写入robots.txt
        robots_file = ARCHIVE_DIR / 'robots.txt'
        with open(robots_file, 'w', encoding='utf-8') as f:
            f.write(robots_content)
        
        logger.info(f"成功生成robots.txt: {robots_file}")
        return True
    except Exception as e:
        logger.error(f"生成robots.txt失败: {e}")
        return False

def main():
    """主函数：处理当天的Markdown文件并生成HTML"""
    start_time = datetime.datetime.now()
    logger.info(f"开始执行转换程序，时间: {start_time}")
    
    try:
        # 首先确保模板文件存在
        if not ensure_template_exists():
            logger.error("模板文件检查失败，程序无法继续执行")
            return False
        
        logger.info("开始处理当天的Markdown文件...")
        
        # 确保目录结构存在
        try:
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"确保归档目录存在: {ARCHIVE_DIR}")
        except Exception as e:
            logger.error(f"创建归档目录失败: {e}")
            raise
        
        # 查找当天的文件
        try:
            today_file = find_today_file()
            if today_file:
                logger.info(f"找到要处理的文件: {today_file}")
            else:
                logger.warning("未找到当天或最近的Markdown文件，将创建空白文件")
        except Exception as e:
            logger.error(f"查找文件时出错: {e}")
            today_file = None
        
        # 如果没有找到文件，创建空白文件
        if not today_file:
            try:
                # 创建空白的当天文件作为备用
                today = datetime.datetime.now()
                year_dir = ARCHIVE_DIR / str(today.year)
                year_dir.mkdir(parents=True, exist_ok=True)
                
                today_str = today.strftime('%Y-%m-%d')
                today_file = year_dir / f"{today_str}.md"
                
                with open(today_file, 'w', encoding='utf-8') as f:
                    f.write(f"# 每日安全资讯（{today_str}）\n\n*今日暂无安全资讯更新*\n")
                
                logger.info(f"已创建空白的当天文件: {today_file}")
            except Exception as e:
                logger.error(f"创建空白文件失败: {e}")
                raise
        
        # 转换找到的文件
        html_file = None
        conversion_success = False
        validation_success = False
        try:
            html_file = today_file.with_suffix('.html')
            logger.info(f"开始转换: {today_file} -> {html_file}")
            
            # 最多尝试3次转换
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if convert_md_to_html(today_file, html_file):
                        logger.info(f"转换成功! (尝试 {attempt+1}/{max_retries})")
                        conversion_success = True
                        
                        # 验证生成的HTML文件
                        if HTML_VALIDATOR_AVAILABLE:
                            logger.info(f"开始验证HTML文件: {html_file}")
                            validation_result = validate_html_file(str(html_file))
                            
                            if validation_result['valid']:
                                if not validation_result['warnings']:
                                    logger.info("HTML验证通过，没有警告")
                                else:
                                    logger.warning(f"HTML验证通过，但有 {len(validation_result['warnings'])} 个警告:")
                                    for warning in validation_result['warnings']:
                                        logger.warning(f"HTML警告: {warning}")
                                validation_success = True
                            else:
                                logger.error(f"HTML验证失败，有 {len(validation_result['errors'])} 个错误:")
                                for error in validation_result['errors']:
                                    logger.error(f"HTML错误: {error}")
                                # 虽然验证失败，但我们仍然继续执行，只是记录错误
                                validation_success = False
                        else:
                            logger.warning("HTML验证模块不可用，跳过验证步骤")
                            validation_success = True  # 如果验证器不可用，我们认为验证成功
                        
                        break
                    else:
                        logger.warning(f"转换返回失败 (尝试 {attempt+1}/{max_retries})")
                except Exception as e:
                    logger.error(f"转换过程中出错 (尝试 {attempt+1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2  # 等待2秒后重试
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
            
            if not conversion_success:
                logger.error("所有转换尝试均失败")
        except Exception as e:
            logger.error(f"转换文件时发生未处理的错误: {e}")
        
        # 更新索引页面
        index_success = False
        try:
            logger.info("开始更新索引页面...")
            
            # 最多尝试3次更新索引
            max_retries = 3
            all_urls = []
            for attempt in range(max_retries):
                try:
                    index_result, urls = generate_index_html()
                    if index_result:
                        logger.info(f"索引页面更新成功! (尝试 {attempt+1}/{max_retries})")
                        all_urls = urls
                        index_success = True
                        break
                    else:
                        logger.warning(f"索引页面更新返回失败 (尝试 {attempt+1}/{max_retries})")
                except Exception as e:
                    logger.error(f"更新索引页面时出错 (尝试 {attempt+1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2  # 等待2秒后重试
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
            
            if not index_success:
                logger.error("所有索引更新尝试均失败")
            
            # 生成sitemap.xml、robots.txt 和标题搜索索引
            if index_success and all_urls:
                logger.info("开始生成站点文件（sitemap.xml, robots.txt, search-index.json）...")
                try:
                    # 可以配置base_url，如果部署到网站的话
                    base_url = ''  # 如果部署到 https://example.com/archive/，可以设置为 'https://example.com/archive/'
                    generate_sitemap(all_urls, base_url)
                    generate_robots_txt(base_url)
                    build_search_index()
                    logger.info("站点文件生成完成")
                except Exception as e:
                    logger.warning(f"生成站点文件时出错（不影响主流程）: {e}")
        except Exception as e:
            logger.error(f"更新索引页面时发生未处理的错误: {e}")
        
        # 总结执行结果
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result_summary = []
        if conversion_success:
            result_summary.append(f"HTML转换成功: {html_file}")
        else:
            result_summary.append("HTML转换失败")
        
        if index_success:
            result_summary.append("索引页面更新成功")
        else:
            result_summary.append("索引页面更新失败")
        
        logger.info(f"执行完成，耗时: {duration:.2f}秒")
        logger.info(f"执行结果: {', '.join(result_summary)}")
        
        return conversion_success and index_success
    
    except Exception as e:
        logger.error(f"处理过程中发生严重错误: {e}")
        return False

if __name__ == '__main__':
    main()