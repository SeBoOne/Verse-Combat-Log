@echo off
REM ========================================
REM Verse Combat Log - Build & Hash Script
REM ========================================

echo.
echo ========================================
echo  Verse Combat Log v1.1 - Build Script
echo ========================================
echo.

REM 1. Build mit PyInstaller
echo [1/3] Building EXE with PyInstaller...
echo.
pyinstaller build_exe.spec

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Build completed!
echo.

REM 2. SHA256 Hash erstellen
echo [2/3] Generating SHA256 hash...
echo.

if exist "dist\VerseCombatLog.exe" (
    certutil -hashfile "dist\VerseCombatLog.exe" SHA256 > "dist\VerseCombatLog_SHA256.txt"

    echo SHA256 Hash saved to: dist\VerseCombatLog_SHA256.txt
    echo.
    echo Hash:
    type "dist\VerseCombatLog_SHA256.txt"
    echo.
) else (
    echo [WARNING] VerseCombatLog.exe not found in dist folder!
)

REM 3. README kopieren
echo [3/3] Copying README to dist folder...
echo.

if exist "RELEASE_README.md" (
    copy "RELEASE_README.md" "dist\README.md" >nul
    echo README copied to dist folder
) else (
    echo [WARNING] RELEASE_README.md not found!
)

echo.
echo ========================================
echo  Build Process Complete!
echo ========================================
echo.
echo Output location: dist\VerseCombatLog.exe
echo.
echo Next steps:
echo  1. Test the EXE: dist\VerseCombatLog.exe --debug
echo  2. Upload to VirusTotal.com for scanning
echo  3. Report False-Positives to AV vendors
echo  4. Create GitHub Release with SHA256 hash
echo.

pause
