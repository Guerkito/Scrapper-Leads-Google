.PHONY: run setup stop clean web streamlit deploy deploy-down

run:
	@bash lanzador.sh

web:
	@venv/bin/python -m uvicorn web.app:app --host 127.0.0.1 --port 8502 --reload

streamlit:
	@venv/bin/streamlit run app.py --server.port=8501 --server.headless=true --browser.gatherUsageStats=false --theme.base=dark

deploy:
	@docker compose -f docker-compose.app.yml up -d --build

deploy-down:
	@docker compose -f docker-compose.app.yml down

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
	@pkill -f email_agent.py || true
	@pkill -f "uvicorn web.app" || true
	@pkill -f streamlit || true

clean:
	@echo "Limpiando entorno virtual y temporales..."
	@rm -rf venv
	@find . -type d -name "__pycache__" -exec rm -rf {} +
