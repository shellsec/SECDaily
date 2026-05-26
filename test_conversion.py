import os
import sys
import logging
import datetime
from pathlib import Path
import shutil
import tempfile

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_conversion.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 导入转换模块
try:
    import convert_today
    CONVERT_MODULE_AVAILABLE = True
except ImportError:
    CONVERT_MODULE_AVAILABLE = False
    logger.error("转换模块未找到，测试无法继续")

# 导入HTML验证模块
try:
    from html_validator import validate_html_file
    HTML_VALIDATOR_AVAILABLE = True
except ImportError:
    HTML_VALIDATOR_AVAILABLE = False
    logger.warning("HTML验证模块未找到，将跳过HTML验证步骤")

def create_test_markdown():
    """创建测试用的Markdown文件"""
    try:
        # 获取当前日期
        today = datetime.datetime.now()
        date_str = today.strftime('%Y-%m-%d')
        
        # 创建临时目录
        temp_dir = Path(tempfile.mkdtemp())
        logger.info(f"创建临时测试目录: {temp_dir}")
        
        # 创建测试Markdown文件
        md_file = temp_dir / f"security-news-{date_str}.md"
        
        # 生成测试内容
        content = f"""# 安全资讯日报 {date_str}

## 漏洞与威胁

### 1. 微软发布紧急安全更新修复Windows严重漏洞

**来源**: Microsoft Security Response Center

微软今日发布紧急安全更新，修复了Windows操作系统中的一个严重远程代码执行漏洞(CVE-2023-XXXXX)。该漏洞影响所有受支持的Windows版本，攻击者可以通过特制的网络请求在目标系统上执行任意代码。

**关键词**: Windows, RCE, 微软, 安全更新

### 2. 研究人员发现新型Android恶意软件在Google Play上传播

**来源**: 安全研究实验室

安全研究人员发现一种新型Android恶意软件，已经通过伪装成实用工具和游戏在Google Play商店上传播。该恶意软件能够窃取用户的银行凭证和个人信息。

**关键词**: Android, 恶意软件, Google Play, 数据窃取

## 安全研究

### 1. 研究团队发布AI安全框架评估报告

**来源**: 网络安全研究中心

一个国际研究团队发布了针对AI系统安全性的综合评估框架，该框架提供了一套标准化的方法来评估AI系统的安全性和隐私保护能力。

**关键词**: AI安全, 评估框架, 隐私保护

## 安全产业动态

### 1. 某安全公司完成新一轮融资

**来源**: 安全产业新闻

知名网络安全公司今日宣布完成5亿美元融资，计划加强云安全和零信任网络解决方案的研发。

**关键词**: 融资, 云安全, 零信任网络

## 合规与标准

### 1. 新数据保护法规将于下月生效

**来源**: 法律法规资讯

新的数据保护法规将于下月正式生效，要求企业加强个人数据保护措施，违规企业将面临高额罚款。

**关键词**: 数据保护, 法规, 合规
"""
        
        # 写入文件
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"成功创建测试Markdown文件: {md_file}")
        return temp_dir, md_file
        
    except Exception as e:
        logger.error(f"创建测试Markdown文件时出错: {e}")
        return None, None

def test_conversion_process():
    """测试转换流程"""
    if not CONVERT_MODULE_AVAILABLE:
        logger.error("转换模块不可用，测试终止")
        return False
    
    temp_dir = None
    try:
        # 创建测试文件
        temp_dir, md_file = create_test_markdown()
        if not md_file:
            logger.error("创建测试文件失败，测试终止")
            return False
        
        # 备份原始配置
        original_input_dir = convert_today.INPUT_DIR
        original_output_dir = convert_today.OUTPUT_DIR
        original_archive_dir = convert_today.ARCHIVE_DIR
        original_template_file = convert_today.TEMPLATE_FILE
        
        # 设置测试配置
        convert_today.INPUT_DIR = temp_dir
        convert_today.OUTPUT_DIR = temp_dir
        convert_today.ARCHIVE_DIR = temp_dir / "archive"
        convert_today.TEMPLATE_FILE = temp_dir / "template.html"
        
        # 创建模板文件
        template_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }
        h2 {
            color: #444;
            margin-top: 30px;
        }
        h3 {
            color: #555;
        }
        .date {
            color: #777;
            font-style: italic;
        }
        .footer {
            margin-top: 50px;
            border-top: 1px solid #eee;
            padding-top: 10px;
            color: #777;
            font-size: 0.9em;
        }
        .stats-line {
            background-color: #f8f8f8;
            padding: 10px;
            margin: 20px 0;
            border-radius: 5px;
            font-size: 0.9em;
            color: #555;
        }
        .stat-separator {
            margin: 0 10px;
            color: #ccc;
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <div class="date">{{ date }}</div>
    
    {{ content }}
    
    <div class="footer">
        &copy; {{ year }} 安全资讯日报
    </div>
</body>
</html>
"""
        with open(convert_today.TEMPLATE_FILE, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        logger.info(f"成功创建测试模板文件: {convert_today.TEMPLATE_FILE}")
        
        # 运行转换程序
        logger.info("开始运行转换程序...")
        result = convert_today.main()
        
        # 检查结果
        if result:
            logger.info("转换程序执行成功")
            
            # 检查HTML文件是否生成
            html_file = md_file.with_suffix('.html')
            if html_file.exists():
                logger.info(f"HTML文件已生成: {html_file}")
                
                # 验证HTML文件
                if HTML_VALIDATOR_AVAILABLE:
                    logger.info("开始验证生成的HTML文件...")
                    validation_result = validate_html_file(str(html_file))
                    
                    if validation_result['valid']:
                        if not validation_result['warnings']:
                            logger.info("HTML验证通过，没有警告")
                        else:
                            logger.warning(f"HTML验证通过，但有 {len(validation_result['warnings'])} 个警告")
                            for warning in validation_result['warnings']:
                                logger.warning(f"HTML警告: {warning}")
                        
                        logger.info("测试完成: 成功")
                        return True
                    else:
                        logger.error(f"HTML验证失败，有 {len(validation_result['errors'])} 个错误")
                        for error in validation_result['errors']:
                            logger.error(f"HTML错误: {error}")
                        
                        logger.error("测试完成: 失败 (HTML验证未通过)")
                        return False
                else:
                    logger.warning("HTML验证模块不可用，跳过验证步骤")
                    logger.info("测试完成: 成功 (但未进行HTML验证)")
                    return True
            else:
                logger.error(f"HTML文件未生成: {html_file}")
                logger.error("测试完成: 失败 (未生成HTML文件)")
                return False
        else:
            logger.error("转换程序执行失败")
            logger.error("测试完成: 失败 (转换程序执行失败)")
            return False
            
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        logger.error("测试完成: 失败 (发生异常)")
        return False
        
    finally:
        # 恢复原始配置
        if CONVERT_MODULE_AVAILABLE:
            convert_today.INPUT_DIR = original_input_dir
            convert_today.OUTPUT_DIR = original_output_dir
            convert_today.ARCHIVE_DIR = original_archive_dir
            convert_today.TEMPLATE_FILE = original_template_file
        
        # 清理临时目录
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"已清理临时测试目录: {temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录时出错: {e}")

def main():
    """主函数"""
    logger.info("开始测试转换和验证流程")
    
    if test_conversion_process():
        print("测试成功: 转换和验证流程正常工作")
        return 0
    else:
        print("测试失败: 转换或验证流程出现问题")
        return 1

if __name__ == '__main__':
    sys.exit(main())