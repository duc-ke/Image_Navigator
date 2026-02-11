@echo off
REM Image Navigator - Windows .exe 빌드 스크립트
REM
REM 사용법:
REM   cd sam3\Image_Navigator
REM   build.bat
REM
REM 결과:
REM   dist\ImageNavigator\ImageNavigator.exe

cd /d "%~dp0"

echo === Image Navigator Build ===
echo.

REM 의존성 확인
python -c "import PySide6" 2>nul
if errorlevel 1 (
    echo [*] PySide6 not found. Installing dependencies...
    pip install -r requirements.txt
)

python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [*] PyInstaller not found. Installing...
    pip install pyinstaller
)

echo [*] Building ImageNavigator...

pyinstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --onedir ^
    --name "ImageNavigator" ^
    --add-data "canvas.py;." ^
    main.py

echo.
echo === Build Complete ===
echo Exe location: %~dp0dist\ImageNavigator\ImageNavigator.exe
echo.
echo To run:
echo   dist\ImageNavigator\ImageNavigator.exe
