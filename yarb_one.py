#!/usr/bin/python3

import os
import json
import time
import asyncio
import schedule
import pyfiglet
import argparse
import datetime
import listparser
import feedparser
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time as time_module

from bot import *
from utils import *

import requests
requests.packages.urllib3.disable_warnings()

today = datetime.datetime.now().strftime("%Y-%m-%d")

# 获取当前时间
def get_current_time():
    return time_module.strftime('%Y-%m-%d %H:%M:%S', time_module.localtime(time_module.time()))


def update_today(data: list=[], conf: dict=None):
    """更新today和archive中的每日安全资讯文件
    
    Args:
        data: 包含安全资讯数据的列表
        conf: 配置字典，用于判断是否启用AI总结
    
    Returns:
        tuple: (更新是否成功, AI总结内容)
    """
    try:
        # 使用Path统一处理所有路径
        today = datetime.datetime.now().strftime("%Y-%m-%d")        
        root_path = Path(__file__).absolute().parent
        data_path = root_path / 'temp_data.json'
        today_path = root_path / 'today.md'
        year_dir = root_path / 'archive' / today.split("-")[0]
        archive_path = year_dir / f'{today}.md'

        # 如果没有提供数据，尝试从临时文件加载
        if not data and data_path.exists():
            try:
                with open(data_path, 'r', encoding='utf-8') as f1:
                    data = json.load(f1)
                print(f"[+] 从{data_path}加载了数据")
            except json.JSONDecodeError as e:
                print(f"[-] 临时数据文件解析失败: {e}")
                return False, None
            except Exception as e:
                print(f"[-] 读取临时数据文件失败: {e}")
                return False, None

        # 确保目录存在
        year_dir.mkdir(parents=True, exist_ok=True)
        print(f"[+] 确保目录存在: {year_dir}")

        # 生成内容
        content = f'# 每日安全资讯（{today}）\n\n'
        for item in data:
            (feed, value), = item.items()
            content += f'- {feed}\n'
            for title, url in value.items():
                content += f'  - [{title}]({url})\n'

        # 写入文件并验证
        def write_and_verify(file_path, content):
            try:
                with open(file_path, 'w+', encoding='utf-8') as f:
                    f.write(content)
                # 验证文件写入
                if not file_path.exists():
                    print(f"[-] 文件未成功创建: {file_path}")
                    return False
                with open(file_path, 'r', encoding='utf-8') as f:
                    written_content = f.read()
                if written_content != content:
                    print(f"[-] 文件内容验证失败: {file_path}")
                    return False
                print(f"[+] 成功写入并验证文件: {file_path}")
                return True
            except Exception as e:
                print(f"[-] 写入文件失败 {file_path}: {e}")
                return False

        # 写入两个文件
        today_success = write_and_verify(today_path, content)
        archive_success = write_and_verify(archive_path, content)

        # 如果文件写入成功，调用AI总结（需要检查是否启用）
        ai_summary = None
        if today_success and archive_success:
            # 检查是否启用AI总结
            ai_enabled = False
            if conf:
                ai_enabled = conf.get('AISummary', {}).get('enabled', False)
            else:
                try:
                    from config_loader import load_config
                    conf = load_config(root_path.joinpath('config.json'))
                    ai_enabled = conf.get('AISummary', {}).get('enabled', False)
                except Exception:
                    pass
            
            if ai_enabled:
                try:
                    print("[+] 开始调用AI总结...")
                    from oneapi import summarize_security_news
                    
                    # 调用AI总结
                    ai_summary = summarize_security_news(content)
                    
                    # 如果AI总结为空或出错，不保存
                    if ai_summary and not ai_summary.startswith("错误") and not ai_summary.startswith("API调用出错"):
                        # 保存AI总结到 AISummary+日期.md
                        summary_filename = f'AISummary{today}.md'
                        summary_path = year_dir / summary_filename
                        
                        summary_content = f'# AI总结 - {today}\n\n生成时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n---\n\n{ai_summary}\n'
                        
                        with open(summary_path, 'w+', encoding='utf-8') as f:
                            f.write(summary_content)
                        
                        print(f"[+] AI总结已保存到: {summary_path}")
                    else:
                        print("[-] AI总结为空或出错，不保存")
                        ai_summary = None
                except Exception as e:
                    print(f"[-] AI总结过程出错: {e}")
                    # 即使AI总结失败，也不影响主流程
                    ai_summary = None
            else:
                print("[!] AI总结功能未启用，跳过AI总结")
        
        return today_success and archive_success, ai_summary

    except Exception as e:
        print(f"[-] 更新today时发生错误: {e}")
        return False, None


def update_rss(rss: dict, proxy_url=''):
    """更新订阅源文件"""
    proxy = {'http': proxy_url, 'https': proxy_url} if proxy_url else {'http': None, 'https': None}

    (key, value), = rss.items()
    rss_path = root_path.joinpath(f'rss/{value["filename"]}')

    result = None
    if url := value.get('url'):
        try:
            r = requests.get(value['url'], proxies=proxy, timeout=30)
            if r.status_code == 200:
                # 验证下载的内容是否有效
                content = r.text.strip()
                if not content:
                    raise ValueError("下载的内容为空")
                
                # 尝试解析OPML内容，验证是否有效
                try:
                    parsed = listparser.parse(content)
                    # 检查是否至少包含一些feed
                    if not hasattr(parsed, 'feeds') or len(parsed.feeds) == 0:
                        raise ValueError("OPML文件不包含有效的feed")
                except Exception as parse_error:
                    raise ValueError(f"OPML解析失败: {str(parse_error)}")
                
                # 验证通过，保存到临时文件，然后替换原文件
                temp_path = rss_path.with_suffix(rss_path.suffix + '.tmp')
                with open(temp_path, 'w+', encoding='utf-8') as f:
                    f.write(content)
                
                # 如果本地文件存在，备份原文件
                backup_path = None
                if rss_path.exists():
                    backup_path = rss_path.with_suffix(rss_path.suffix + '.bak')
                    shutil.copy2(rss_path, backup_path)
                
                # 替换原文件
                temp_path.replace(rss_path)
                
                # 删除备份文件（如果存在）
                if backup_path and backup_path.exists():
                    backup_path.unlink()
                
                print(f'[+] 更新完成：{key} (包含 {len(parsed.feeds)} 个feed)')
                result = {key: rss_path}
            elif rss_path.exists():
                print(f'[-] 更新失败 (HTTP {r.status_code})，使用旧文件：{key}')
                result = {key: rss_path}
            else:
                print(f'[-] 更新失败 (HTTP {r.status_code})，跳过：{key}')
        except Exception as e:
            # 下载或验证失败，保留本地文件
            if rss_path.exists():
                print(f'[-] 更新失败 ({str(e)})，保留旧文件：{key}')
                result = {key: rss_path}
            else:
                print(f'[-] 更新失败 ({str(e)})，跳过：{key}')
    else:
        print(f'[+] 本地文件：{key}')
        if rss_path.exists():
            result = {key: rss_path}

    return result


def parseThread(conf: dict, url: str, proxy_url='', verbose=False):
    """获取文章线程（带超时保护）"""
    def filter(title: str):
        """过滤文章"""
        for i in conf['exclude']:
            if i in title:
                return False
        return True

    proxy = {'http': proxy_url, 'https': proxy_url} if proxy_url else {'http': None, 'https': None}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    title = ''
    result = {}
    try:
        # 使用较短的超时时间，避免卡住
        r = requests.get(url, timeout=15, headers=headers, verify=False, proxies=proxy)
        if r.status_code != 200:
            return title, result
        
        # 解析RSS内容，限制内容大小避免内存问题
        content = r.content
        if len(content) > 10 * 1024 * 1024:  # 超过10MB跳过
            if verbose:
                print(f"[-] RSS源内容过大，跳过: {url}")
            return title, result
            
        r = feedparser.parse(content)
        if not hasattr(r, 'feed') or not hasattr(r, 'entries'):
            return title, result
            
        title = getattr(r.feed, 'title', 'Unknown')
        for entry in r.entries:
            d = entry.get('published_parsed') or entry.get('updated_parsed')
            if not d:
                continue
            yesterday = datetime.date.today() + datetime.timedelta(-1)
            try:
                pubday = datetime.date(d[0], d[1], d[2])
                if pubday == yesterday and filter(entry.title):
                    item = {entry.title: entry.link}
                    if verbose:
                        print(item)
                    result |= item
            except (ValueError, IndexError):
                # 日期解析失败，跳过
                continue
                
        if verbose:
            console.print(f'[+] {title}\t{url}\t{len(result.values())}/{len(r.entries)}', style='bold green')
    except requests.exceptions.Timeout:
        if verbose:
            console.print(f'[-] 超时: {url}', style='bold red')
    except requests.exceptions.RequestException as e:
        if verbose:
            console.print(f'[-] 请求失败: {url} - {str(e)}', style='bold red')
    except Exception as e:
        if verbose:
            console.print(f'[-] 处理失败: {url} - {str(e)}', style='bold red')
    return title, result


async def init_bot(conf: dict, proxy_url=''):
    """初始化机器人"""
    bots = []
    for name, v in conf.items():
        if v['enabled']:
            key = os.getenv(v['secrets']) or v['key']

            if name == 'mail':
                receiver = os.getenv(v['secrets_receiver']) or v['receiver']
                bot = globals()[f'{name}Bot'](v['address'], key, receiver, v['from'], v['server'])
                bots.append(bot)
            elif name == 'telegram':
                bot = globals()[f'{name}Bot'](key, v['chat_id'], proxy_url)
                if await bot.test_connect():
                    bots.append(bot)
            else:
                if name == 'dingtalk':
                    secret = v.get('secret', '')
                    bot = globals()[f'{name}Bot'](key, secret, proxy_url)
                else:
                    bot = globals()[f'{name}Bot'](key, proxy_url)
                bots.append(bot)
    return bots


def init_rss(conf: dict, update: bool=False, proxy_url=''):
    """初始化订阅源"""
    rss_list = []
    
    # 获取自动更新配置
    auto_update_config = conf.get('auto_update', {})
    auto_update_enabled = auto_update_config.get('enabled', False)
    update_interval_days = auto_update_config.get('update_interval_days', 7)
    
    # 过滤掉 auto_update 配置项，只处理实际的 RSS 源
    enabled = [{k: v} for k, v in conf.items() if k != 'auto_update' and v.get('enabled', False)]
    
    for rss in enabled:
        (key, value), = rss.items()
        rss_path = root_path.joinpath(f'rss/{value["filename"]}')
        
        # 检查是否需要更新
        need_update = False
        if update:
            # 命令行强制更新
            need_update = True
        elif auto_update_enabled and value.get('url'):
            # 自动更新检查：如果文件不存在或超过更新间隔，则更新
            if not rss_path.exists():
                need_update = True
                print(f'[+] 文件不存在，需要更新：{key}')
            else:
                # 检查文件修改时间
                file_mtime = datetime.datetime.fromtimestamp(rss_path.stat().st_mtime)
                time_diff = datetime.datetime.now() - file_mtime
                if time_diff.days >= update_interval_days:
                    need_update = True
                    print(f'[+] 文件超过 {update_interval_days} 天未更新，需要更新：{key} (上次更新: {file_mtime.strftime("%Y-%m-%d %H:%M:%S")})')
        
        if need_update:
            if rss := update_rss(rss, proxy_url):
                rss_list.append(rss)
        else:
            rss_list.append({key: rss_path})

    # 合并相同链接
    feeds = []
    for rss in rss_list:
        (_, value), = rss.items()
        try:
            rss = listparser.parse(open(value, encoding='utf-8').read())
            for feed in rss.feeds:
                url = feed.url.strip().rstrip('/')
                short_url = url.split('://')[-1].split('www.')[-1]
                check = [feed for feed in feeds if short_url in feed]
                if not check:
                    feeds.append(url)
        except Exception as e:
            console.print(f'[-] 解析失败：{value}', style='bold red')
            print(e)

    console.print(f'[+] {len(feeds)} feeds', style='bold yellow')
    return feeds


async def job(args):
    """定时任务"""
    print(f'{pyfiglet.figlet_format("SECDaily")}\n{today}')

    global root_path
    root_path = Path(__file__).absolute().parent
    if args.config:
        config_path = Path(args.config).expanduser().absolute()
    else:
        config_path = root_path.joinpath('config.json')
    from config_loader import load_config
    conf = load_config(config_path)

    proxy_rss = conf['proxy']['url'] if conf['proxy']['rss'] else ''
    feeds = init_rss(conf['rss'], args.update, proxy_rss)
    
    # 获取是否显示详细输出配置
    verbose = conf.get('verbose', False)

    results = []
    if args.test:
        # 测试数据
        results.extend({f'test{i}': {Pattern.create(i*500): 'test'}} for i in range(1, 20))
    else:
        # 获取文章
        print(f"\n[+] 开始获取文章，共 {len(feeds)} 个RSS源...")
        numb = 0
        tasks = []
        completed = 0
        total = len(feeds)
        
        with ThreadPoolExecutor(100) as executor:
            tasks.extend(executor.submit(parseThread, conf['keywords'], url, proxy_rss, verbose) for url in feeds)
            # 使用timeout参数，避免无限等待
            try:
                for task in as_completed(tasks, timeout=3600):  # 最多等待1小时
                    completed += 1
                    # 每处理50个或完成时显示进度
                    if completed % 50 == 0 or completed == total:
                        print(f"[进度] {completed}/{total} ({completed*100//total}%)", end='\r')
                    
                    try:
                        title, result = task.result()
                        if result:
                            numb += len(result.values())
                            results.append({title: result})
                    except Exception as e:
                        # 忽略单个任务失败，继续处理其他任务
                        if verbose:
                            print(f"\n[-] 处理任务失败: {str(e)}")
            except TimeoutError:
                print(f"\n[-] 警告：处理超时，已完成 {completed}/{total} 个任务")
                # 尝试获取已完成的任务结果
                for task in tasks:
                    if task.done():
                        try:
                            title, result = task.result()
                            if result:
                                numb += len(result.values())
                                results.append({title: result})
                        except:
                            pass
        
        print(f"\n[+] 完成！共处理 {len(results)} 个feeds，获取 {numb} 篇文章")
        console.print(f'[+] {len(results)} feeds, {numb} articles', style='bold yellow')

        # temp_path = root_path.joinpath('temp_data.json')
        # with open(temp_path, 'w+') as f:
        #     f.write(json.dumps(results, indent=4, ensure_ascii=False))
        #     console.print(f'[+] temp data: {temp_path}', style='bold yellow')

        # 更新today（包含自动AI总结）
        update_result = update_today(results, conf)
        if isinstance(update_result, tuple):
            today_success, ai_summary = update_result
        else:
            today_success = update_result
            ai_summary = None
        
        # 自动生成HTML报告（包含AI总结显示）
        print("\n[+] 开始生成HTML报告...")
        try:
            import subprocess
            subprocess.run(["python", "convert_today.py"], check=True, timeout=300)
            print("[+] HTML报告生成完成")
        except subprocess.TimeoutExpired:
            print("[-] HTML报告生成超时")
        except subprocess.CalledProcessError as e:
            print(f"[-] HTML报告生成失败: {e}")
        except Exception as e:
            print(f"[-] HTML报告生成出错: {e}")
        
        # 推送AI总结（如果启用且AI总结不为空）
        ai_conf = conf.get('AISummary', {})
        if ai_summary and ai_conf.get('enabled', False):
            print(f"\n[+] 开始推送AI总结...")
            print(f"[+] AI总结长度: {len(ai_summary)} 字符")
            print(f"[+] AISummary.enabled: {ai_conf.get('enabled', False)}")
            
            try:
                from bot import wechatAppBot, dingtalkAISummaryBot
                proxy_bot = conf['proxy']['url'] if conf['proxy']['bot'] else ''
                
                # 格式化AI总结内容（使用函数开头定义的 today 变量）
                summary_title = f"🤖 AI安全资讯总结 - {today}"
                summary_text = f"{summary_title}\n\n{ai_summary}"
                
                # 企业微信推送
                if ai_conf.get('wechat', {}).get('enabled', False):
                    wechat_conf = ai_conf.get('wechat', {})
                    print(f"[+] 尝试企业微信推送...")
                    print(f"[+] corpid: {wechat_conf.get('corpid', 'N/A')}")
                    print(f"[+] agentid: {wechat_conf.get('agentid', 'N/A')}")
                    try:
                        wechat_bot = wechatAppBot(
                            wechat_conf.get('corpid'),
                            wechat_conf.get('corpsecret'),
                            wechat_conf.get('agentid'),
                            proxy_bot
                        )
                        result = await wechat_bot.send(summary_text)
                        if result:
                            print("[+] 企业微信推送成功")
                        else:
                            print("[-] 企业微信推送失败（无返回结果）")
                    except Exception as e:
                        print(f"[-] 企业微信推送异常: {e}")
                        # 不记录日志，但打印错误信息
                
                # 钉钉推送
                if ai_conf.get('dingtalk', {}).get('enabled', False):
                    dingtalk_conf = ai_conf.get('dingtalk', {})
                    print(f"[+] 尝试钉钉推送...")
                    print(f"[+] access_token: {dingtalk_conf.get('access_token', 'N/A')[:20]}...")
                    try:
                        dingtalk_bot = dingtalkAISummaryBot(
                            dingtalk_conf.get('access_token'),
                            dingtalk_conf.get('secret', ''),
                            proxy_bot
                        )
                        result = await dingtalk_bot.send(summary_text)
                        if result:
                            print("[+] 钉钉推送成功")
                        else:
                            print("[-] 钉钉推送失败（无返回结果）")
                    except Exception as e:
                        print(f"[-] 钉钉推送异常: {e}")
                        # 不记录日志，但打印错误信息
            except Exception as e:
                print(f"[-] 推送过程异常: {e}")
                # 不记录日志，但打印错误信息
        else:
            if not ai_summary:
                print("[!] AI总结为空，跳过推送")
            elif not ai_conf.get('enabled', False):
                print("[!] AI总结推送未启用，跳过推送")
            else:
                print("[!] 跳过推送（未知原因）")

    # 推送文章
    proxy_bot = conf['proxy']['url'] if conf['proxy']['bot'] else ''
    bots = await init_bot(conf['bot'], proxy_bot)
    for bot in bots:
        await bot.send(bot.parse_results(results))


def argument():
    parser = argparse.ArgumentParser()
    parser.add_argument('--update', help='Update RSS config file', action='store_true', required=False)
    parser.add_argument('--cron', help='Execute scheduled tasks every day (eg:"11:00")', type=str, required=False)
    parser.add_argument('--config', help='Use specified config file', type=str, required=False)
    parser.add_argument('--test', help='Test bot', action='store_true', required=False)
    return parser.parse_args()

async def main():
    args = argument()
    if args.cron:
        schedule.every().day.at(args.cron).do(job, args)
        while True:
            schedule.run_pending()
            await asyncio.sleep(1)
    else:
        await job(args)


# 修改主函数，增加错误处理和重试机制
if __name__ == "__main__":
    # import time
    # import datetime
    # import asyncio
    # import logging
    # import sys
    
    # # 配置日志
    # logging.basicConfig(
    #     level=logging.INFO,
    #     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    #     handlers=[
    #         logging.FileHandler("yarb.log"),
    #         logging.StreamHandler(sys.stdout)
    #     ]
    # )
    
    # def is_weekday():
    #     # 判断是否是工作日（周一到周五）
    #     return datetime.datetime.today().weekday() < 5  # 0-4是周一到周五
    
    # def should_run_now():
    #     now = datetime.datetime.now()
    #     # 检查是否是工作日且当前时间是10点整（精确到分钟）
    #     return is_weekday() and now.hour == 10 and now.minute == 0
    
    # def should_run_force():
    #     # 检查是否有强制运行参数
    #     return len(sys.argv) > 1 and sys.argv[1] == '--force'
    
    # print(f"YARB安全资讯收集器已启动，当前时间: {datetime.datetime.now()}")
    # logging.info("YARB安全资讯收集器已启动")
    
    # while True:
    #     try:
    #         current_time = datetime.datetime.now()
            
    #         # 检查是否应该运行
    #         if should_run_force() or should_run_now():
    #             message = f"当前时间: {current_time}, "
    #             message += "强制执行任务..." if should_run_force() else "是工作日10:00，执行任务..."
    #             print(message)
    #             logging.info(message)
                
    #             # 最多尝试3次
    #             max_retries = 3
    #             for attempt in range(max_retries):
    #                 try:
    #                     asyncio.run(main())
    #                     print(f"任务执行成功，当前时间: {datetime.datetime.now()}")
    #                     logging.info("任务执行成功")
    #                     break
    #                 except Exception as e:
    #                     print(f"任务执行失败 (尝试 {attempt+1}/{max_retries}): {str(e)}")
    #                     logging.error(f"任务执行失败 (尝试 {attempt+1}/{max_retries}): {str(e)}")
    #                     if attempt < max_retries - 1:
    #                         wait_time = 60  # 等待1分钟后重试
    #                         print(f"等待 {wait_time} 秒后重试...")
    #                         time.sleep(wait_time)
    #                     else:
    #                         print("达到最大重试次数，放弃执行")
    #                         logging.error("达到最大重试次数，放弃执行")
                
    #             # 如果是强制执行，执行完就退出
    #             if should_run_force():
    #                 print("强制执行完成，退出程序")
    #                 logging.info("强制执行完成，退出程序")
    #                 sys.exit(0)
    #         else:
    #             # 仅在整分钟时打印状态（避免日志过多）
    #             if current_time.second == 0:
    #                 if current_time.minute == 0:  # 整点报告
    #                     status = f"当前时间: {current_time}, "
    #                     if is_weekday():
    #                         if current_time.hour < 10:
    #                             status += f"等待今日执行时间 (还有 {10-current_time.hour} 小时)"
    #                         else:
    #                             status += "今日任务已执行或未到执行时间"
    #                     else:
    #                         status += "今天是周末，不执行任务"
    #                     print(status)
    #                     logging.info(status)
            
    #         # 每30秒检查一次（平衡精确性和系统负载）
    #         time.sleep(30)
    #     except KeyboardInterrupt:
    #         print("程序被用户中断，正在退出...")
    #         logging.info("程序被用户中断，正在退出...")
    #         sys.exit(0)
    #     except Exception as e:
    #         print(f"主循环发生错误: {str(e)}")
    #         logging.error(f"主循环发生错误: {str(e)}")
    #         time.sleep(60)  # 发生错误后等待1分钟再继续


# if __name__ == '__main__':
    asyncio.run(main())