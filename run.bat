@echo off
REM BONK Blueprint Scanner - MONTHLY recorder (Windows Task Scheduler entry point).
REM Rebuilds the SDE index when stale, re-prices from Jita, writes index.html, publishes.
REM Exit code reflects failure so Task Scheduler "Last Result" is truthful.
cd /d "%~dp0"
".venv\Scripts\python.exe" bonk_blueprint_scanner.py --me 10 >> blueprint.log 2>&1
if errorlevel 1 ( echo SCANNER FAILED, skipping publish >> blueprint.log & exit /b 1 )
call "%~dp0publish.bat" >> blueprint.log 2>&1
exit /b %errorlevel%
