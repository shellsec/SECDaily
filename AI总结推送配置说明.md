# AI总结推送配置说明

## ✅ 已实现功能

1. **config.json 配置**
   - 添加了 `AISummary` 配置段
   - 支持启用/禁用AI总结推送
   - 支持企业微信和钉钉两种推送方式

2. **推送功能**
   - 企业微信应用推送（使用corpid、corpsecret、agentid）
   - 钉钉机器人推送（使用access_token和secret）
   - 推送不记录日志（静默推送）
   - AI总结为空时不推送

3. **自动化流程**
   - 生成AI总结后自动推送
   - 在生成HTML报告后推送
   - 如果AI总结为空或出错，不推送

## 📋 配置说明

### config.json + .env 配置

密钥请写入 `.env`（参考 `.env.example`），`config.json` 只保留开关和结构（参考 `config.example.json`）：

```json
{
    "AISummary": {
        "enabled": true,
        "wechat": {
            "enabled": true,
            "secrets_corpid": "WECOM_CORPID",
            "secrets_corpsecret": "WECOM_CORPSECRET",
            "secrets_agentid": "WECOM_AGENTID",
            "corpid": "",
            "corpsecret": "",
            "agentid": ""
        },
        "dingtalk": {
            "enabled": true,
            "secrets_access_token": "DINGTALK_ACCESS_TOKEN",
            "secrets_secret": "DINGTALK_SECRET",
            "access_token": "",
            "secret": ""
        }
    }
}
```

对应 `.env` 示例：

```env
WECOM_CORPID=your-corp-id
WECOM_CORPSECRET=your-corp-secret
WECOM_AGENTID=1000002
DINGTALK_ACCESS_TOKEN=your-dingtalk-token
DINGTALK_SECRET=your-dingtalk-secret
```

### 配置项说明

- **enabled**: 总开关，控制是否启用AI总结推送
- **wechat.enabled**: 企业微信推送开关
- **wechat.corpid**: 企业ID
- **wechat.corpsecret**: 应用密钥
- **wechat.agentid**: 应用ID
- **dingtalk.enabled**: 钉钉推送开关
- **dingtalk.access_token**: 钉钉机器人access_token
- **dingtalk.secret**: 钉钉机器人密钥（可选，用于签名验证）

## 🔄 工作流程

1. **收集安全资讯** → 生成Markdown文件
2. **调用AI总结** → 生成AI总结内容
3. **保存AI总结** → 保存到 `AISummary日期.md`
4. **生成HTML报告** → 包含AI总结的HTML页面
5. **推送AI总结**（如果启用且AI总结不为空）
   - 企业微信推送
   - 钉钉推送

## 📝 推送规则

1. **推送条件**：
   - `AISummary.enabled` 为 `true`
   - AI总结内容不为空
   - AI总结不包含错误信息

2. **推送内容**：
   - 标题：`🤖 AI安全资讯总结 - 日期`
   - 内容：完整的AI总结文本

3. **推送方式**：
   - 企业微信：应用消息推送（@all）
   - 钉钉：Markdown格式消息

4. **错误处理**：
   - 推送失败不记录日志
   - 推送失败不影响主流程
   - 静默失败，不影响其他功能

## 🚀 使用方法

### 启用推送

1. 在 `config.json` 中设置 `AISummary.enabled` 为 `true`
2. 配置对应的推送渠道（企业微信或钉钉）
3. 设置对应渠道的 `enabled` 为 `true`
4. 填写正确的配置信息

### 禁用推送

1. 设置 `AISummary.enabled` 为 `false`（禁用所有推送）
2. 或设置对应渠道的 `enabled` 为 `false`（禁用特定渠道）

## ⚙️ 企业微信配置获取

1. 登录企业微信管理后台
2. 进入"应用管理" → "自建应用"
3. 创建或选择应用
4. 获取：
   - **corpid**: 企业ID（在"我的企业" → "企业信息"中查看）
   - **corpsecret**: 应用密钥（在应用详情中查看）
   - **agentid**: 应用ID（在应用详情中查看）

## ⚙️ 钉钉配置获取

1. 登录钉钉管理后台
2. 进入"工作台" → "智能群助手"
3. 创建自定义机器人
4. 获取：
   - **access_token**: 机器人的access_token
   - **secret**: 机器人的密钥（安全设置中）

## 📊 推送示例

### 企业微信推送格式

```
🤖 AI安全资讯总结 - 2025-11-06

1. 今日安全资讯概览
...

2. 重点关注
...

3. 安全趋势分析
...

4. 建议关注
...
```

### 钉钉推送格式

Markdown格式，标题为"AI安全资讯总结"，内容为完整的AI总结文本。

## ✅ 验证

运行程序后，检查：
1. AI总结是否生成（`archive/年份/AISummary日期.md`）
2. 企业微信/钉钉是否收到推送消息
3. 如果AI总结为空，确认不推送

## 🔧 故障排查

### 推送失败

1. 检查配置是否正确
2. 检查网络连接
3. 检查企业微信/钉钉配置是否有效
4. 查看程序输出（虽然不记录日志，但可能有错误信息）

### AI总结为空

- 检查AI API配置
- 检查网络连接
- 查看AI总结生成日志

