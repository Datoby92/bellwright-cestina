@echo off
chcp 65001 >nul
title Bellwright - instalace cestiny
powershell -noProfile -ExecutionPolicy Bypass -File "%~dp0nastroje\instalace.ps1" -Akce Instalovat
pause
