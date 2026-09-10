@echo off
chcp 65001 >nul
title Zoom Bot - Сборка EXE
color 0A

echo ============================================
echo    СБОРКА ZOOM BOT В EXE
echo ============================================
echo.

py --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python не найден.
    pause
    exit /b
)

echo [+] Установка PyInstaller...
py -m pip install pyinstaller --quiet

if not exist "zoom_bot_app.py" (
    echo [!] zoom_bot_app.py не найден в этой папке.
    pause
    exit /b
)

echo [+] Сборка exe...
py -m PyInstaller --onefile --windowed --name "ZoomBot" --clean zoom_bot_app.py

if errorlevel 1 (
    echo [!] Ошибка сборки.
    pause
    exit /b
)

echo.
echo [+] Готово. Файл: dist\ZoomBot.exe
echo [+] Скопируйте его куда нужно. Рядом положите names.txt и WAV.
echo.
pause