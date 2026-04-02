@echo off
echo Iniciando Lead Gen Pro Elite en WSL...
wsl -d Ubuntu -e bash -c "cd '/home/guerk/Scrapper Clientes' && source venv/bin/activate && streamlit run app.py"
pause
