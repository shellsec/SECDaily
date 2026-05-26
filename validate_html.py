import os
import sys
import logging
from pathlib import Path
from html_validator import validate_html_file, validate_directory, print_validation_report

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("validate_html.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """主函数：验证HTML文件或目录"""
    try:
        import argparse
        
        parser = argparse.ArgumentParser(description='验证HTML文件或目录')
        parser.add_argument('path', help='要验证的HTML文件或目录路径')
        parser.add_argument('-r', '--recursive', action='store_true', help='递归验证目录中的所有HTML文件')
        parser.add_argument('-v', '--verbose', action='store_true', help='显示详细报告')
        
        args = parser.parse_args()
        
        path = args.path
        path_obj = Path(path)
        
        logger.info(f"开始验证: {path}")
        
        if path_obj.is_file():
            logger.info(f"验证单个文件: {path}")
            result = validate_html_file(path)
            print_validation_report(result, args.verbose)
            
            if result['valid']:
                logger.info(f"文件验证通过: {path}")
                return 0
            else:
                logger.error(f"文件验证失败: {path}")
                return 1
                
        elif path_obj.is_dir():
            logger.info(f"验证目录: {path} (递归: {args.recursive})")
            result = validate_directory(path, args.recursive)
            print_validation_report(result, args.verbose)
            
            if result['invalid_files'] == 0:
                logger.info(f"所有文件验证通过: {path}")
                return 0
            else:
                logger.warning(f"有 {result['invalid_files']} 个文件验证失败: {path}")
                return 1
                
        else:
            logger.error(f"路径不存在: {path}")
            print(f"错误: 路径不存在 - {path}")
            return 1
            
    except Exception as e:
        logger.error(f"验证过程中发生错误: {e}")
        print(f"错误: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())