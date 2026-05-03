@echo off
REM Start Django with Channels support using Daphne ASGI server
echo Starting Django Realtime Chat Application...
echo.
echo Make sure Redis is running: docker-compose up -d
echo.

REM Check if Daphne is installed
python -c "import daphne" >nul 2>&1
if errorlevel 1 (
    echo Installing Daphne...
    pip install daphne
)

echo.
echo Starting Daphne ASGI server on http://127.0.0.1:8000
echo Press Ctrl+C to stop
echo.

python manage.py runserver --asgi 0.0.0.0:8000
