# SECDaily

## ☕ 请我喝可乐

开源不易，欢迎赞助支持：  
👉 [爱发电](https://ifdian.net/a/shellsec)

## 项目简介

SECDaily 是一个安全资讯聚合工具，用于自动收集、整理和推送安全相关的 RSS 资讯。该工具可以自动从多个 RSS 源收集安全资讯，生成 Markdown 和 HTML 格式的日报，并提供 AI 总结和多种推送方式。

## 功能特点

- 🔄 **RSS自动更新**：支持自动检查并更新RSS源文件，防止源失效导致数据丢失
- 📰 **多源聚合**：支持从多个RSS源收集安全资讯
- 🤖 **AI智能总结**：自动对收集的资讯进行AI分析和总结
- 🔍 **关键词分析**：基于关键词匹配的安全需求分析，无需AI即可使用
- 🔄 **智能降级**：AI分析失败时自动降级到关键词分析，确保功能可用
- 📄 **多格式输出**：自动生成Markdown和HTML格式的日报
- 📤 **多渠道推送**：支持企业微信、钉钉、Telegram、邮件等多种推送方式
- ⏰ **定时任务**：支持定时自动执行，无需人工干预
- 🛡️ **安全保护**：更新RSS时验证内容有效性，防止覆盖本地有效数据

## 文件结构

- `yarb.py`: 主程序（支持定时任务和AI总结）
- `yarb_one.py`: 简化版主程序
- `config.json`: 配置文件（RSS源、推送方式等）
- `convert_today.py`: Markdown转HTML工具
- `oneapi.py`: AI总结功能
- `bot.py`: 推送机器人实现
- `rss/`: RSS源文件目录

## 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `feedparser`: RSS解析
- `listparser`: OPML解析
- `requests`: HTTP请求
- `schedule`: 定时任务
- `markdown`: Markdown转换
- `jinja2`: HTML模板渲染

## 使用方法

### 启动定时任务

```bash
# 默认每天10:00执行
python yarb.py

# 立即执行一次（测试用）
python yarb.py --force

# 自定义执行时间
python yarb.py --cron "11:00"

# 强制更新RSS源
python yarb.py --update
```

### 手动转换HTML

```bash
python convert_today.py
```

## 配置说明

### RSS源配置 (`config.json`)

```json
{
    "rss": {
        "auto_update": {
            "enabled": true,              // 是否启用自动更新
            "update_interval_days": 7     // 更新间隔（天）
        },
        "CustomRSS": {
            "enabled": true,
            "filename": "CustomRSS.opml"
        },
        "CyberSecurityRSS": {
            "enabled": true,
            "url": "https://...",
            "filename": "CyberSecurityRSS.opml"
        }
    }
}
```

### RSS自动更新功能

#### 功能说明

- **自动检查**：程序启动时自动检查RSS源文件是否需要更新
- **时间判断**：根据文件修改时间和配置的更新间隔判断是否需要更新
- **安全验证**：更新前验证下载内容的有效性，防止覆盖本地有效数据
- **失败保护**：如果远程源失效或内容无效，保留本地文件

#### 更新机制

1. **检查时机**：每次启动任务前自动检查
2. **更新条件**：
   - 文件不存在
   - 文件超过 `update_interval_days` 天未更新
3. **验证流程**：
   - 检查内容是否为空
   - 验证OPML格式是否正确
   - 检查是否包含有效的feed
4. **安全保护**：
   - 使用临时文件保存新内容
   - 验证通过后才替换原文件
   - 验证失败时保留本地文件

#### 配置选项

- `auto_update.enabled`: 启用/禁用自动更新（默认：`true`）
- `auto_update.update_interval_days`: 更新间隔天数（默认：`7`）

### AI分析配置 (`config.json`)

```json
{
    "AISummary": {
        "enabled": false,              // 是否启用AI分析（false时默认使用关键词分析）
        "wechat": {
            "enabled": false,
            "corpid": "...",
            "corpsecret": "...",
            "agentid": "..."
        },
        "dingtalk": {
            "enabled": false,
            "access_token": "...",
            "secret": "..."
        }
    }
}
```

#### AI分析与关键词分析

**安全需求分析功能** (`analyze_security_report_fenlei`) 支持两种分析模式：

1. **AI分析模式**（需要配置）
   - 当 `AISummary.enabled = true` 时启用
   - 使用AI模型进行深度安全评估
   - 提供更详细和个性化的分析结果

2. **关键词分析模式**（默认）
   - 当 `AISummary.enabled = false` 时自动使用
   - 基于预定义关键词库进行匹配分析
   - 无需AI配置即可使用
   - 支持8个安全类别：敏感数据类、账户登录注册类、支付扣款消耗类、上传下载导出类、内容消息推送类、数据统计UI类、API接口类、加固类

3. **自动降级机制**
   - AI分析失败时自动降级到关键词分析
   - 确保功能始终可用
   - 降级时会显示提示信息

#### 使用示例

```python
from oneapi import analyze_security_report_fenlei

# 根据配置自动选择分析方式
result = analyze_security_report_fenlei(content)

# 强制使用关键词分析
result = analyze_security_report_fenlei(content, use_keyword_analysis=True)
```

### 推送配置

支持多种推送方式，详见 `config.json` 中的 `bot` 和 `AISummary` 配置段。

## 最近改进

1. **RSS自动更新功能**：添加了自动检查和更新RSS源文件的功能，支持配置更新间隔
2. **安全保护机制**：更新RSS时验证内容有效性，防止远程源失效导致本地数据丢失
3. **AI智能总结**：集成AI总结功能，自动分析和总结安全资讯
4. **关键词分析功能**：新增基于关键词的安全需求分析功能，支持8个安全类别自动识别
5. **智能降级机制**：AI分析失败时自动降级到关键词分析，确保功能始终可用
6. **多渠道推送**：支持企业微信、钉钉等多种推送方式
7. **增强错误处理**：完善的错误处理和日志记录机制

## 日志记录

程序运行过程中的日志会记录在以下文件中：

- `yarb.log`: 主程序运行日志
- `convert_today.log`: HTML转换日志

## 错误处理

程序包含完善的错误处理机制，包括：

1. RSS源更新失败时保留本地文件
2. 内容验证失败时拒绝更新
3. 网络请求超时处理（30秒）
4. Markdown解析错误处理
5. HTML生成错误处理
6. AI分析失败时的自动降级处理（自动切换到关键词分析）
7. AI配置缺失时的静默降级（不显示提示，直接使用关键词分析）

## RSS更新安全机制

### 保护措施

1. **内容验证**：下载后验证内容非空且格式正确
2. **OPML解析**：验证OPML格式并检查feed数量
3. **原子更新**：使用临时文件，验证通过后才替换
4. **失败回退**：验证失败时保留本地文件，不覆盖

### 更新日志示例

```
[+] 文件超过 7 天未更新，需要更新：CyberSecurityRSS (上次更新: 2025-01-15 10:00:00)
[+] 更新完成：CyberSecurityRSS (包含 150 个feed)
```

如果更新失败：
```
[-] 更新失败 (OPML解析失败: ...)，保留旧文件：CyberSecurityRSS
```

## GitHub Pages 部署（含全站搜索）

归档目录可通过 GitHub Actions 自动发布为静态站点，**标题搜索**与**日期归档**在 Pages 上均可使用。

### 需要配置 GitHub 密钥吗？

**不需要。** 本工作流只发布 `archive/` 里的静态文件，并在 CI 里根据已有 Markdown 生成 `search-index.json`。  
GitHub 会自动提供 `GITHUB_TOKEN`，无需在仓库 Settings → Secrets 里添加任何密钥。

若将来要让 Actions **自动跑日报抓取**（`yarb.py`），才需要单独配置钉钉、企业微信、AI 等 Secrets；与当前 Pages 部署无关。

### 一次性开启步骤

1. 将代码推送到 GitHub（分支 `main` 或 `master`）。
2. 仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。
3. 推送包含 `archive/` 的提交，或到 **Actions** 手动运行 **Deploy GitHub Pages**。
4. 部署完成后访问：`https://<用户名>.github.io/<仓库名>/`（首页即归档索引）。

### 搜索说明

| 功能 | 说明 |
|------|------|
| 日期归档 | 在首页按年月过滤，无需额外文件 |
| 标题搜索 | 依赖 CI 生成的 `search-index.json`（约 16MB，首次加载可能稍慢） |
| 日报内筛选 | 单日 HTML 页内「筛选标题或 CVE」为本地过滤，始终可用 |

`archive/search-index.json` 仍在 `.gitignore` 中，由 CI 在每次部署前生成，避免把大文件提交进 Git 历史。

### 本地预览归档站

```bash
pip install markdown jinja2
python scripts/build_archive_site.py
cd archive && python -m http.server 8080
```

浏览器打开 `http://127.0.0.1:8080/` 即可测试搜索。

## 贡献指南

欢迎提交问题报告和改进建议。如果您想贡献代码，请确保：

1. 代码符合PEP 8风格指南
2. 添加适当的注释和文档
3. 包含测试用例
4. 提交前运行测试确保功能正常

## 致谢

本项目基于 [VulnTotal-Team/yarb](https://github.com/VulnTotal-Team/yarb) 二次开发，感谢原作者开源贡献。

## 许可证

MIT