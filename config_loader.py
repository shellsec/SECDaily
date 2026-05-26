import json
import os
from copy import deepcopy
from pathlib import Path

BASE_DIR = Path(__file__).parent
DEFAULT_CONFIG_PATH = BASE_DIR / 'config.json'


def load_dotenv_if_available():
    """若安装了 python-dotenv 且存在 .env，则自动加载。"""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env_path = BASE_DIR / '.env'
    if env_path.exists():
        load_dotenv(env_path)


def _pick(env_name, *fallback_keys, conf_section=None):
    """优先环境变量，其次配置文件中的 fallback 字段。"""
    if env_name:
        value = os.getenv(env_name)
        if value:
            return value

    if conf_section is not None:
        for key in fallback_keys:
            value = conf_section.get(key, '')
            if value:
                return value
    return ''


def resolve_config_secrets(conf):
    """将配置中的密钥字段解析为环境变量值。"""
    conf = deepcopy(conf)

    for name, bot in conf.get('bot', {}).items():
        env_key_name = bot.get('secrets')
        if env_key_name:
            bot['key'] = _pick(env_key_name, 'key', conf_section=bot)

        if name == 'dingtalk':
            bot['secret'] = _pick(
                bot.get('secrets_secret', 'DINGTALK_SECRET'),
                'secret',
                conf_section=bot,
            )

        if name == 'mail':
            bot['key'] = _pick(bot.get('secrets', 'MAIL_KEY'), 'key', conf_section=bot)
            bot['receiver'] = _pick(
                bot.get('secrets_receiver', 'MAIL_RECEIVER'),
                'receiver',
                conf_section=bot,
            )
            bot['address'] = _pick('MAIL_ADDRESS', 'address', conf_section=bot)
            bot['server'] = _pick('MAIL_SERVER', 'server', conf_section=bot)
            bot['from'] = _pick('MAIL_FROM', 'from', conf_section=bot)

        if name == 'telegram':
            bot['key'] = _pick(bot.get('secrets', 'TELEGRAM_KEY'), 'key', conf_section=bot)
            chat_ids = os.getenv('TELEGRAM_CHAT_IDS')
            if chat_ids:
                bot['chat_id'] = [item.strip() for item in chat_ids.split(',') if item.strip()]
            elif not bot.get('chat_id'):
                bot['chat_id'] = []

    ai_conf = conf.get('AISummary', {})
    wechat_conf = ai_conf.get('wechat', {})
    if wechat_conf:
        wechat_conf['corpid'] = _pick(
            wechat_conf.get('secrets_corpid', 'WECOM_CORPID'),
            'corpid',
            conf_section=wechat_conf,
        )
        wechat_conf['corpsecret'] = _pick(
            wechat_conf.get('secrets_corpsecret', 'WECOM_CORPSECRET'),
            'corpsecret',
            conf_section=wechat_conf,
        )
        wechat_conf['agentid'] = _pick(
            wechat_conf.get('secrets_agentid', 'WECOM_AGENTID'),
            'agentid',
            conf_section=wechat_conf,
        )

    dingtalk_conf = ai_conf.get('dingtalk', {})
    if dingtalk_conf:
        dingtalk_conf['access_token'] = _pick(
            dingtalk_conf.get('secrets_access_token', 'DINGTALK_ACCESS_TOKEN'),
            'access_token',
            conf_section=dingtalk_conf,
        ) or _pick('DINGTALK_KEY', conf_section=dingtalk_conf)
        dingtalk_conf['secret'] = _pick(
            dingtalk_conf.get('secrets_secret', 'DINGTALK_SECRET'),
            'secret',
            conf_section=dingtalk_conf,
        )

    return conf


def load_config(path=None):
    """加载 config.json 并解析环境变量中的密钥。"""
    load_dotenv_if_available()

    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        example_path = BASE_DIR / 'config.example.json'
        hint = f'请复制 {example_path.name} 为 config.json，并在 .env 中填写密钥。'
        raise FileNotFoundError(f'配置文件不存在: {config_path}. {hint}')

    with open(config_path, encoding='utf-8') as f:
        conf = json.load(f)

    return resolve_config_secrets(conf)
