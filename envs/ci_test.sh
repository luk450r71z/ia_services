#!/bin/bash
# Script de pruebas para entorno de CI/CD
# ---------------------------------------------------

# Definir directorios
root_dir=$(dirname "$PWD")
project_dir=$root_dir
api_dir="$project_dir/src/api"
chatbot_dir="$project_dir/src/chatbot"
envs_dir="$project_dir/envs"

tests_passed=true

echo "=========================================="
echo "     PRUEBAS DE INTEGRACIÓN CI/CD         "
echo "=========================================="

# 1. Verificar y preparar entorno
# -------------------------------
echo -e "\n[1/4] Verificando entorno..."
# Comprobar Python
python_version=$(python --version 2>&1)
if [ $? -eq 0 ]; then
    echo "Python: $python_version"
else
    echo "❌ Python no está instalado o no está en el PATH"
    exit 1
fi

# Comprobar Node.js
node_version=$(node --version 2>&1)
if [ $? -eq 0 ]; then
    echo "Node.js: $node_version"
else
    echo "❌ Node.js no está instalado o no está en el PATH"
    exit 1
fi

# Comprobar Docker
docker_version=$(docker --version 2>&1)
if [ $? -eq 0 ]; then
    echo "Docker: $docker_version"
else
    echo "❌ Docker no está instalado o no está en el PATH"
    exit 1
fi

# Comprobar Docker Compose
compose_version=$(docker-compose --version 2>&1)
if [ $? -eq 0 ]; then
    echo "Docker Compose: $compose_version"
else
    echo "❌ Docker Compose no está instalado o no está en el PATH"
    exit 1
fi

# 2. Ejecutar pruebas del API
# ---------------------------
echo -e "\n[2/4] Ejecutando pruebas del API..."
cd $api_dir

# Crear entorno virtual para las pruebas
python -m venv .venv
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
elif [ -f .venv/Scripts/activate ]; then
    source .venv/Scripts/activate
else
    echo "❌ No se pudo crear o activar el entorno virtual"
    tests_passed=false
fi

if [ "$tests_passed" = true ]; then
    # Instalar dependencias
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Error al instalar dependencias de Python"
        tests_passed=false
    fi
fi

if [ "$tests_passed" = true ]; then
    # Ejecutar pruebas
    python -m pytest tests/test_api.py -v
    if [ $? -ne 0 ]; then
        echo "❌ Pruebas del API fallaron"
        tests_passed=false
    else
        echo "✅ Pruebas del API completadas exitosamente"
    fi
    
    # Desactivar entorno virtual
    deactivate
fi

# 3. Ejecutar pruebas del Chatbot
# -------------------------------
echo -e "\n[3/4] Ejecutando pruebas del Chatbot..."
cd $chatbot_dir

# Instalar dependencias
npm ci
if [ $? -ne 0 ]; then
    echo "❌ Error al instalar dependencias de Node.js"
    tests_passed=false
else
    # Ejecutar pruebas
    npm test
    if [ $? -ne 0 ]; then
        echo "❌ Pruebas del Chatbot fallaron"
        tests_passed=false
    else
        echo "✅ Pruebas del Chatbot completadas exitosamente"
    fi
fi

# 4. Pruebas de integración con Docker
# -----------------------------------
echo -e "\n[4/4] Ejecutando pruebas de integración con Docker..."
cd $envs_dir

# Construir imágenes
docker-compose build
if [ $? -ne 0 ]; then
    echo "❌ Error al construir imágenes Docker"
    tests_passed=false
else
    # Iniciar servicios en modo de prueba
    docker-compose up -d
    if [ $? -ne 0 ]; then
        echo "❌ Error al iniciar servicios Docker"
        tests_passed=false
    else
        # Esperar a que los servicios estén disponibles
        echo "Esperando a que los servicios estén disponibles..."
        sleep 15
        
        # Probar API
        api_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)
        if [ "$api_status" = "200" ]; then
            echo "✅ API respondiendo correctamente (Status: $api_status)"
        else
            echo "❌ No se pudo conectar con el API (Status: $api_status)"
            tests_passed=false
        fi
        
        # Probar Chatbot - Aceptar código 302 como respuesta válida
        chatbot_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/)
        if [ "$chatbot_status" = "200" ] || [ "$chatbot_status" = "302" ]; then
            echo "✅ Chatbot respondiendo correctamente (Status: $chatbot_status)"
        else
            echo "❌ No se pudo conectar con el Chatbot (Status: $chatbot_status)"
            tests_passed=false
        fi
        
        # Detener contenedores
        docker-compose down
    fi
fi

# Resultados finales
# -----------------
echo -e "\n=========================================="
echo "           RESULTADOS DE PRUEBAS          "
echo "=========================================="

if [ "$tests_passed" = true ]; then
    echo -e "\n✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE"
    exit 0
else
    echo -e "\n❌ ALGUNAS PRUEBAS FALLARON - Revisar los logs para más detalles"
    exit 1
fi 