@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONDONTWRITEBYTECODE=1"
for %%V in (3.14 3.13 3.12) do (
  py -%%V -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    py -%%V -B lancer.py %*
    goto resultat
  )
)
python -c "import sys; assert (3,12) <= sys.version_info[:2] < (3,15)" >nul 2>nul
if errorlevel 1 (
  echo Installe Python 3.12, 3.13 ou 3.14 depuis https://www.python.org/downloads/
  echo Coche Add python.exe to PATH pendant l'installation, puis relance ce fichier.
  if /i not "%~1"=="--verifier" pause
  exit /b 1
)
python -B lancer.py %*
:resultat
if errorlevel 1 (
  if /i not "%~1"=="--verifier" pause
  exit /b 1
)
