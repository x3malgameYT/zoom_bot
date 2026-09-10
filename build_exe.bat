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

echo [+] Установка зависимостей...
py -m pip install --upgrade pip --quiet
py -m pip install selenium pyinstaller --quiet

if not exist "zoom_bot_app.py" (
    echo [!] zoom_bot_app.py не найден.
    pause
    exit /b
)

echo [+] Сборка exe...
py -m PyInstaller --onefile --windowed --name "ZoomBot" ^
  --hidden-import=selenium ^
  --hidden-import=selenium.webdriver ^
  --hidden-import=selenium.webdriver.chrome ^
  --hidden-import=selenium.webdriver.chrome.webdriver ^
  --hidden-import=selenium.webdriver.chrome.options ^
  --hidden-import=selenium.webdriver.chrome.service ^
  --hidden-import=selenium.webdriver.common.by ^
  --hidden-import=selenium.webdriver.common.keys ^
  --hidden-import=selenium.webdriver.support.ui ^
  --hidden-import=selenium.webdriver.support.expected_conditions ^
  --hidden-import=selenium.webdriver.support.wait ^
  --hidden-import=selenium.webdriver.remote.webdriver ^
  --collect-all=selenium ^
  --collect-all=urllib3 ^
  --collect-all=certifi ^
  --clean zoom_bot_app.py

if errorlevel 1 (
    echo [!] Ошибка сборки.
    pause
    exit /b
)

echo.
echo [+] Готово: dist\ZoomBot.exe
pause