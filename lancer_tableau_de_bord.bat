@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Environnement Python introuvable. Cree d'abord le venv et installe requirements.txt.
    pause
    exit /b 1
)
.venv\Scripts\python.exe -m src.web_ui
pause
