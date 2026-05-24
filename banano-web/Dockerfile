FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código
COPY backend/ ./backend/
COPY static/ ./static/

# Exponer puerto
EXPOSE 8080

# Comando para iniciar
CMD ["python", "backend/main.py"]
