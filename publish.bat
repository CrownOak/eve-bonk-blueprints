@echo off
REM Publish the generated page to git. FAIL-CLOSED: refuses to push an unlocked page,
REM and exits non-zero on refusal so a missing password surfaces as a failure.
cd /d "%~dp0"
findstr /C:"const B =" index.html >nul
if errorlevel 1 (
  echo publish: index.html is NOT locked -- refusing to push. Is EVE_PAGE_PASSWORD set?
  exit /b 1
)
git add index.html
git diff --cached --quiet
if %ERRORLEVEL%==0 (
  echo publish: no page change
) else (
  git commit -m "blueprint: update top builds"
  git push
)
