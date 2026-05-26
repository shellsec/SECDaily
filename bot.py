import time
import json
import telegram
import requests
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime
from pyrate_limiter import Duration, Rate, InMemoryBucket, Limiter

from utils import *

__all__ = ["feishuBot", "wecomBot", "dingtalkBot", "telegramBot", "mailBot"]
today = datetime.now().strftime("%Y-%m-%d")


class feishuBot:
    """飞书群机器人
    https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNxkjN
    """

    def __init__(self, key, proxy_url='') -> None:
        self.key = key
        self.proxy = {'http': proxy_url, 'https': proxy_url} if proxy_url else {
            'http': None, 'https': None}

    @staticmethod
    def parse_results(results: list):
        text_list = []
        for result in results:
            (feed, value), = result.items()
            text = f'[ {feed} ]\n\n'
            for title, link in value.items():
                text += f'{title}\n{link}\n\n'
            text_list.append(text.strip())
        return text_list

    async def send(self, text_list: list):
        for text in text_list:
            print(f'{len(text)} {text[:50]}...{text[-50:]}')

            data = {"msg_type": "text", "content": {"text": text}}
            headers = {'Content-Type': 'application/json'}
            url = f'https://open.feishu.cn/open-apis/bot/v2/hook/{self.key}'
            r = requests.post(url=url, headers=headers,
                              data=json.dumps(data), proxies=self.proxy)

            if r.status_code == 200:
                console.print('[+] feishuBot 发送成功', style='bold green')
            else:
                console.print('[-] feishuBot 发送失败', style='bold red')
                print(r.text)

    async def send_markdown(self, text):
        # TODO 富文本
        data = {"msg_type": "text", "content": {"text": text}}
        self.send(data)


class wecomBot:
    """企业微信群机器人
    https://developer.work.weixin.qq.com/document/path/91770
    """

    def __init__(self, key, proxy_url='') -> None:
        self.key = key
        self.proxy = {'http': proxy_url, 'https': proxy_url} if proxy_url else {
            'http': None, 'https': None}

    @staticmethod
    def parse_results(results: list):
        text_list = []
        for result in results:
            (feed, value), = result.items()
            text = f'## {feed}\n'
            for title, link in value.items():
                text += f'- [{title}]({link})\n'
            text_list.append(text.strip())
        return text_list

    async def send(self, text_list: list):
        rates = [Rate(20, Duration.MINUTE)] # 频率限制，20条/分钟
        bucket = InMemoryBucket(rates)
        limiter = Limiter(bucket, max_delay=Duration.MINUTE.value)

        for text in text_list:
            limiter.try_acquire('identity')
            print(f'{len(text)} {text[:50]}...{text[-50:]}')

            data = {"msgtype": "markdown", "markdown": {"content": text}}
            headers = {'Content-Type': 'application/json'}
            url = f'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self.key}'
            r = requests.post(url=url, headers=headers, data=json.dumps(data), proxies=self.proxy)

            if r.status_code == 200:
                console.print('[+] wecomBot 发送成功', style='bold green')
            else:
                console.print('[-] wecomBot 发送失败', style='bold red')
                print(r.text)


class dingtalkBot:
    """钉钉群机器人
    https://open.dingtalk.com/document/robots/custom-robot-access
    """

    def __init__(self, key, secret='', proxy_url='') -> None:
        self.key = key
        self.secret = secret
        self.proxy = {'http': proxy_url, 'https': proxy_url} if proxy_url else {
            'http': None, 'https': None}

    @staticmethod
    def parse_results(results: list):
        text_list = []
        for result in results:
            (feed, value), = result.items()
            text = ''.join(
                f'- [{title}]({link})\n' for title, link in value.items())
            text_list.append([feed, text.strip()])
        return text_list

    def _get_sign(self):
        """计算钉钉机器人签名"""
        import hmac
        import hashlib
        import base64
        import urllib.parse
        
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    async def send(self, text_list: list):
        rates = [Rate(20, Duration.MINUTE)] # 频率限制，20条/分钟
        bucket = InMemoryBucket(rates)
        limiter = Limiter(bucket, max_delay=Duration.MINUTE.value)

        for (feed, text) in text_list:
            limiter.try_acquire('identity')

            text = f'## {feed}\n{text}'
            text += f"\n\n <!-- Powered by Yarb. -->"
            print(f'{len(text)} {text[:50]}...{text[-50:]}')

            data = {"msgtype": "markdown", "markdown": {
                "title": feed, "text": text}}
            headers = {'Content-Type': 'application/json'}
            
            url = f'https://oapi.dingtalk.com/robot/send?access_token={self.key}'
            
            # 如果设置了secret，添加签名
            if self.secret:
                timestamp, sign = self._get_sign()
                url = f'{url}&timestamp={timestamp}&sign={sign}'
                console.print(f'[*] dingtalkBot 使用签名验证', style='bold blue')
            
            r = requests.post(url=url, headers=headers,
                                data=json.dumps(data), proxies=self.proxy)

            if r.status_code == 200:
                resp = r.json()
                if resp.get('errcode') == 0:
                    console.print('[+] dingtalkBot 发送成功', style='bold green')
                else:
                    console.print(f"[-] dingtalkBot 发送失败: {resp.get('errmsg')}", style='bold red')
            else:
                console.print('[-] dingtalkBot 发送失败', style='bold red')
                print(r.text)


class mailBot:
    """邮件机器人
    """

    def __init__(self, sender, passwd, receiver: str, fromwho='', server='') -> None:
        self.sender = sender
        self.receiver = receiver
        self.fromwho = fromwho or sender
        server = server or self.get_server(sender)

        self.smtp = smtplib.SMTP_SSL(server)
        self.smtp.login(sender, passwd)

    def get_server(self, sender: str):
        key = sender.rstrip('.com').split('@')[-1]
        server = {
            'qq': 'smtp.qq.com',
            'foxmail': 'smtp.qq.com',
            '163': 'smtp.163.com',
            'sina': 'smtp.sina.com',
            'gmail': 'smtp.gmail.com',
            'outlook': 'smtp.live.com',
        }
        return server.get(key, f'smtp.{key}.com')

    @staticmethod
    def parse_results(results: list):
        text = f'<html><head><h1>每日安全资讯（{today}）</h1></head><body>'
        for result in results:
            (feed, value), = result.items()
            text += f'<h3>{feed}</h3><ul>'
            for title, link in value.items():
                text += f'<li><a href="{link}">{title}</a></li>'
            text += '</ul>'
        text += '<br><br><b>如不需要，可直接回复本邮件退订。</b></body></html>'
        print(text)
        return text

    async def send(self, text: str):
        print(f'{len(text)} {text[:50]}...{text[-50:]}')

        msg = MIMEText(text, 'html')
        msg['Subject'] = Header(f'每日安全资讯（{today}）')
        msg['From'] = self.fromwho
        msg['To'] = self.receiver

        try:
            self.smtp.sendmail(
                self.sender, self.receiver.split(','), msg.as_string())
            console.print('[+] mailBot 发送成功', style='bold green')
        except Exception as e:
            console.print('[+] mailBot 发送失败', style='bold red')
            print(e)


class telegramBot:
    """Telegram机器人
    https://core.telegram.org/bots/api
    """

    def __init__(self, key, chat_id: list, proxy_url='') -> None:
        self.key = key
        self.proxy = {'http': proxy_url, 'https': proxy_url} if proxy_url else {
            'http': None, 'https': None}

        proxy = telegram.request.HTTPXRequest(proxy_url=None)
        self.chat_id = chat_id
        self.bot = telegram.Bot(token=key, request=proxy)

    async def test_connect(self):
        try:
            await self.bot.get_me()
            return True
        except Exception as e:
            console.print('[-] telegramBot 连接失败', style='bold red')
            return False

    @staticmethod
    def parse_results(results: list):
        text_list = []
        for result in results:
            (feed, value), = result.items()
            text = f'<b>{feed}</b>\n'
            for idx, (title, link) in enumerate(value.items()):
                text += f'{idx+1}. <a href="{link}">{title}</a>\n'
            text_list.append(text.strip())
        return text_list

    async def send(self, text_list: list):
        rates = [Rate(20, Duration.MINUTE)] # 频率限制，20条/分钟
        bucket = InMemoryBucket(rates)
        limiter = Limiter(bucket, max_delay=Duration.MINUTE.value)

        for text in text_list:
            limiter.try_acquire('identity')
            print(f'{len(text)} {text[:50]}...{text[-50:]}')

            for id in self.chat_id:
                try:
                    self.bot.send_message(chat_id=id, text=text, parse_mode='HTML')
                    console.print(f'[+] telegramBot 发送成功 {id}', style='bold green')
                except Exception as e:
                    console.print(f'[-] telegramBot 发送失败 {id}', style='bold red')
                    print(e)


class wechatAppBot:
    """企业微信应用推送
    https://developer.work.weixin.qq.com/document/path/90236
    """
    
    def __init__(self, corpid, corpsecret, agentid, proxy_url=''):
        self.corpid = corpid
        self.corpsecret = corpsecret
        self.agentid = agentid
        self.proxy = {'http': proxy_url, 'https': proxy_url} if proxy_url else {
            'http': None, 'https': None}
        self.access_token = None
        self.token_expire_time = 0
    
    def _get_access_token(self):
        """获取access_token"""
        import time
        current_time = time.time()
        
        # 如果token未过期，直接返回
        if self.access_token and current_time < self.token_expire_time:
            return self.access_token
        
        # 获取新token
        url = f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corpid}&corpsecret={self.corpsecret}'
        try:
            r = requests.get(url, proxies=self.proxy, timeout=10)
            
            if r.status_code == 200:
                resp = r.json()
                if resp.get('errcode') == 0:
                    self.access_token = resp.get('access_token')
                    # token有效期7200秒，提前300秒刷新
                    self.token_expire_time = current_time + resp.get('expires_in', 7200) - 300
                    return self.access_token
                else:
                    # 打印错误信息用于调试
                    print(f"[-] 企业微信获取token失败: errcode={resp.get('errcode')}, errmsg={resp.get('errmsg')}")
                    return None
            else:
                print(f"[-] 企业微信获取token失败: HTTP {r.status_code}")
                return None
        except Exception as e:
            print(f"[-] 企业微信获取token异常: {e}")
            return None
    
    async def send(self, text: str):
        """发送文本消息（不记录日志）"""
        try:
            access_token = self._get_access_token()
            if not access_token:
                print("[-] 企业微信推送失败: 无法获取access_token")
                return False
            
            url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
            
            # 企业微信应用消息格式
            data = {
                "touser": "@all",
                "msgtype": "text",
                "agentid": self.agentid,
                "text": {
                    "content": text
                }
            }
            
            headers = {'Content-Type': 'application/json'}
            r = requests.post(url, headers=headers, data=json.dumps(data, ensure_ascii=False), proxies=self.proxy, timeout=10)
            
            if r.status_code == 200:
                resp = r.json()
                if resp.get('errcode') == 0:
                    return True
                else:
                    print(f"[-] 企业微信推送失败: errcode={resp.get('errcode')}, errmsg={resp.get('errmsg')}")
                    return False
            else:
                print(f"[-] 企业微信推送失败: HTTP {r.status_code}, {r.text[:200]}")
                return False
        except Exception as e:
            print(f"[-] 企业微信推送异常: {e}")
            return False


class dingtalkAISummaryBot:
    """钉钉AI总结推送（不记录日志）"""
    
    def __init__(self, access_token, secret='', proxy_url=''):
        self.access_token = access_token
        self.secret = secret
        self.proxy = {'http': proxy_url, 'https': proxy_url} if proxy_url else {
            'http': None, 'https': None}
    
    def _get_sign(self):
        """计算钉钉机器人签名"""
        import hmac
        import hashlib
        import base64
        import urllib.parse
        
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign
    
    async def send(self, text: str):
        """发送文本消息（不记录日志）"""
        try:
            if not self.access_token:
                print("[-] 钉钉推送失败: access_token为空")
                return False
            
            data = {"msgtype": "markdown", "markdown": {
                "title": "AI安全资讯总结",
                "text": text
            }}
            headers = {'Content-Type': 'application/json'}
            
            url = f'https://oapi.dingtalk.com/robot/send?access_token={self.access_token}'
            
            # 如果设置了secret，添加签名
            if self.secret:
                timestamp, sign = self._get_sign()
                url = f'{url}&timestamp={timestamp}&sign={sign}'
            
            r = requests.post(url, headers=headers, data=json.dumps(data, ensure_ascii=False), proxies=self.proxy, timeout=10)
            
            if r.status_code == 200:
                resp = r.json()
                if resp.get('errcode') == 0:
                    return True
                else:
                    print(f"[-] 钉钉推送失败: errcode={resp.get('errcode')}, errmsg={resp.get('errmsg')}")
                    return False
            else:
                print(f"[-] 钉钉推送失败: HTTP {r.status_code}, {r.text[:200]}")
                return False
        except Exception as e:
            print(f"[-] 钉钉推送异常: {e}")
            import traceback
            traceback.print_exc()
            return False