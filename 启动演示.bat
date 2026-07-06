@echo off
chcp 65001 >nul
title Surya OCR 实时演示系统
echo ====================================
echo   Surya OCR 实时演示系统
echo   Surya 0.17.x - 90+ 语言 OCR
echo ====================================
echo.
echo 正在启动 Streamlit 服务...
echo.
set PYTHONIOENCODING=utf-8
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
"C:\Users\35160\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run "%~dp0surya_demo.py" --server.port 8501
echo.
pause
