@echo off
echo ============================================
echo  CAN Bus IDS - Setup and Launch
echo  NMAM Institute of Technology
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Download from https://www.python.org/downloads/
    pause & exit /b 1
)

echo [1/4] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 ( echo [ERROR] pip install failed. & pause & exit /b 1 )

echo.
echo [2/4] Creating upload folder...
if not exist "static\uploads" mkdir "static\uploads"

echo.
echo [3/4] Training demo ML model (synthetic data)...
python ml/train.py --demo
if errorlevel 1 ( echo [WARN] Model training failed - will use heuristic mode. )

echo.
echo [4/4] Starting Flask server...
echo.
echo  Open your browser at:  http://127.0.0.1:5000
echo  Press CTRL+C to stop the server.
echo.
python app.py
pause
