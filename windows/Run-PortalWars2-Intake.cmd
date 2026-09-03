@echo off
setlocal EnableExtensions

rem PortalWars2 Prefix Intake v1.0.0
rem Scans the user's complete %LOCALAPPDATA% tree for PortalWars2.
rem Output is created beside this launcher.

set "REPO_ROOT=%~dp0.."
set "LAUNCHER_DIR=%~dp0"
set "PYTHONPATH=%REPO_ROOT%\src"
set "PWI_LAUNCHER_DIR=%LAUNCHER_DIR%"

set "PY_CMD="
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 set "PY_CMD=py -3"
if not defined PY_CMD (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 set "PY_CMD=python"
)

if not defined PY_CMD (
    echo.
    echo ERROR: Python 3.10 or newer was not found in PATH.
    echo Install Python and make ^"py^" or ^"python^" available.
    echo.
    pause
    exit /b 1
)

if not defined LOCALAPPDATA (
    echo.
    echo ERROR: %%LOCALAPPDATA%% is not set.
    echo This launcher is intended for Windows and uses the current user's LocalAppData directory.
    echo.
    pause
    exit /b 1
)

%PY_CMD% -c "import os,sys; from pathlib import Path; sys.path.insert(0, os.environ['PYTHONPATH']); from portalwars2_prefix_intake.core import main; raise SystemExit(main(['--localappdata'], script_dir=Path(os.environ['PWI_LAUNCHER_DIR'])))"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Intake failed with exit code %EXIT_CODE%.
    echo.
    pause
    exit /b %EXIT_CODE%
)

echo.
echo Intake complete. Output was written beside this launcher.
echo.
pause
exit /b 0
