@echo off
cd "%~dp0.."
.venv\Scripts\python -m pytest -q %*
