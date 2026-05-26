import os
import requests
import json
import time
from pathlib import Path
from ai_config import get_env_config


def _mask_env_config_for_log(env_config):
    masked = dict(env_config)
    key = masked.get('api_key', '')
    if key:
        masked['api_key'] = f"{key[:4]}..." if len(key) > 4 else '***'
    return masked


def build_ai_request_headers(env_config):
    """根据 AI_PROVIDER 构建请求头，默认 OpenAI 兼容格式。"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {env_config['api_key']}",
    }
    provider = env_config.get('provider') or 'openai'
    if provider == 'tencent':
        headers.update({
            "X-TC-Action": os.getenv('AI_TC_ACTION', 'ChatCompletion'),
            "X-TC-Version": os.getenv('AI_TC_VERSION', '2025-02-24'),
            "X-TC-Timestamp": str(int(time.time())),
            "X-TC-RequestClient": os.getenv('AI_TC_REQUEST_CLIENT', 'SDK'),
        })
        region = os.getenv('AI_TC_REGION', '').strip()
        if region:
            headers["X-TC-Region"] = region
    return headers

def analyze_by_keywords(content):
    """基于关键词的安全需求分析函数
    
    Args:
        content: 需求内容文本
    
    Returns:
        str: 结构化的安全评估报告
    """
    print("analyze_by_keywords - 使用关键词分析")
    
    # 需求验证逻辑
    if not content or len(content.strip()) < 20 or '需求' not in content:
        return "错误：输入内容不符合需求格式要求，请提供详细的需求描述。"
    
    # 定义安全类别关键词字典
    security_keywords = {
        '敏感数据类': {
            'keywords': ['密码', '密钥', 'token', '身份证', '手机号', '银行卡', '个人信息', '隐私', 
                        '加密', '解密', '敏感数据', '数据脱敏', '数据加密', 'AES', 'RSA', 'DES'],
            'risk_level': '高',
            'suggestions': [
                '1. 使用强加密算法（如AES-256）对敏感数据进行加密存储',
                '2. 密钥管理：使用密钥管理系统，定期轮换密钥',
                '3. 数据脱敏：对展示的敏感信息进行脱敏处理',
                '4. 访问控制：严格控制敏感数据的访问权限',
                '5. 日志审计：记录所有敏感数据的访问和操作日志'
            ]
        },
        '账户登录注册类': {
            'keywords': ['登录', '注册', '登出', '认证', '验证码', '短信验证', '邮箱验证', 
                        '密码重置', '忘记密码', '多因素认证', 'MFA', '单点登录', 'SSO', 
                        'OAuth', 'JWT', 'session', 'cookie'],
            'risk_level': '高',
            'suggestions': [
                '1. 密码策略：强制使用强密码，定期更换密码',
                '2. 验证码防护：验证码有效期限制，防暴力破解',
                '3. 登录限制：登录失败次数限制，IP白名单/黑名单',
                '4. 会话管理：设置合理的session超时时间，使用安全的cookie属性',
                '5. 多因素认证：对敏感操作启用多因素认证'
            ]
        },
        '支付扣款消耗类': {
            'keywords': ['支付', '扣款', '充值', '提现', '转账', '订单', '金额', '余额', 
                        '银行卡', '支付宝', '微信支付', '第三方支付', '支付网关', '交易'],
            'risk_level': '高',
            'suggestions': [
                '1. 金额校验：前后端双重校验，防止金额篡改',
                '2. 支付安全：使用官方支付网关，不存储完整银行卡信息',
                '3. 交易记录：完整记录所有交易流水，支持对账',
                '4. 风控系统：异常交易检测，大额交易二次确认',
                '5. 数据加密：支付数据传输和存储加密'
            ]
        },
        '上传下载导出类': {
            'keywords': ['上传', '下载', '导出', '导入', '文件', '附件', '图片', '文档', 
                        'Excel', 'PDF', '压缩包', '文件类型', '文件大小', '文件校验'],
            'risk_level': '中',
            'suggestions': [
                '1. 文件类型限制：白名单机制，严格限制允许的文件类型',
                '2. 文件大小限制：防止大文件攻击，限制上传文件大小',
                '3. 文件扫描：对上传文件进行病毒扫描和内容检查',
                '4. 文件存储：上传文件隔离存储，使用安全的文件路径',
                '5. 下载控制：下载权限验证，防止未授权下载'
            ]
        },
        '内容消息推送类': {
            'keywords': ['推送', '消息', '通知', '短信', '邮件', '站内信', '公告', 
                        '内容审核', '敏感词', '消息加密', '推送频率'],
            'risk_level': '中',
            'suggestions': [
                '1. 内容审核：对推送内容进行敏感词过滤和内容审核',
                '2. 消息加密：敏感消息内容加密传输和存储',
                '3. 推送限制：限制推送频率，防止恶意推送',
                '4. 用户权限：验证用户是否有接收消息的权限',
                '5. 消息签名：对重要消息进行数字签名，防止篡改'
            ]
        },
        '数据统计UI类': {
            'keywords': ['统计', '报表', '数据展示', '图表', 'Dashboard', '数据分析', 
                        '数据可视化', '导出报表', '数据权限'],
            'risk_level': '低',
            'suggestions': [
                '1. 数据脱敏：统计数据中的敏感信息进行脱敏处理',
                '2. 权限控制：根据用户角色控制可查看的统计数据范围',
                '3. 数据准确性：确保统计数据的准确性和实时性',
                '4. 性能优化：大数据量统计使用缓存和异步处理',
                '5. 审计日志：记录数据统计的访问日志'
            ]
        },
        'API接口类': {
            'keywords': ['API', '接口', '接口调用', 'RESTful', 'GraphQL', '接口鉴权', 
                        '接口限流', '接口文档', '接口测试', '接口版本'],
            'risk_level': '高',
            'suggestions': [
                '1. 接口鉴权：使用Token、OAuth等机制进行接口认证',
                '2. 接口限流：防止接口被恶意调用，设置合理的限流策略',
                '3. 参数校验：严格校验接口参数，防止SQL注入、XSS等攻击',
                '4. 接口加密：敏感接口使用HTTPS，对请求参数加密',
                '5. 接口监控：监控接口调用情况，及时发现异常'
            ]
        },
        '加固类': {
            'keywords': ['加固', '安全加固', '防护', '防攻击', 'WAF', '防火墙', 
                        '安全配置', '安全策略', '漏洞修复', '补丁'],
            'risk_level': '中',
            'suggestions': [
                '1. 安全配置：按照安全最佳实践进行系统配置',
                '2. 漏洞扫描：定期进行安全扫描和漏洞检测',
                '3. 补丁管理：及时安装安全补丁，修复已知漏洞',
                '4. 防护措施：部署WAF、防火墙等安全防护设备',
                '5. 安全审计：定期进行安全审计和渗透测试'
            ]
        }
    }
    
    # 分析内容，匹配关键词
    content_lower = content.lower()
    matched_categories = {}
    
    for category, info in security_keywords.items():
        matched_keywords = []
        for keyword in info['keywords']:
            if keyword.lower() in content_lower:
                matched_keywords.append(keyword)
        
        if matched_keywords:
            matched_categories[category] = {
                'keywords': matched_keywords,
                'risk_level': info['risk_level'],
                'suggestions': info['suggestions']
            }
    
    # 生成报告
    if not matched_categories:
        return """## 关键词分析结果

**需求摘要：**
未检测到明确的安全相关关键词，建议进行人工审核。

**风险分类：**
无法自动分类

**风险等级评估：**
无法评估

**建议：**
请提供更详细的需求描述，或使用AI分析功能进行深度分析。
"""
    
    # 确定最高风险等级
    risk_levels = {'高': 3, '中': 2, '低': 1}
    max_risk_score = max([risk_levels[cat['risk_level']] for cat in matched_categories.values()])
    max_risk_level = [k for k, v in risk_levels.items() if v == max_risk_score][0]
    
    # 构建报告
    report = "## 关键词分析结果\n\n"
    report += "**需求摘要：**\n"
    report += f"通过关键词匹配，识别出 {len(matched_categories)} 个安全相关类别。\n\n"
    
    report += "**风险分类：**\n"
    for category, info in matched_categories.items():
        report += f"- {category}（匹配关键词：{', '.join(info['keywords'][:5])}）\n"
    report += "\n"
    
    report += f"**风险等级评估：**{max_risk_level}风险\n\n"
    
    report += "**具体风险点描述：**\n"
    for category, info in matched_categories.items():
        report += f"\n### {category}\n"
        report += f"- 风险等级：{info['risk_level']}风险\n"
        report += f"- 匹配的关键词：{', '.join(info['keywords'])}\n"
    
    report += "\n**加固建议：**\n"
    for category, info in matched_categories.items():
        report += f"\n### {category}加固建议\n"
        for suggestion in info['suggestions']:
            report += f"{suggestion}\n"
    
    report += "\n**测试用例建议：**\n"
    report += "1. 功能测试：验证各项安全功能是否正常工作\n"
    report += "2. 安全测试：进行SQL注入、XSS、CSRF等安全测试\n"
    report += "3. 性能测试：测试系统在高并发情况下的表现\n"
    report += "4. 权限测试：验证权限控制是否有效\n"
    report += "5. 异常测试：测试异常情况下的系统行为\n"
    
    report += "\n**合规性检查：**\n"
    report += "1. 数据保护：确保符合《个人信息保护法》等相关法规\n"
    report += "2. 数据安全：符合《网络安全法》等安全法规要求\n"
    report += "3. 行业标准：遵循相关行业安全标准和最佳实践\n"
    
    return report

def is_ai_enabled():
    """检查AI分析是否启用
    
    Returns:
        bool: True表示启用，False表示未启用
    """
    try:
        config_path = Path(__file__).parent / 'config.json'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('AISummary', {}).get('enabled', False)
    except Exception as e:
        print(f"[-] 读取配置文件失败: {e}")
    return False

def analyze_security_report_fenlei(content, use_keyword_analysis=False):
    """安全需求分析函数
    
    Args:
        content: 需求内容文本
        use_keyword_analysis: 是否强制使用关键词分析，False则根据配置决定使用AI还是关键词分析（默认False）
    
    Returns:
        str: 安全评估报告
    """
    print("analyze_security_report_fenlei")
    
    # 需求验证逻辑
    if not content or len(content.strip()) < 20 or '需求' not in content:
        return "错误：输入内容不符合需求格式要求，请提供详细的需求描述。"
    
    # 如果强制使用关键词分析，直接返回关键词分析结果
    if use_keyword_analysis:
        return analyze_by_keywords(content)
    
    # 检查AI是否启用
    ai_enabled = is_ai_enabled()
    if not ai_enabled:
        # AI未启用，默认使用关键词分析（不显示提示）
        print("[-] AI分析未启用，使用关键词分析")
        return analyze_by_keywords(content)
    
    # AI已启用，尝试使用AI分析
    print("尝试使用AI分析...")
    try:
        # 获取当前环境配置
        env_config = get_env_config()
        print("当前环境配置:", _mask_env_config_for_log(env_config))
        
        # 检查AI配置是否完整
        if not env_config.get('url') or not env_config.get('api_key'):
            print("[-] AI配置不完整，自动降级到关键词分析")
            keyword_result = analyze_by_keywords(content)
            return f"**注意：AI分析不可用（配置不完整），已自动使用关键词分析**\n\n{keyword_result}"
        
        url = env_config['url']
        headers = build_ai_request_headers(env_config)
    except Exception as e:
        print(f"[-] 获取AI配置失败: {e}，自动降级到关键词分析")
        keyword_result = analyze_by_keywords(content)
        return f"**注意：AI分析不可用（配置获取失败），已自动使用关键词分析**\n\n{keyword_result}"

    # payload = {
    #     "model": "ms-qwrz8wfk",
    #     "messages": [
    #         {
    #             "role": "system",
    #             "content": "你是一个安全分析专家，请分析下面的安全周报内容。"
    #         },
    #         {
    #             "role": "user",
    #             "content": content
    #         }
    #     ],
    #     "temperature": 0.7
    # }


    payload = {
        "model": env_config['model'],  # 从环境配置中获取 model
        "messages": [
            {
                "role": "system",
                "content": """
- Role: TAPD需求工单安全评估专家
- 新增任务：
  1. 验证输入是否为有效需求（非空框架）
  2. 对有效需求进行安全评估并提供具体安全建议
  3. 根据需求类型自动匹配安全评估模板
  4. 提供风险等级评估（高/中/低）
  5. 给出具体实施建议和代码示例

- Role: 应用安全评估专家
- Role: 应用安全评估专家
- Background: 用户需要对应用的功能进行全面的安全评估，以确保应用在涉及个人信息、账户登录注册、支付扣款消耗、上传下载导出、内容消息推送、数据统计UI以及API接口等方面的安全性，同时对新功能进行安全测试覆盖，以防止潜在的安全风险。
- Profile: 你是一位资深的应用安全评估专家，拥有丰富的信息安全经验，熟悉各类应用安全规范和最佳实践，能够精准识别和评估应用功能中的安全风险，并提供有效的加固建议。
- Skills: 你具备深入的网络安全知识、应用安全测试能力、数据加密技术、身份验证机制、风险评估方法以及新功能安全测试的全面技能，能够从多个角度对应用功能进行细致的安全评估。
- Goals: 对应用中的加固类、敏感数据类、账户登录注册类、支付扣款消耗类、上传下载导出类、内容消息推送类、数据统计UI类以及API接口类功能进行安全评估，确保应用在各个方面的安全性，并对新功能进行安全测试覆盖，以保障用户数据和应用的安全性。
- Constrains: 评估过程中应严格遵守相关法律法规和隐私政策，确保用户数据的保密性、完整性和可用性，同时评估建议应具有可操作性和实用性，能够有效提升应用的安全性。
- OutputFormat: 结构化安全评估报告，包含以下部分：
  1. 需求摘要
  2. 风险分类（数据安全/访问控制/输入验证等）
  3. 风险等级评估（高/中/低）
  4. 具体风险点描述
  5. 加固建议（含代码示例）
  6. 测试用例建议
  7. 合规性检查
- Workflow:
  1. 对应用功能进行全面的安全风险识别，包括加固类、敏感数据类、账户登录注册类、支付扣款消耗类、上传下载导出类、内容消息推送类、数据统计UI类以及API接口类功能。
  2. 根据风险识别结果，对各类功能进行详细的安全评估，分析潜在的安全漏洞和风险点。
  3. 提出针对性的加固建议，包括数据加密、身份验证增强、权限管理优化、安全审计等措施。
  4. 对新功能进行安全测试覆盖，确保新功能在上线前经过充分的安全评估和测试。
  5. 编制安全评估报告，详细记录评估过程、风险评估结果、加固建议以及安全测试覆盖情况。
- Examples:
  - 例子1：加固类功能安全评估
    - 功能描述：应用对敏感数据进行加密存储和传输。
    - 风险评估：加密算法是否符合行业标准，密钥管理是否安全。
    - 加固建议：采用强加密算法，如AES-256，确保密钥的安全存储和定期更新。
  - 例子2：账户登录注册类功能安全评估
    - 功能描述：应用使用短信验证和拖动滑块验证进行用户注册和登录。
    - 风险评估：短信验证码是否容易被拦截，拖动滑块验证是否容易被破解。
    - 加固建议：增加验证码的有效期限制，采用多因素身份验证增强安全性。
  - 例子3：支付扣款消耗类功能安全评估
    - 功能描述：应用涉及金额变动和银行卡信息处理。
    - 风险评估：支付接口是否安全，银行卡信息是否加密存储。
    - 加固建议：使用安全的支付网关，对银行卡信息进行端到端加密。
  - 例子4：上传下载导出类功能安全评估
    - 功能描述：应用提供数据上传、下载和导出功能。
    - 风险评估：上传文件是否经过安全检查，下载和导出数据是否加密。
    - 加固建议：对上传文件进行病毒扫描和内容检查，对下载和导出数据进行加密处理。
  - 例子5：内容消息推送类功能安全评估
    - 功能描述：应用推送消息内容和短信内容。
    - 风险评估：消息内容是否包含敏感信息，是否容易被篡改。
    - 加固建议：对消息内容进行加密和签名，确保消息的完整性和保密性。
  - 例子6：数据统计UI类功能安全评估
    - 功能描述：应用展示统计数据和前端UI设计。
    - 风险评估：统计数据是否经过脱敏处理，UI设计是否符合安全规范。
    - 加固建议：对统计数据进行脱敏处理，确保UI设计符合安全最佳实践。
  - 例子7：API接口类功能安全评估
    - 功能描述：应用提供API接口供第三方调用。
    - 风险评估：API接口是否进行身份验证和授权，是否容易被滥用。
    - 加固建议：对API接口进行严格的认证和授权管理，限制接口调用频率。
  - 例子8：新功能安全测试覆盖
    - 功能描述：应用开发了新的社交功能。
    - 风险评估：新功能是否经过安全测试，是否存在安全漏洞。
    - 加固建议：进行全面的安全测试，包括漏洞扫描、渗透测试等，确保新功能的安全性。
- Initialization: 在第一次对话中，请直接输出以下：您好，作为TAPD需求工单安全评估专家，我将按照以下标准流程进行评估：
  1. 需求有效性验证（内容完整性检查）
  2. 自动分类匹配评估模板（数据类/接口类/功能类等）
  3. 风险等级评估标准：
     - 高风险：可能导致数据泄露或系统入侵
     - 中风险：可能影响系统可用性或完整性
     - 低风险：轻微安全问题或优化建议
  4. 提供具体实施建议，包括：
     - 代码示例（加密/验证/日志等）
     - 配置修改建议
     - 测试用例模板
  5. 生成结构化报告

请提供详细的需求描述，我将为您生成定制化的安全评估方案。

请提供详细的需求描述，以便我开始评估工作。

                """
            },
            {
                "role": "user",
                "content": content
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()  # 抛出HTTP错误
        
        result = response.json()
        print("API返回结果:", json.dumps(result, ensure_ascii=False, indent=2))
        
        # 检查返回结构
        if 'choices' not in result:
            print("[-] API返回格式异常，自动降级到关键词分析")
            keyword_result = analyze_by_keywords(content)
            return f"**注意：AI分析返回格式异常，已自动使用关键词分析**\n\n{keyword_result}"
            
        if not result['choices'] or not isinstance(result['choices'], list):
            print("[-] API返回的choices为空或格式错误，自动降级到关键词分析")
            keyword_result = analyze_by_keywords(content)
            return f"**注意：AI分析返回数据异常，已自动使用关键词分析**\n\n{keyword_result}"
            
        # 获取AI回复内容
        ai_response = result['choices'][0]['message']['content']
        
        # 处理回复，去除思维链
        final_response = remove_thinking_chain(ai_response)
        
        # 检查AI回复是否有效（不是错误信息）
        if final_response.startswith("错误") or final_response.startswith("API调用出错"):
            print("[-] AI分析返回错误信息，自动降级到关键词分析")
            keyword_result = analyze_by_keywords(content)
            return f"**注意：AI分析失败，已自动使用关键词分析**\n\n{keyword_result}"
        
        print("[+] AI分析成功")
        return final_response
        
    except requests.exceptions.RequestException as e:
        print(f"[-] API调用出错: {str(e)}，自动降级到关键词分析")
        keyword_result = analyze_by_keywords(content)
        return f"**注意：AI分析不可用（API调用失败），已自动使用关键词分析**\n\n{keyword_result}"
    except json.JSONDecodeError as e:
        print(f"[-] JSON解析错误: {str(e)}，自动降级到关键词分析")
        keyword_result = analyze_by_keywords(content)
        return f"**注意：AI分析不可用（JSON解析失败），已自动使用关键词分析**\n\n{keyword_result}"
    except Exception as e:
        print(f"[-] 处理过程出错: {str(e)}，自动降级到关键词分析")
        keyword_result = analyze_by_keywords(content)
        return f"**注意：AI分析不可用（处理失败），已自动使用关键词分析**\n\n{keyword_result}"



def remove_thinking_chain(text):
    # 如果存在 </think>，从其后开始提取内容
    if "</think>" in text:
        text = text.split("</think>")[1].strip()
    
    # 常见的思维链结束标记
    end_markers = ["因此", "总结", "综上所述", "结论"]
    
    lines = text.split('\n')
    result_lines = []
    skip_mode = False
    
    for line in lines:
        # 跳过思维链开始部分
        if any(marker in line for marker in ["让我思考", "让我分析", "首先", "我来分析"]):
            skip_mode = True
            continue
            
        # 当遇到结论标记时，开始保留内容
        if any(marker in line for marker in end_markers):
            skip_mode = False
            continue
            
        if not skip_mode:
            result_lines.append(line)
    
    return '\n'.join(line for line in result_lines if line.strip())


def summarize_security_news(content):
    """总结每日安全资讯内容
    
    Args:
        content: 安全资讯的Markdown内容
    
    Returns:
        str: AI总结后的内容
    """
    print("开始AI总结安全资讯...")
    # 获取当前环境配置
    env_config = get_env_config()
    print("当前环境配置:", _mask_env_config_for_log(env_config))
    
    # 验证输入内容
    if not content or len(content.strip()) < 50:
        return "错误：输入内容过短，无法进行总结。"
    
    url = env_config['url']
    headers = build_ai_request_headers(env_config)
    
    payload = {
        "model": env_config['model'],
        "messages": [
            {
                "role": "system",
                "content": """你是一个安全资讯分析专家，请对每日安全资讯进行总结。
请按照以下格式输出总结：
1. 今日安全资讯概览（简要说明今日资讯的主要内容和数量）
2. 重点关注（列出3-5个最重要的安全事件或漏洞）
3. 安全趋势分析（分析今日资讯反映的安全趋势）
4. 建议关注（给出需要重点关注的安全领域或技术）

请用中文输出，内容要简洁明了，突出重点。"""
            },
            {
                "role": "user",
                "content": f"请对以下每日安全资讯进行总结：\n\n{content}"
            }
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()  # 抛出HTTP错误
        
        result = response.json()
        print("API返回结果:", json.dumps(result, ensure_ascii=False, indent=2))
        
        # 检查返回结构
        if 'choices' not in result:
            return f"API返回格式异常: {json.dumps(result, ensure_ascii=False)}"
            
        if not result['choices'] or not isinstance(result['choices'], list):
            return "API返回的choices为空或格式错误"
            
        # 获取AI回复内容
        ai_response = result['choices'][0]['message']['content']
        
        # 处理回复，去除思维链
        final_response = remove_thinking_chain(ai_response)
        
        print("AI总结完成")
        return final_response
        
    except requests.exceptions.RequestException as e:
        return f"API调用出错: {str(e)}"
    except json.JSONDecodeError as e:
        return f"JSON解析错误: {str(e)}"
    except Exception as e:
        return f"处理过程出错: {str(e)}"

# 使用示例
if __name__ == "__main__":
    # security_report = """
    # [在这里放入安全周报内容]
    # """
    # 测试用例1：使用关键词分析
    security_report_keyword = """
    需求：开发用户登录注册功能，需要支持手机号登录、短信验证码验证、密码加密存储。
    同时需要实现支付功能，支持银行卡支付和第三方支付。
    """
    
    print("=" * 50)
    print("测试1：使用关键词分析")
    print("=" * 50)
    result_keyword = analyze_security_report_fenlei(security_report_keyword, use_keyword_analysis=True)
    print(result_keyword)
    print("\n")
    
    # 测试用例2：使用AI分析（需要API配置）
    security_report_ai = """
    需求：开发用户登录注册功能，需要支持手机号登录、短信验证码验证、密码加密存储。
    同时需要实现支付功能，支持银行卡支付和第三方支付。
    """
    
    print("=" * 50)
    print("测试2：使用AI分析")
    print("=" * 50)
    result_ai = analyze_security_report_fenlei(security_report_ai, use_keyword_analysis=False)
    print(result_ai)





