import os
import sys
import logging
from pathlib import Path
import re
from html.parser import HTMLParser

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("html_validator.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class HTMLValidationParser(HTMLParser):
    """HTML验证解析器，用于检查HTML文件的基本结构和有效性"""
    
    def __init__(self):
        super().__init__()
        self.tags = []
        self.errors = []
        self.warnings = []
        self.has_title = False
        self.has_body = False
        self.has_head = False
        self.has_html = False
        self.line_number = 1
        self.column_number = 0
        self.current_data = ""
    
    def update_position(self, data):
        """更新当前解析位置"""
        lines = data.split('\n')
        if len(lines) > 1:
            self.line_number += len(lines) - 1
            self.column_number = len(lines[-1])
        else:
            self.column_number += len(data)
    
    def handle_starttag(self, tag, attrs):
        """处理开始标签"""
        self.update_position(self.current_data)
        self.current_data = ""
        
        self.tags.append((tag, self.line_number, self.column_number))
        
        if tag == 'html':
            self.has_html = True
        elif tag == 'head':
            self.has_head = True
        elif tag == 'body':
            self.has_body = True
        elif tag == 'title':
            self.has_title = True
        
        # 检查属性
        for attr_name, attr_value in attrs:
            if attr_value and ('<' in attr_value or '>' in attr_value):
                self.warnings.append(f"行 {self.line_number}: 属性 '{attr_name}' 包含可能的HTML标签: {attr_value}")
    
    def handle_endtag(self, tag):
        """处理结束标签"""
        self.update_position(self.current_data)
        self.current_data = ""
        
        # 检查标签是否匹配
        if self.tags and self.tags[-1][0] == tag:
            self.tags.pop()
        else:
            # 查找匹配的开始标签
            found = False
            for i in range(len(self.tags) - 1, -1, -1):
                if self.tags[i][0] == tag:
                    found = True
                    # 记录嵌套错误
                    for j in range(i + 1, len(self.tags)):
                        self.errors.append(f"行 {self.tags[j][1]}: 标签 <{self.tags[j][0]}> 未正确关闭")
                    # 移除所有直到匹配标签的标签
                    self.tags = self.tags[:i]
                    break
            
            if not found:
                self.errors.append(f"行 {self.line_number}: 结束标签 </{tag}> 没有匹配的开始标签")
    
    def handle_data(self, data):
        """处理文本数据"""
        self.current_data = data
    
    def check_structure(self):
        """检查HTML基本结构"""
        if not self.has_html:
            self.warnings.append("缺少 <html> 标签")
        if not self.has_head:
            self.warnings.append("缺少 <head> 标签")
        if not self.has_body:
            self.warnings.append("缺少 <body> 标签")
        if not self.has_title:
            self.warnings.append("缺少 <title> 标签")
        
        # 检查未关闭的标签
        for tag, line, col in self.tags:
            self.errors.append(f"行 {line}: 标签 <{tag}> 未关闭")
    
    def get_result(self):
        """获取验证结果"""
        self.check_structure()
        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings
        }

def validate_html_file(file_path):
    """验证HTML文件的有效性"""
    try:
        logger.info(f"开始验证HTML文件: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return {
                'valid': False,
                'errors': [f"文件不存在: {file_path}"],
                'warnings': []
            }
        
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                logger.error(f"文件为空: {file_path}")
                return {
                    'valid': False,
                    'errors': [f"文件为空: {file_path}"],
                    'warnings': []
                }
                
            logger.info(f"成功读取文件，大小: {len(content)} 字节")
        except Exception as e:
            logger.error(f"读取文件时出错: {e}")
            return {
                'valid': False,
                'errors': [f"读取文件时出错: {str(e)}"],
                'warnings': []
            }
        
        # 基本检查
        basic_errors = []
        basic_warnings = []
        
        # 检查DOCTYPE声明
        if not re.search(r'<!DOCTYPE\s+html>', content, re.IGNORECASE):
            basic_warnings.append("缺少 DOCTYPE 声明")
        
        # 检查字符集声明
        if not re.search(r'<meta\s+charset=["\']utf-8["\']', content, re.IGNORECASE) and \
           not re.search(r'<meta\s+http-equiv=["\']Content-Type["\'].*charset=utf-8', content, re.IGNORECASE):
            basic_warnings.append("缺少 UTF-8 字符集声明")
        
        # 检查基本HTML结构
        parser = HTMLValidationParser()
        try:
            parser.feed(content)
            result = parser.get_result()
            
            # 合并基本检查结果
            result['errors'] = basic_errors + result['errors']
            result['warnings'] = basic_warnings + result['warnings']
            
            if result['valid'] and not result['warnings']:
                logger.info(f"HTML文件验证通过: {file_path}")
            elif result['valid']:
                logger.warning(f"HTML文件验证通过，但有 {len(result['warnings'])} 个警告: {file_path}")
            else:
                logger.error(f"HTML文件验证失败，有 {len(result['errors'])} 个错误: {file_path}")
            
            return result
        except Exception as e:
            logger.error(f"解析HTML时出错: {e}")
            return {
                'valid': False,
                'errors': [f"解析HTML时出错: {str(e)}"] + basic_errors,
                'warnings': basic_warnings
            }
            
    except Exception as e:
        logger.error(f"验证过程中发生严重错误: {e}")
        return {
            'valid': False,
            'errors': [f"验证过程中发生严重错误: {str(e)}"],
            'warnings': []
        }

def validate_directory(directory_path, recursive=True, file_pattern="*.html"):
    """验证目录中的所有HTML文件"""
    try:
        logger.info(f"开始验证目录中的HTML文件: {directory_path}")
        
        if not os.path.exists(directory_path):
            logger.error(f"目录不存在: {directory_path}")
            return {
                'total_files': 0,
                'valid_files': 0,
                'invalid_files': 0,
                'results': {}
            }
        
        # 获取所有HTML文件
        path_obj = Path(directory_path)
        if recursive:
            html_files = list(path_obj.glob(f"**/{file_pattern}"))
        else:
            html_files = list(path_obj.glob(file_pattern))
        
        logger.info(f"找到 {len(html_files)} 个HTML文件")
        
        # 验证每个文件
        results = {}
        valid_count = 0
        invalid_count = 0
        
        for html_file in html_files:
            file_path = str(html_file)
            result = validate_html_file(file_path)
            results[file_path] = result
            
            if result['valid']:
                valid_count += 1
            else:
                invalid_count += 1
        
        summary = {
            'total_files': len(html_files),
            'valid_files': valid_count,
            'invalid_files': invalid_count,
            'results': results
        }
        
        logger.info(f"验证完成: 总共 {len(html_files)} 个文件，{valid_count} 个有效，{invalid_count} 个无效")
        return summary
        
    except Exception as e:
        logger.error(f"验证目录时发生严重错误: {e}")
        return {
            'total_files': 0,
            'valid_files': 0,
            'invalid_files': 0,
            'results': {}
        }

def print_validation_report(validation_result, verbose=False):
    """打印验证报告"""
    if isinstance(validation_result, dict) and 'results' in validation_result:
        # 目录验证结果
        print(f"\n=== HTML验证报告 ===")
        print(f"总文件数: {validation_result['total_files']}")
        print(f"有效文件: {validation_result['valid_files']}")
        print(f"无效文件: {validation_result['invalid_files']}")
        
        if verbose and validation_result['invalid_files'] > 0:
            print("\n无效文件详情:")
            for file_path, result in validation_result['results'].items():
                if not result['valid']:
                    print(f"\n文件: {file_path}")
                    print("错误:")
                    for error in result['errors']:
                        print(f"  - {error}")
                    if result['warnings']:
                        print("警告:")
                        for warning in result['warnings']:
                            print(f"  - {warning}")
    else:
        # 单文件验证结果
        print(f"\n=== HTML验证报告 ===")
        print(f"验证状态: {'有效' if validation_result['valid'] else '无效'}")
        
        if validation_result['errors']:
            print("\n错误:")
            for error in validation_result['errors']:
                print(f"  - {error}")
        
        if validation_result['warnings']:
            print("\n警告:")
            for warning in validation_result['warnings']:
                print(f"  - {warning}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HTML文件验证工具')
    parser.add_argument('path', help='要验证的HTML文件或目录路径')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归验证目录中的所有HTML文件')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细报告')
    parser.add_argument('-p', '--pattern', default='*.html', help='文件匹配模式 (默认: *.html)')
    
    args = parser.parse_args()
    
    path = args.path
    
    if os.path.isfile(path):
        result = validate_html_file(path)
        print_validation_report(result, args.verbose)
    elif os.path.isdir(path):
        result = validate_directory(path, args.recursive, args.pattern)
        print_validation_report(result, args.verbose)
    else:
        print(f"错误: 路径不存在 - {path}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())