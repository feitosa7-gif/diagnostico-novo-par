@echo off
title Diagnostico do Novo PAR - SEEDF
echo Iniciando servidor da aplicacao...
python -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
