@echo off
cls
echo ========================================================
echo  Professional CV Screening System v2.0
echo  Enterprise AI-Powered Recruitment Platform
echo ========================================================
echo.
echo This will install:
echo  - Advanced AI models (768D embeddings)
echo  - Multi-industry support (8 fields)
echo  - Dynamic weighting system
echo  - Analytics dashboard
echo.
pause

cd /d "%~dp0"

echo.
echo [1/7] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.11 from python.org
    pause
    exit /b 1
)
python --version
echo.

echo [2/7] Removing old installation...
if exist venv (
    rmdir /s /q venv
    echo   Removed old virtual environment
)
if exist data\chroma_db (
    rmdir /s /q data\chroma_db
    echo   Cleared old database
)

echo.
echo [3/7] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)
echo   Done!

echo.
echo [4/7] Activating virtual environment...
call venv\Scripts\activate.bat
echo   Activated!

echo.
echo [5/7] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo   Done!

echo.
echo [6/7] Installing dependencies...
echo   This will take 3-5 minutes (downloading ~500MB)
echo.
echo   Installing core packages...
pip install streamlit pandas numpy --quiet
echo   Installing AI models...
pip install sentence-transformers transformers torch --quiet
echo   Installing vector database...
pip install chromadb --quiet
echo   Installing document processors...
pip install pypdf2 python-docx openpyxl --quiet
echo   Installing visualization...
pip install plotly scikit-learn --quiet
echo   Installing utilities...
pip install pydantic python-dateutil regex --quiet

echo.
echo [7/7] Verifying installation...
python -c "import streamlit; import chromadb; import sentence_transformers; print('All packages installed successfully!')"
if errorlevel 1 (
    echo ERROR: Package verification failed
    pause
    exit /b 1
)

echo.
echo ========================================================
echo  INSTALLATION COMPLETE!
echo ========================================================
echo.
echo  System Features:
echo   - 8 Industry configurations
echo   - Advanced AI model (86.9%% accuracy)
echo   - Dynamic weight adjustment
echo   - Cross-encoder re-ranking
echo   - Analytics dashboard
echo   - Export to CSV/JSON
echo.
echo  First-time Setup:
echo   1. Select your industry from dropdown
echo   2. Adjust scoring weights in sidebar
echo   3. Upload CVs (5 samples in data/cvs/)
echo   4. Try searching for candidates
echo.
echo  Starting application...
echo  Browser will open at http://localhost:8501
echo.
echo  Press Ctrl+C to stop the application
echo.
pause

streamlit run app.py
