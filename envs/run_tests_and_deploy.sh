#!/bin/bash

# Directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Asegurar que el directorio de datos existe
mkdir -p data

echo "==== Ejecutando despliegue con tests ===="

# Detener contenedores anteriores si existen
docker-compose down

# Construir los contenedores
docker-compose build

# Ejecutar la API
docker-compose up -d api

# Esperar a que la API esté disponible
echo "Esperando a que la API esté disponible..."
sleep 10

# Ejecutar los tests
echo "Ejecutando tests..."
docker-compose up tests

# Verificar el resultado de los tests de una manera más robusta
CONTAINER_ID=$(docker-compose ps -q tests)
if [ -n "$CONTAINER_ID" ]; then
    TEST_EXIT_CODE=$(docker inspect -f '{{ .State.ExitCode }}' $CONTAINER_ID)
    # Verificar que TEST_EXIT_CODE es un número
    if [[ "$TEST_EXIT_CODE" =~ ^[0-9]+$ ]]; then
        if [ "$TEST_EXIT_CODE" -eq "0" ]; then
            echo "==== Tests completados con éxito ===="
            echo "La API está desplegada y en funcionamiento."
        else
            echo "==== Los tests han fallado con código $TEST_EXIT_CODE ===="
            echo "Deteniendo la API debido a fallos en los tests."
            docker-compose down
            exit 1
        fi
    else
        echo "==== Error al obtener el código de salida del contenedor de tests ===="
        echo "Código obtenido: '$TEST_EXIT_CODE'"
        echo "Verificando manualmente el estado de los contenedores..."
        docker-compose ps
        echo "Deteniendo los servicios por precaución."
        docker-compose down
        exit 1
    fi
else
    echo "==== No se pudo encontrar el contenedor de tests ===="
    echo "Verificando estado de los contenedores..."
    docker-compose ps
    echo "Deteniendo los servicios por precaución."
    docker-compose down
    exit 1
fi 