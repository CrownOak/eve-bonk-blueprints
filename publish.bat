@echo off
REM Publish the blueprint page into the wdeve site (wdeve/blueprints/). FAIL-CLOSED.
cd /d "%~dp0"
findstr /C:"const B =" index.html >nul
if errorlevel 1 (
  echo publish: index.html is NOT locked -- refusing to push. Is EVE_PAGE_PASSWORD set?
  exit /b 1
)
set "DEST=C:\Users\sales\wdeve\blueprints"
if not exist "%DEST%" mkdir "%DEST%"
copy /Y index.html "%DEST%\index.html" >nul
pushd "C:\Users\sales\wdeve"
git add blueprints/index.html
git diff --cached --quiet
if %ERRORLEVEL%==0 ( echo publish: no page change ) else ( git commit -m "blueprints: update page" & git push )
popd
