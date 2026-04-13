@echo off
cd /d %~dp0..\frontend

echo Starting Music Stream Frontend...
echo Server at http://localhost:5500
echo.

python -m http.server 5500

pause