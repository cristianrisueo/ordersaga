# Imagen del servicio stock: la misma imagen arranca la API, el productor del outbox o el consumidor, solo cambia el comando.
FROM python:3.14.8-slim

# Copia uv de su imagen oficial, en la versión fijada
COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /uvx /bin/

# Compila a bytecode al instalar (arranca más rápido) y copia los paquetes en vez de enlazarlos
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Instala solo las dependencias: esta capa se reutiliza mientras pyproject.toml y uv.lock no cambien
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# Copia el código (proyecto virtual: app se importa porque el proceso arranca en /app)
COPY . .

# Ejecuta como un usuario sin privilegios, nunca como root
RUN useradd --create-home app
USER app

# Pone el entorno virtual delante en el PATH: uvicorn y python se ejecutan sin «uv run»
ENV PATH="/app/.venv/bin:$PATH"

# Arranca la API escuchando en todas las interfaces del contenedor
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
