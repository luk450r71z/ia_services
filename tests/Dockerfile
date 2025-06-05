FROM python:3.9-slim

WORKDIR /app

# Copiar los requisitos de la API e instalarlos primero
COPY src/api/requirements.txt /app/api_requirements.txt
RUN pip install --no-cache-dir -r api_requirements.txt

# Copiar requisitos de tests e instalarlos después
COPY tests/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar los archivos de prueba
COPY tests /app/tests

# Copiar el código fuente de la aplicación
COPY src /app/src
COPY envs /app/envs

# Comando para ejecutar las pruebas
CMD ["python", "tests/run_tests.py"] 