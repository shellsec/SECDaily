import os
import socket

DEFAULT_ENV = 'default'


def get_local_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return None


def _load_dotenv():
    try:
        from config_loader import load_dotenv_if_available
        load_dotenv_if_available()
    except ImportError:
        pass


def _profile_env_name(env_name):
    return env_name.upper().replace('-', '_')


def _parse_ip_routing():
    """解析 AI_IP_ROUTING，格式：IP前缀:环境名,IP前缀:环境名"""
    routing = os.getenv('AI_IP_ROUTING', '').strip()
    if not routing:
        return []

    rules = []
    for item in routing.split(','):
        item = item.strip()
        if not item or ':' not in item:
            continue
        prefix, env_name = item.split(':', 1)
        prefix = prefix.strip()
        env_name = env_name.strip()
        if prefix and env_name:
            rules.append((prefix, env_name))
    return rules


def auto_select_env():
    """根据本机 IP 前缀选择 AI 环境，规则来自 AI_IP_ROUTING。"""
    explicit_env = os.getenv('AI_ENV')
    if explicit_env:
        return explicit_env

    local_ip = get_local_ip()
    if local_ip:
        for prefix, env_name in _parse_ip_routing():
            if local_ip.startswith(prefix):
                return env_name

    return os.getenv('AI_ENV_DEFAULT', DEFAULT_ENV)


def get_env_config():
    """读取 AI 服务配置，URL / 模型 / 密钥均来自环境变量。"""
    _load_dotenv()

    env_name = auto_select_env()
    suffix = _profile_env_name(env_name)

    url = os.getenv('AI_API_URL') or os.getenv(f'AI_{suffix}_URL', '')
    api_key = os.getenv('AI_API_KEY') or os.getenv(f'AI_{suffix}_API_KEY', '')
    model = os.getenv('AI_MODEL') or os.getenv(f'AI_{suffix}_MODEL', '')

    return {
        'env': env_name,
        'url': url.strip(),
        'api_key': api_key.strip(),
        'model': model.strip(),
        'provider': (
            os.getenv('AI_PROVIDER')
            or os.getenv(f'AI_{suffix}_PROVIDER')
            or 'openai'
        ).strip().lower(),
    }
