@echo off
echo ========================================
echo Music Stream - Windows Setup
echo ========================================

cd /d %~dp0..\backend

echo.
echo [1/4] Creating virtual environment...
python -m venv venv

echo.
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [3/4] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [4/4] Setting up configuration...
if not exist .env (
    copy .env.example .env
    echo Created .env file. Please edit it with your settings.
)

echo.
echo ========================================
echo Setup completed!
echo.
echo Next steps:
echo 1. Edit backend\.env file with your settings
echo 2. Run: scripts\start_backend.bat
echo 3. In another terminal: scripts\start_frontend.bat
echo ========================================

pause