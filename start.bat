@echo off
title MemOS - Adaptive Memory & LLM Engine
cd /d "%~dp0"

echo =====================================================================
echo   Starting MemOS Full-Stack Application
echo =====================================================================

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python 3.10 or higher from https://python.org
    pause
    exit /b 1
)

python run_app.py %*

if errorlevel 1 (
    echo.
    echo [ERROR] MemOS encountered an unexpected error.
    pause
)
