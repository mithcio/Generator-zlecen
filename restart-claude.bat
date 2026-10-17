@echo off
rem Restartuje Claude Desktop. Opcjonalnie: restart-claude.bat 60  (czeka 60 s przed restartem)
set DELAY=%1
if "%DELAY%"=="" set DELAY=0
start "" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0restart-claude.ps1" -DelaySeconds %DELAY%
