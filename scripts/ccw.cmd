@echo off
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src;%PYTHONPATH%
if exist "%ROOT%\.venv-http\Scripts\python.exe" (
  "%ROOT%\.venv-http\Scripts\python.exe" -m ccw %*
) else (
  python -m ccw %*
)
exit /b %ERRORLEVEL%
