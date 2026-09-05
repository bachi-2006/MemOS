@echo off
setlocal
title MemOS Phase 2 Full-Stack UI
set ROOT=%~dp0

if not exist "%ROOT%frontend\dist\index.html" (
  echo Building frontend...
  pushd "%ROOT%frontend"
  call npm install >nul 2>&1
  call npm run build
  popd
)

echo Starting MemOS Phase 2 API on http://127.0.0.1:5151
start "" http://127.0.0.1:5151
python "%ROOT%backend\run.py"

endlocal