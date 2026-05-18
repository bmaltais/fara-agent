@echo off
REM Start llama-server with settings from config.json
REM Edit config.json to change model_path, port, or GPU layers (ngl)

for /f "tokens=*" %%i in ('uv run python -c "import json; c=json.load(open('config.json')); a=c.get('llama_cpp_args',{}); print(c['llama_cpp_path'], '-m', c['model_path'], '-ngl', a.get('ngl',99), '-c', a.get('ctx_size',8192), '--host', a.get('host','0.0.0.0'), '--port', a.get('port',8080))"') do set CMD=%%i

echo Starting: %CMD%
%CMD%
