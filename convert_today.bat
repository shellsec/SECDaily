@echo off
echo 开始执行当天Markdown转HTML处理...
echo 时间: %date% %time%
echo ===================================

:: 设置工作目录为脚本所在目录
cd /d "%~dp0"

:: 执行Python脚本
python convert_today.py

:: 检查执行结果
if %ERRORLEVEL% EQU 0 (
    echo ===================================
    echo 处理成功完成!
) else (
    echo ===================================
    echo 处理过程中出现错误，错误代码: %ERRORLEVEL%
)

