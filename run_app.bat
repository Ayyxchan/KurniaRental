@echo off
REM Jalankan aplikasi Flask KurniaRental dari root workspace yang memiliki subfolder KurniaRental\KurniaRental
cd /d "%~dp0KurniaRental"
if not exist app.py (
  echo ERROR: app.py tidak ditemukan di %cd%
  pause
  exit /b 1
)
python app.py
pause
