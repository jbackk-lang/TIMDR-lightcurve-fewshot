@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements-lock.txt
if errorlevel 1 goto fail
echo Gotowe. Uruchom START.cmd.
pause
exit /b 0
:fail
echo Instalacja nie powiodla sie. Sprawdz komunikat powyzej i dostepnosc Python 3.12.
pause
exit /b 1
