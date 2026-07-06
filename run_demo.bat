@echo off
chcp 65001 >nul
title Surya OCR Demo
echo ==============================
echo   Surya OCR Demo
echo ==============================
echo.
echo Starting Streamlit...
echo.
set PYTHONIOENCODING=utf-8
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
"C:\Users\35160\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run "%~dp0surya_demo.py" --server.port 8501
echo.
pause
