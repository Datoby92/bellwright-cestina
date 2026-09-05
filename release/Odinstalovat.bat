@echo off
chcp 65001 >nul
title Bellwright - odebrani cestiny
powershell -noProfile -ExecutionPolicy Bypass -File "%~dp0nastroje\instalace.ps1" -Akce Odinstalovat
pause
