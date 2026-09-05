@echo off
setlocal
title MemOS Phase 2 Backup UI
set DIR=%~dp0
set PORT=5150

echo Starting Phase 2 Backup Build UI on http://127.0.0.1:%PORT%/chat.html
start "" http://127.0.0.1:%PORT%/chat.html
python -m http.server %PORT% --bind 127.0.0.1 --directory "%DIR%"

endlocal