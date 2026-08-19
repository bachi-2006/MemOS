@echo off
title MemOS Windows Local Bridge
echo Starting MemOS Windows Local Bridge on Port 11435...
cd /d "%~dp0\.."
python scripts\memos_bridge.py
pause
