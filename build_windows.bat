@echo off
REM ============================================================
REM  Build MEP Drawing Reader thanh file .exe (chay tren WINDOWS)
REM  Yeu cau cai san: Python 3.12 (64-bit) va Node.js
REM  Cach dung: double-click file nay, hoac chay trong CMD.
REM ============================================================
setlocal
cd /d "%~dp0"

REM --- Kiem tra dang chay dung trong thu muc du an ---
if not exist "backend\requirements.txt" goto :nofolder
if not exist "frontend\package.json" goto :nofolder

echo [1/4] Cai dependencies Python...
python -m venv .venv_build 2>nul
call .venv_build\Scripts\activate
pip install --upgrade pip >nul
pip install -r backend\requirements.txt pyinstaller || goto :err

echo [2/4] Build giao dien (frontend)...
cd frontend
call npm install || goto :err
call npm run build || goto :err
cd ..

echo [3/4] Dong goi thanh .exe (PyInstaller)...
cd backend
pyinstaller --noconfirm mep_reader.spec || goto :err
cd ..

echo [4/4] Xong!
echo File .exe nam o: backend\dist\MEP-Drawing-Reader.exe
echo Gui file do cho nguoi khac, ho double-click la chay duoc.
pause
exit /b 0

:nofolder
echo.
echo *** LOI: Khong tim thay thu muc "backend" va "frontend" canh file nay. ***
echo.
echo Ban dang chay build_windows.bat MOT MINH (vi du double-click tu ben trong
echo file ZIP). Script can CA THU MUC DU AN moi build duoc.
echo.
echo Cach sua:
echo   1. GIAI NEN (Extract All) toan bo file ZIP ra 1 thu muc that.
echo   2. Mo thu muc do, kiem tra co thay folder "backend" va "frontend"
echo      nam CANH file build_windows.bat.
echo   3. Luc do moi double-click build_windows.bat.
echo.
echo Thu muc hien tai: %CD%
pause
exit /b 1

:err
echo.
echo *** Build that bai. Kiem tra loi ben tren. ***
pause
exit /b 1
