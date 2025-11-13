@echo off
echo ================================================
echo Verse Combat Log v3.1 - Installation
echo ================================================
echo.

REM Prüfe Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python wurde nicht gefunden!
    echo Bitte installiere Python 3.7 oder höher von https://www.python.org
    pause
    exit /b 1
)

echo [OK] Python gefunden
echo.

REM Installiere Dependencies
echo Installiere Dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [FEHLER] Installation fehlgeschlagen!
    pause
    exit /b 1
)

echo.
echo ================================================
echo Installation erfolgreich!
echo ================================================
echo.
echo WICHTIG: Stelle sicher dass du die internalNames.ini Datei hast!
echo.
echo Starte das Tool mit: python app.py
echo Oder nutze: start.bat
echo.
pause