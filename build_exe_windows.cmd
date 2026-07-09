@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\python_bootstrap.ps1" -Mode build -AllowSystemInstall -AllowDependencyInstall -AllowDesktopBuild %*
exit /b %ERRORLEVEL%
