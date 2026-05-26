@echo off
SETLOCAL


:: 运行转换脚本
echo 正在转换Markdown文件为HTML...
python md_to_html.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo HTML文件转换成功!
    echo 生成的HTML文件位于: archive目录
    echo 主索引文件: archive\index.html
    echo ========================================
    echo.
) else (
    echo.
    echo [错误] 转换过程中出现错误
    echo.
)

