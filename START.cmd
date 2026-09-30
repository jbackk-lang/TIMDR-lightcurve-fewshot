@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" ui_server.py --port 8768
) else (
  echo Najpierw uruchom SETUP.cmd, aby przygotowac srodowisko.
)
pause
