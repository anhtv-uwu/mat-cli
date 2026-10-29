@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0mat-cli.ps1" %*
exit /b %errorlevel%
