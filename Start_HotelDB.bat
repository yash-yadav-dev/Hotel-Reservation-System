@echo off
cd /d "%~dp0"
py -c "import tkcalendar" >nul 2>&1
if errorlevel 1 (
    echo Installing required package: tkcalendar
    py -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Could not install dependencies. Check your internet connection and Python installation.
        pause
        exit /b 1
    )
)
py app\main.py
if errorlevel 1 pause
