@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   门店经营 ChatBI 演示
echo ========================================
echo.
echo [1/2] 检查数据库...
if not exist data\retail.db (
    echo 数据库不存在，正在生成...
    python data\generate_data.py
)
echo.
echo [2/2] 启动服务，浏览器打开 http://localhost:8000
echo 按 Ctrl+C 停止
echo.
python -m uvicorn app.main:app --reload --port 8000
pause
