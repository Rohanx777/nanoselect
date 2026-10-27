@echo off
setlocal
if not exist "%~dp0nanomaterial_hybrid\START_DEMO.cmd" (
  echo Cannot find the demo in the nanomaterial_hybrid folder.
  pause
  exit /b 1
)
if /I "%~1"=="--check" (
  call "%~dp0nanomaterial_hybrid\START_DEMO.cmd" --check
  exit /b
)
if /I "%~1"=="--text" (
  call "%~dp0nanomaterial_hybrid\START_DEMO.cmd" --text
  exit /b
)
call "%~dp0nanomaterial_hybrid\START_DEMO.cmd"
