@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo The project Python environment is missing. Read START_HERE.md.
  pause
  exit /b 1
)
if /I "%~1"=="--check" (
  ".venv\Scripts\python.exe" -m src.launch --check
  exit /b
)
if /I "%~1"=="--text" (
  ".venv\Scripts\python.exe" -m src.launch --text
  exit /b
)
".venv\Scripts\python.exe" -m src.launch
if errorlevel 1 (
  echo Demo launch failed. Read START_HERE.md for the terminal fallback.
  pause
)
