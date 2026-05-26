#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AI总结功能
"""

import sys
import datetime
import asyncio
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import load_config

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def test_oneapi():
    """测试 oneapi.py 的 AI 总结功能
    
    直接读取当天的Markdown文件（如 2025-11-14.md），不修改原始文件内容
    """
    print("=" * 60)
    print("测试 1: 测试 oneapi.py 的 AI 总结功能")
    print("=" * 60)
    
    try:
        from oneapi import summarize_security_news
        
        # 使用当天的日期（如 2025-11-14）
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        year = today.split("-")[0]
        
        # 直接读取当天的Markdown文件，不修改原始内容
        test_file = Path(__file__).parent / 'archive' / year / f'{today}.md'
        
        if test_file.exists():
            # 只读模式读取，不修改文件
            with open(test_file, 'r', encoding='utf-8') as f:
                test_content = f.read()
            
            print(f"[+] 读取测试文件: {test_file}")
            print(f"[+] 内容长度: {len(test_content)} 字符")
            print("\n[+] 开始调用AI总结...")
            
            result = summarize_security_news(test_content)
            
            print("\n" + "=" * 60)
            print("AI总结结果:")
            print("=" * 60)
            print(result)
            print("=" * 60)
            
            if result and not result.startswith("错误") and not result.startswith("API调用出错"):
                print("\n[OK] 测试通过: AI总结功能正常")
                return True
            else:
                print("\n[FAIL] 测试失败: AI总结返回错误")
                return False
        else:
            print(f"[FAIL] 测试文件不存在: {test_file}")
            return False
            
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_save_summary():
    """测试保存AI总结到文件
    
    直接读取当天的Markdown文件（如 2025-11-14.md），不修改原始文件内容
    只保存AI总结到新的 AISummary 文件
    """
    print("\n" + "=" * 60)
    print("测试 2: 测试保存AI总结到文件")
    print("=" * 60)
    
    try:
        from oneapi import summarize_security_news
        
        # 使用当天的日期（如 2025-11-14）
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        year = today.split("-")[0]
        
        # 直接读取当天的Markdown文件，不修改原始内容
        test_file = Path(__file__).parent / 'archive' / year / f'{today}.md'
        
        if not test_file.exists():
            print(f"[FAIL] 测试文件不存在: {test_file}")
            return False
        
        # 只读模式读取，不修改原始文件
        with open(test_file, 'r', encoding='utf-8') as f:
            test_content = f.read()
        
        print("[+] 调用AI总结...")
        ai_summary = summarize_security_news(test_content)
        
        if not ai_summary or ai_summary.startswith("错误") or ai_summary.startswith("API调用出错"):
            print("[FAIL] AI总结失败，无法保存")
            return False
        
        # 保存到文件
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        year_dir = Path(__file__).parent / 'archive' / today.split("-")[0]
        year_dir.mkdir(parents=True, exist_ok=True)
        
        summary_filename = f'AISummary{today}.md'
        summary_path = year_dir / summary_filename
        
        summary_content = f'# AI总结 - {today}\n\n生成时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n---\n\n{ai_summary}\n'
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        print(f"[+] AI总结已保存到: {summary_path}")
        
        # 验证文件
        if summary_path.exists():
            with open(summary_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            
            if len(saved_content) > 100:
                print(f"[OK] 测试通过: 文件保存成功，内容长度 {len(saved_content)} 字符")
                return True
            else:
                print("[FAIL] 测试失败: 文件内容过短")
                return False
        else:
            print("[FAIL] 测试失败: 文件未成功创建")
            return False
            
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_html_generation():
    """测试HTML生成时加载AI总结
    
    直接读取当天的Markdown文件（如 2025-11-14.md），不修改原始文件内容
    """
    print("\n" + "=" * 60)
    print("测试 3: 测试HTML生成时加载AI总结")
    print("=" * 60)
    
    try:
        from convert_today import convert_md_to_html
        from pathlib import Path
        
        # 使用当天的日期（如 2025-11-14）
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        year = today.split("-")[0]
        
        # 直接读取当天的Markdown文件，不修改原始内容
        test_file = Path(__file__).parent / 'archive' / year / f'{today}.md'
        
        if not test_file.exists():
            print(f"[FAIL] 测试文件不存在: {test_file}")
            return False
        
        html_file = test_file.with_suffix('.html')
        
        print(f"[+] 开始转换: {test_file} -> {html_file}")
        
        result = convert_md_to_html(test_file, html_file)
        
        if result:
            print(f"[+] HTML文件生成成功: {html_file}")
            
            # 检查HTML文件是否包含AI总结相关内容
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            if 'ai-summary-panel' in html_content or 'AI总结' in html_content:
                print("[OK] 测试通过: HTML文件包含AI总结内容")
                return True
            else:
                print("[!] 警告: HTML文件未包含AI总结内容（可能AI总结文件不存在）")
                # 检查是否存在AI总结文件
                summary_file = test_file.parent / f'AISummary{today}.md'
                if summary_file.exists():
                    print(f"[!] AI总结文件存在: {summary_file}")
                    print("[FAIL] 测试失败: HTML未包含AI总结，可能是模板问题")
                    return False
                else:
                    print(f"[!] AI总结文件不存在: {summary_file}")
                    print("[!] 这是正常的，因为需要先运行测试2生成AI总结文件")
                    return True
        else:
            print("[FAIL] 测试失败: HTML文件生成失败")
            return False
            
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_yarb_integration():
    """测试 yarb.py 集成功能（模拟完整流程，包括推送）
    
    直接读取当天的Markdown文件（如 2025-11-14.md），不修改原始文件内容
    只保存AI总结到新的 AISummary 文件
    """
    print("\n" + "=" * 60)
    print("测试 4: 测试 yarb.py 集成功能（模拟完整流程，包括推送）")
    print("=" * 60)
    
    try:
        # 模拟 update_today 函数的AI总结部分
        from oneapi import summarize_security_news
        import datetime
        import json
        from bot import wechatAppBot, dingtalkAISummaryBot
        
        # 使用当天的日期（如 2025-11-14）
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        year = today.split("-")[0]
        
        # 直接读取当天的Markdown文件，不修改原始内容
        test_file = Path(__file__).parent / 'archive' / year / f'{today}.md'
        
        if not test_file.exists():
            print(f"[FAIL] 测试文件不存在: {test_file}")
            return False
        
        # 只读模式读取，不修改原始文件
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 模拟生成内容
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        year_dir = Path(__file__).parent / 'archive' / today.split("-")[0]
        
        print("[+] 模拟 yarb.py 的 update_today 函数...")
        print("[+] 调用AI总结...")
        
        ai_summary = summarize_security_news(content)
        
        if not ai_summary or ai_summary.startswith("错误") or ai_summary.startswith("API调用出错"):
            print("[FAIL] AI总结失败")
            return False
        
        # 保存AI总结
        summary_filename = f'AISummary{today}.md'
        summary_path = year_dir / summary_filename
        
        summary_content = f'# AI总结 - {today}\n\n生成时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n---\n\n{ai_summary}\n'
        
        with open(summary_path, 'w+', encoding='utf-8') as f:
            f.write(summary_content)
        
        print(f"[+] AI总结已保存到: {summary_path}")
        
        # 模拟推送AI总结（如果启用）
        print("\n[+] 开始测试推送功能...")
        
        # 读取配置
        config_path = Path(__file__).parent / 'config.json'
        if config_path.exists():
            config = load_config(config_path)
            
            ai_conf = config.get('AISummary', {})
            
            if ai_summary and ai_conf.get('enabled', False):
                print(f"[+] AI总结长度: {len(ai_summary)} 字符")
                print(f"[+] AISummary.enabled: {ai_conf.get('enabled', False)}")
                
                proxy_bot = config['proxy']['url'] if config['proxy']['bot'] else ''
                
                # 格式化AI总结内容
                summary_title = f"🤖 AI安全资讯总结 - {today}"
                summary_text = f"{summary_title}\n\n{ai_summary}"
                
                push_results = []
                
                # 企业微信推送
                if ai_conf.get('wechat', {}).get('enabled', False):
                    wechat_conf = ai_conf.get('wechat', {})
                    print(f"\n[+] 尝试企业微信推送...")
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
                            push_results.append(True)
                        else:
                            print("[-] 企业微信推送失败（无返回结果）")
                            push_results.append(False)
                    except Exception as e:
                        print(f"[-] 企业微信推送异常: {e}")
                        push_results.append(False)
                else:
                    print("[!] 企业微信推送未启用，跳过")
                
                # 钉钉推送
                if ai_conf.get('dingtalk', {}).get('enabled', False):
                    dingtalk_conf = ai_conf.get('dingtalk', {})
                    print(f"\n[+] 尝试钉钉推送...")
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
                            push_results.append(True)
                        else:
                            print("[-] 钉钉推送失败（无返回结果）")
                            push_results.append(False)
                    except Exception as e:
                        print(f"[-] 钉钉推送异常: {e}")
                        push_results.append(False)
                else:
                    print("[!] 钉钉推送未启用，跳过")
                
                # 检查推送结果
                if push_results:
                    if all(push_results):
                        print("\n[+] 所有启用的推送渠道都成功")
                    else:
                        print("\n[!] 部分推送渠道失败，但不影响主流程")
                else:
                    print("\n[!] 没有启用的推送渠道")
            else:
                if not ai_summary:
                    print("[!] AI总结为空，跳过推送")
                elif not ai_conf.get('enabled', False):
                    print("[!] AI总结推送未启用，跳过推送")
        else:
            print("[!] 配置文件不存在，跳过推送测试")
        
        print("\n[OK] 测试通过: yarb.py 集成功能正常（包括推送测试）")
        return True
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_enabled_flag():
    """测试 AISummary.enabled 开关功能"""
    print("\n" + "=" * 60)
    print("测试 5: 测试 AISummary.enabled 开关功能")
    print("=" * 60)
    
    try:
        import json
        import shutil
        from yarb import update_today
        
        # 读取当前配置
        config_path = Path(__file__).parent / 'config.json'
        if not config_path.exists():
            print(f"[FAIL] 配置文件不存在: {config_path}")
            return False
        
        # 备份原配置
        config_backup = config_path.with_suffix('.json.bak')
        shutil.copy(config_path, config_backup)
        print(f"[+] 已备份配置文件: {config_backup}")
        
        try:
            # 读取配置
            config = load_config(config_path)
            
            # 测试数据
            test_data = [{'测试来源': {'测试标题': 'https://example.com'}}]
            
            # 测试1: enabled = true
            print("\n[+] 测试1: AISummary.enabled = true")
            config['AISummary']['enabled'] = True
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            result = update_today(test_data, config)
            if isinstance(result, tuple):
                success, ai_summary = result
            else:
                success = result
                ai_summary = None
            
            if success and ai_summary:
                print("[OK] 测试通过: enabled=true 时，AI总结被调用")
            else:
                print("[FAIL] 测试失败: enabled=true 时，AI总结未被调用")
                return False
            
            # 测试2: enabled = false
            print("\n[+] 测试2: AISummary.enabled = false")
            config['AISummary']['enabled'] = False
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            result = update_today(test_data, config)
            if isinstance(result, tuple):
                success, ai_summary = result
            else:
                success = result
                ai_summary = None
            
            if success and ai_summary is None:
                print("[OK] 测试通过: enabled=false 时，AI总结未被调用")
            else:
                print(f"[FAIL] 测试失败: enabled=false 时，AI总结仍被调用 (ai_summary: {ai_summary})")
                return False
            
            # 恢复配置
            config['AISummary']['enabled'] = True
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            print("\n[OK] 测试通过: AISummary.enabled 开关功能正常")
            return True
            
        finally:
            # 恢复原配置
            if config_backup.exists():
                shutil.copy(config_backup, config_path)
                config_backup.unlink()
                print(f"[+] 已恢复配置文件")
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_push_functionality():
    """测试AI总结推送功能"""
    print("\n" + "=" * 60)
    print("测试 6: 测试AI总结推送功能")
    print("=" * 60)
    
    try:
        import json
        from bot import wechatAppBot, dingtalkAISummaryBot
        
        # 读取配置
        config_path = Path(__file__).parent / 'config.json'
        if not config_path.exists():
            print(f"[FAIL] 配置文件不存在: {config_path}")
            return False
        
        config = load_config(config_path)
        
        ai_conf = config.get('AISummary', {})
        
        if not ai_conf.get('enabled', False):
            print("[!] AI总结推送未启用，跳过测试")
            return True
        
        # 测试消息
        test_message = "🤖 AI安全资讯总结测试\n\n这是一条测试消息，用于验证推送功能是否正常。"
        
        proxy_bot = config['proxy']['url'] if config['proxy']['bot'] else ''
        
        push_results = []
        
        # 测试企业微信推送
        if ai_conf.get('wechat', {}).get('enabled', False):
            wechat_conf = ai_conf.get('wechat', {})
            print(f"\n[+] 测试企业微信推送...")
            print(f"[+] corpid: {wechat_conf.get('corpid', 'N/A')}")
            print(f"[+] agentid: {wechat_conf.get('agentid', 'N/A')}")
            
            try:
                wechat_bot = wechatAppBot(
                    wechat_conf.get('corpid'),
                    wechat_conf.get('corpsecret'),
                    wechat_conf.get('agentid'),
                    proxy_bot
                )
                result = await wechat_bot.send(test_message)
                if result:
                    print("[OK] 企业微信推送成功")
                    push_results.append(True)
                else:
                    print("[FAIL] 企业微信推送失败")
                    push_results.append(False)
            except Exception as e:
                print(f"[FAIL] 企业微信推送异常: {e}")
                push_results.append(False)
        else:
            print("[!] 企业微信推送未启用，跳过")
            push_results.append(True)  # 未启用不算失败
        
        # 测试钉钉推送
        if ai_conf.get('dingtalk', {}).get('enabled', False):
            dingtalk_conf = ai_conf.get('dingtalk', {})
            print(f"\n[+] 测试钉钉推送...")
            print(f"[+] access_token: {dingtalk_conf.get('access_token', 'N/A')[:20]}...")
            print(f"[+] secret: {'已设置' if dingtalk_conf.get('secret') else '未设置'}")
            
            try:
                dingtalk_bot = dingtalkAISummaryBot(
                    dingtalk_conf.get('access_token'),
                    dingtalk_conf.get('secret', ''),
                    proxy_bot
                )
                result = await dingtalk_bot.send(test_message)
                if result:
                    print("[OK] 钉钉推送成功")
                    push_results.append(True)
                else:
                    print("[FAIL] 钉钉推送失败")
                    push_results.append(False)
            except Exception as e:
                print(f"[FAIL] 钉钉推送异常: {e}")
                push_results.append(False)
        else:
            print("[!] 钉钉推送未启用，跳过")
            push_results.append(True)  # 未启用不算失败
        
        # 如果至少有一个推送渠道启用且测试通过，或者所有启用的都通过
        if push_results and all(push_results):
            print("\n[OK] 测试通过: 推送功能正常")
            return True
        elif not push_results:
            print("\n[!] 没有启用的推送渠道，跳过测试")
            return True
        else:
            print("\n[FAIL] 测试失败: 部分推送失败")
            return False
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_html_display_logic():
    """测试HTML页面显示逻辑（启用/禁用）"""
    print("\n" + "=" * 60)
    print("测试 7: 测试HTML页面显示逻辑（启用/禁用）")
    print("=" * 60)
    
    try:
        import json
        import shutil
        from convert_today import convert_md_to_html
        from pathlib import Path
        
        # 读取当前配置
        config_path = Path(__file__).parent / 'config.json'
        if not config_path.exists():
            print(f"[FAIL] 配置文件不存在: {config_path}")
            return False
        
        # 备份原配置
        config_backup = config_path.with_suffix('.json.bak')
        shutil.copy(config_path, config_backup)
        print(f"[+] 已备份配置文件: {config_backup}")
        
        try:
            # 读取配置
            config = load_config(config_path)
            
            # 使用当天的日期
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            year = today.split("-")[0]
            
            # 测试文件
            test_file = Path(__file__).parent / 'archive' / year / f'{today}.md'
            if not test_file.exists():
                print(f"[FAIL] 测试文件不存在: {test_file}")
                return False
            
            # 确保AI总结文件存在
            summary_file = test_file.parent / f'AISummary{today}.md'
            if not summary_file.exists():
                print(f"[!] AI总结文件不存在，先创建测试文件")
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(f'# AI总结 - {today}\n\n---\n\n测试AI总结内容\n')
            
            html_file = test_file.with_suffix('.html')
            
            # 测试1: enabled = true，应该显示AI总结
            print("\n[+] 测试1: AISummary.enabled = true，应该显示AI总结")
            config['AISummary']['enabled'] = True
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            result = convert_md_to_html(test_file, html_file)
            if result:
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                if 'ai-summary-panel' in html_content and 'AI总结' in html_content:
                    print("[OK] 测试通过: enabled=true 时，HTML包含AI总结")
                else:
                    print("[FAIL] 测试失败: enabled=true 时，HTML未包含AI总结")
                    return False
            else:
                print("[FAIL] 测试失败: HTML生成失败")
                return False
            
            # 测试2: enabled = false，不应该显示AI总结
            print("\n[+] 测试2: AISummary.enabled = false，不应该显示AI总结")
            config['AISummary']['enabled'] = False
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            result = convert_md_to_html(test_file, html_file)
            if result:
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # 检查是否包含AI总结面板（应该不包含）
                if 'ai-summary-panel' not in html_content:
                    print("[OK] 测试通过: enabled=false 时，HTML不包含AI总结")
                else:
                    # 检查是否有 {% if ai_summary %} 判断，如果没有内容应该不显示
                    if '{% if ai_summary %}' in html_content or 'ai-summary-panel' in html_content:
                        # 检查是否有实际内容
                        if '测试AI总结内容' not in html_content:
                            print("[OK] 测试通过: enabled=false 时，HTML不包含AI总结内容")
                        else:
                            print("[FAIL] 测试失败: enabled=false 时，HTML仍包含AI总结内容")
                            return False
                    else:
                        print("[OK] 测试通过: enabled=false 时，HTML不包含AI总结")
            else:
                print("[FAIL] 测试失败: HTML生成失败")
                return False
            
            # 恢复配置
            config['AISummary']['enabled'] = True
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            print("\n[OK] 测试通过: HTML页面显示逻辑正常")
            return True
            
        finally:
            # 恢复原配置
            if config_backup.exists():
                shutil.copy(config_backup, config_path)
                config_backup.unlink()
                print(f"[+] 已恢复配置文件")
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("AI总结功能测试套件")
    print("=" * 60)
    print()
    
    results = []
    
    # 测试1: oneapi.py
    results.append(("oneapi.py AI总结功能", test_oneapi()))
    
    # 测试2: 保存AI总结
    results.append(("保存AI总结到文件", test_save_summary()))
    
    # 测试3: HTML生成
    results.append(("HTML生成时加载AI总结", test_html_generation()))
    
    # 测试4: yarb.py 集成（包括推送）
    results.append(("yarb.py 集成功能（包括推送）", asyncio.run(test_yarb_integration())))
    
    # 测试5: AISummary.enabled 开关
    results.append(("AISummary.enabled 开关功能", test_enabled_flag()))
    
    # 测试6: 推送功能
    results.append(("AI总结推送功能", asyncio.run(test_push_functionality())))
    
    # 测试7: HTML页面显示逻辑
    results.append(("HTML页面显示逻辑（启用/禁用）", test_html_display_logic()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"总计: {len(results)} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    print("=" * 60)
    
    if failed == 0:
        print("\n[OK] 所有测试通过！")
        return 0
    else:
        print(f"\n[FAIL] 有 {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

