#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AI总结推送功能
"""

import sys
import json
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


async def test_wechat_push():
    """测试企业微信推送"""
    print("=" * 60)
    print("测试 1: 企业微信推送")
    print("=" * 60)
    
    try:
        from bot import wechatAppBot
        
        # 读取配置
        config_path = Path(__file__).parent / 'config.json'
        if not config_path.exists():
            print(f"[FAIL] 配置文件不存在: {config_path}")
            return False
        
        config = load_config(config_path)
        
        ai_conf = config.get('AISummary', {})
        wechat_conf = ai_conf.get('wechat', {})
        
        if not wechat_conf.get('enabled', False):
            print("[!] 企业微信推送未启用，跳过测试")
            return True
        
        print(f"[+] corpid: {wechat_conf.get('corpid', 'N/A')}")
        print(f"[+] agentid: {wechat_conf.get('agentid', 'N/A')}")
        
        proxy_bot = config['proxy']['url'] if config['proxy']['bot'] else ''
        
        # 创建机器人实例
        wechat_bot = wechatAppBot(
            wechat_conf.get('corpid'),
            wechat_conf.get('corpsecret'),
            wechat_conf.get('agentid'),
            proxy_bot
        )
        
        # 测试消息
        test_message = "🤖 AI安全资讯总结测试\n\n这是一条测试消息，用于验证企业微信推送功能是否正常。"
        
        print(f"\n[+] 发送测试消息...")
        print(f"[+] 消息内容: {test_message[:50]}...")
        
        result = await wechat_bot.send(test_message)
        
        if result:
            print("[OK] 企业微信推送成功")
            return True
        else:
            print("[FAIL] 企业微信推送失败")
            return False
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_dingtalk_push():
    """测试钉钉推送"""
    print("\n" + "=" * 60)
    print("测试 2: 钉钉推送")
    print("=" * 60)
    
    try:
        from bot import dingtalkAISummaryBot
        
        # 读取配置
        config_path = Path(__file__).parent / 'config.json'
        if not config_path.exists():
            print(f"[FAIL] 配置文件不存在: {config_path}")
            return False
        
        config = load_config(config_path)
        
        ai_conf = config.get('AISummary', {})
        dingtalk_conf = ai_conf.get('dingtalk', {})
        
        if not dingtalk_conf.get('enabled', False):
            print("[!] 钉钉推送未启用，跳过测试")
            return True
        
        access_token = dingtalk_conf.get('access_token', '')
        secret = dingtalk_conf.get('secret', '')
        
        print(f"[+] access_token: {access_token[:20]}...")
        print(f"[+] secret: {'已设置' if secret else '未设置'}")
        
        proxy_bot = config['proxy']['url'] if config['proxy']['bot'] else ''
        
        # 创建机器人实例
        dingtalk_bot = dingtalkAISummaryBot(
            access_token,
            secret,
            proxy_bot
        )
        
        # 测试消息
        test_message = "🤖 AI安全资讯总结测试\n\n这是一条测试消息，用于验证钉钉推送功能是否正常。"
        
        print(f"\n[+] 发送测试消息...")
        print(f"[+] 消息内容: {test_message[:50]}...")
        
        result = await dingtalk_bot.send(test_message)
        
        if result:
            print("[OK] 钉钉推送成功")
            return True
        else:
            print("[FAIL] 钉钉推送失败")
            return False
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_both_push():
    """测试两个推送接口"""
    print("\n" + "=" * 60)
    print("AI总结推送功能测试")
    print("=" * 60)
    print()
    
    results = []
    
    # 测试企业微信
    results.append(("企业微信推送", await test_wechat_push()))
    
    # 测试钉钉
    results.append(("钉钉推送", await test_dingtalk_push()))
    
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
    sys.exit(asyncio.run(test_both_push()))

