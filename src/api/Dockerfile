FROM python:3.9-slim

WORKDIR /app

# Instalar curl para healthcheck
RUN apt-get update && apt-get install -y curl && apt-get clean

# Copiar requisitos e instalarlos primero para aprovechar la caché de Docker
COPY src/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente de la aplicación
COPY src /app/src

# Crear directorio para la base de datos
RUN mkdir -p /app/envs/data

# Exponer el puerto en el que se ejecuta la aplicación
EXPOSE 8000

# Establecer PYTHONPATH
ENV PYTHONPATH=/app

# Comando para ejecutar la aplicación
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"] 