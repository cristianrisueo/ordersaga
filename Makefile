# Comandos del proyecto OrderSaga. Help los lista con su descripción.
.PHONY: help up down logs check

help:  ## Muestra los comandos disponibles
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-8s %s\n", $$1, $$2}'

up:  ## Construye las imágenes y levanta los contenedores, espera a que health responda
	docker compose up -d --build --wait

down:  ## Elimina contenedores y datos: cada arranque empieza limpio
	docker compose down -v

logs:  ## Sigue los logs de los contenedores
	docker compose logs -f

check:  ## Formatea, pasa el linter y comprueba tipos en cada servicio; para en el primer fallo
	@for svc in $(wildcard services/*); do echo "==> $$svc"; (cd $$svc && uv run ruff format . && uv run ruff check . && uv run mypy app) || exit 1; done
