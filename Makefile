.PHONY: run setup stop clean

run:
	@bash lanzador.sh

setup:
	@echo "Configurando entorno..."
	@python3 -m venv venv
	@venv/bin/python -m pip install -r requirements.txt
	@venv/bin/python -m playwright install chromium
	@touch venv/installed.txt
	@if [ ! -f .env ]; then cp .env.example .env; fi

stop:
	@echo "Deteniendo servicios Docker..."
	@docker compose down
	@echo "Matando procesos Python..."
	@pkill -f webhook.py || true
	@pkill -f streamlit || true

clean:
	@echo "Limpiando entorno virtual y temporales..."
	@rm -rf venv
	@find . -type d -name "__pycache__" -exec rm -rf {} +
