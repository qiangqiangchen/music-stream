@echo off
cd /d %~dp0..\backend

echo ========================================
echo Music Stream Backend Startup
echo ========================================
echo.

call venv\Scripts\activate.bat

echo [1/3] Installing missing dependencies...
pip install email-validator==2.1.0 --quiet

echo.
echo [2/3] Initializing database...
python ..\scripts\init_db.py

echo.
echo [3/3] Creating admin user...
python ..\scripts\create_admin.py

echo.
echo ========================================
echo Starting server...
echo ========================================
echo.
echo Backend URL: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo Health Check: http://localhost:8000/healthz
echo.
echo Press CTRL+C to stop the server
echo ========================================
echo.

python run.py

pause