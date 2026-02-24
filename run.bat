@echo off
REM Django FinSight Server Startup Script
REM This batch file starts the Django development server

cd /d C:\Users\Thanuja.m\Documents\Downloads\finsight-main\finsight-main

REM Run Django development server using the virtual environment's Python directly
C:\Users\Thanuja.m\Documents\Downloads\finsight-main\.venv\Scripts\python.exe manage.py runserver

REM Keep window open if there's an error
pause
