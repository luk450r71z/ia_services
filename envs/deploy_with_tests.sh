#!/bin/bash
# Script de despliegue con pruebas integradas para IA Services
# ---------------------------------------------------

echo "=========================================="
echo "     PROCESO DE PRUEBAS Y DESPLIEGUE      "
echo "=========================================="

# Definir directorios
root_dir=$(dirname "$PWD")
project_dir=$root_dir
api_dir="$project_dir/src/api"
chatbot_dir="$project_dir/src/chatbot"
envs_dir="$project_dir/envs"

# Función para reportar éxito o error
report_status() {
    local step=$1
    local success=$2
    local error_message=${3:-""}
    
    if [ "$success" = true ]; then
        echo "✅ $step completado exitosamente"
    else
        echo "❌ $step falló: $error_message"
        if [ "$CONTINUE_ON_ERROR" != "true" ]; then
            exit 1
        fi
    fi
}

# 1. Ejecutar pruebas del API
# ---------------------------
echo -e "\n[1/6] Ejecutando pruebas del API..."
cd $api_dir
if ! pip install -r requirements.txt; then
    report_status "Instalación de dependencias del API" false "Error al instalar dependencias"
fi

if ! python -m pytest tests/test_api.py -v; then
    report_status "Pruebas del API" false "Las pruebas fallaron"
else
    report_status "Pruebas del API" true
fi

# 2. Ejecutar pruebas del Chatbot
# -------------------------------
echo -e "\n[2/6] Ejecutando pruebas del Chatbot..."
cd $chatbot_dir
if ! npm install; then
    report_status "Instalación de dependencias del Chatbot" false "Error al instalar dependencias"
fi

if ! npm test; then
    report_status "Pruebas del Chatbot" false "Las pruebas fallaron"
else
    report_status "Pruebas del Chatbot" true
fi

# 3. Construir imágenes Docker
# ---------------------------
echo -e "\n[3/6] Construyendo imágenes Docker..."
cd $envs_dir
if ! docker-compose build --no-cache; then
    report_status "Construcción de imágenes Docker" false "Error al construir imágenes"
else
    report_status "Construcción de imágenes Docker" true
fi

# 4. Detener servicios existentes
# ------------------------------
echo -e "\n[4/6] Deteniendo servicios existentes..."
if ! docker-compose down; then
    report_status "Detención de servicios" false "Error al detener servicios"
else
    report_status "Detención de servicios" true
fi

# 5. Iniciar servicios
# -------------------
echo -e "\n[5/6] Iniciando servicios..."
if ! docker-compose up -d; then
    report_status "Inicio de servicios" false "Error al iniciar servicios"
else
    report_status "Inicio de servicios" true
fi

# 6. Verificar estado de servicios
# -------------------------------
echo -e "\n[6/6] Verificando estado de servicios..."
sleep 10  # Dar tiempo a que los servicios se inicien completamente

services_status=$(docker-compose ps)
all_healthy=true
status_message=""

# Verificar si los contenedores están en ejecución
if ! echo "$services_status" | grep -q "ia_services.*Up"; then
    all_healthy=false
    status_message="$status_message El contenedor ia_services no está en ejecución. "
fi

if ! echo "$services_status" | grep -q "ia_chatbot.*Up"; then
    all_healthy=false
    status_message="$status_message El contenedor ia_chatbot no está en ejecución. "
fi

# Verificar API
api_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)
if [ "$api_response" != "200" ]; then
    all_healthy=false
    status_message="$status_message API no responde con estado 200 (respuesta: $api_response). "
fi

# Verificar Chatbot - Aceptar también 302 (redirección) como respuesta válida
chatbot_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/)
if [ "$chatbot_response" != "200" ] && [ "$chatbot_response" != "302" ]; then
    all_healthy=false
    status_message="$status_message Chatbot no responde con estado 200 o 302 (respuesta: $chatbot_response). "
else
    echo "ℹ️ Chatbot responde con estado $chatbot_response (OK - 200=Respuesta directa, 302=Redirección)"
fi

if [ "$all_healthy" = true ]; then
    report_status "Verificación de servicios" true
else
    report_status "Verificación de servicios" false "$status_message"
fi

# Resumen del despliegue
# ---------------------
echo -e "\n=========================================="
echo "       RESUMEN DEL DESPLIEGUE            "
echo "=========================================="
echo "Servicios desplegados en:"
echo "- API: http://localhost:8000"
echo "- Chatbot: http://localhost:5000"
echo -e "\nComandos útiles:"
echo "- Ver logs: docker-compose logs -f"
echo "- Detener servicios: docker-compose down"
echo "- Reiniciar servicios: docker-compose restart"
echo "==========================================" 