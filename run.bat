@echo off
echo Criando/ativando ambiente virtual...
if not exist venv (
    python -m venv venv
    echo Ambiente virtual criado!
)
call venv\Scripts\activate
pip install -r requirements.txt
echo.
echo Iniciando servidor Flask em http://127.0.0.1:5000
echo Pressione Ctrl+C para parar.
flask run --host=0.0.0.0
pause

