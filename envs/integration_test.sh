#!/bin/bash
# Script de pruebas de integración para IA Services
# ---------------------------------------------------

# Definir directorios
root_dir=$(dirname "$PWD")
project_dir=$root_dir
envs_dir="$project_dir/envs"

echo "=========================================="
echo "       PRUEBAS DE INTEGRACIÓN            "
echo "=========================================="

# 1. Asegurarse de que los servicios estén ejecutándose
# -----------------------------------------------------
echo -e "\n[1/5] Verificando servicios..."
services_running=true
containers=$(docker ps --format "{{.Names}}")

if ! echo "$containers" | grep -q "ia_services"; then
    echo "❌ Servicio ia_services no está en ejecución"
    services_running=false
fi

if ! echo "$containers" | grep -q "ia_chatbot"; then
    echo "❌ Servicio ia_chatbot no está en ejecución"
    services_running=false
fi

if [ "$services_running" = false ]; then
    echo "Iniciando servicios..."
    cd $envs_dir
    docker-compose up -d
    sleep 15  # Esperar a que los servicios estén disponibles
else
    # Verificar que los servicios responden
    api_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)
    if [ "$api_response" != "200" ]; then
        echo "⚠️ API responde con código $api_response, posiblemente no esté listo"
    else
        echo "✅ API responde correctamente (código 200)"
    fi
    
    chatbot_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/)
    if [ "$chatbot_response" != "200" ] && [ "$chatbot_response" != "302" ]; then
        echo "⚠️ Chatbot responde con código $chatbot_response, posiblemente no esté listo"
    else
        echo "✅ Chatbot responde correctamente (código $chatbot_response)"
    fi
fi

# 2. Probar la creación de sesión (autenticación)
# ----------------------------------------------
echo -e "\n[2/5] Probando autenticación y creación de sesión..."
credentials=$(echo -n "fabian:secure_password" | base64)
auth_response=$(curl -s -X POST "http://localhost:8000/api/chat/session/auth" \
    -H "Authorization: Basic $credentials")

if echo "$auth_response" | grep -q "id_session"; then
    session_id=$(echo "$auth_response" | grep -o '"id_session":"[^"]*"' | cut -d'"' -f4)
    echo "✅ Autenticación exitosa - ID de sesión: $session_id"
else
    echo "❌ La respuesta de autenticación no contiene id_session"
    echo "Respuesta: $auth_response"
    exit 1
fi

# 3. Probar la inicialización del cuestionario
# -------------------------------------------
echo -e "\n[3/5] Probando inicialización del cuestionario..."

initiate_payload='{
    "id_session": "'$session_id'",
    "type": "questionnarie",
    "content": {
        "questions": [
            {
                "id": "q1",
                "text": "¿Cuál es tu nombre?"
            },
            {
                "id": "q2",
                "text": "¿Cuál es tu experiencia laboral?"
            }
        ]
    },
    "configs": {
        "max_attempts": 3
    }
}'

initiate_response=$(curl -s -X POST "http://localhost:8000/api/chat/questionnarie/initiate" \
    -H "Content-Type: application/json" \
    -d "$initiate_payload")

if echo "$initiate_response" | grep -q "urls"; then
    resource_uri=$(echo "$initiate_response" | grep -o '"resource_uri":"[^"]*"' | cut -d'"' -f4)
    webui=$(echo "$initiate_response" | grep -o '"webui":"[^"]*"' | cut -d'"' -f4)
    
    echo "✅ Inicialización del cuestionario exitosa"
    echo "   URL del recurso: $resource_uri"
    echo "   URL de la interfaz web: $webui"
else
    echo "❌ La respuesta de inicialización no contiene las URLs esperadas"
    echo "Respuesta: $initiate_response"
    exit 1
fi

# 4. Probar el inicio del cuestionario
# ----------------------------------
echo -e "\n[4/5] Probando inicio del cuestionario..."

start_payload='{
    "id_session": "'$session_id'"
}'

start_response=$(curl -s -X POST "http://localhost:8000/api/chat/questionnarie/start" \
    -H "Content-Type: application/json" \
    -d "$start_payload")

if echo "$start_response" | grep -q "websocket_endpoint"; then
    websocket_endpoint=$(echo "$start_response" | grep -o '"websocket_endpoint":"[^"]*"' | cut -d'"' -f4)
    
    echo "✅ Inicio del cuestionario exitoso"
    echo "   Endpoint WebSocket: $websocket_endpoint"
else
    echo "❌ La respuesta de inicio no contiene el endpoint WebSocket esperado"
    echo "Respuesta: $start_response"
    exit 1
fi

# 5. Verificar la persistencia de datos
# -----------------------------------
echo -e "\n[5/5] Verificando persistencia de datos..."

db_check=$(docker exec ia_services python -c "import sqlite3; conn = sqlite3.connect('/app/data/sessions.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM sessions WHERE id_session = ?', ('$session_id',)); print(cursor.fetchone()[0]); conn.close()")

if [ "$db_check" -eq 1 ]; then
    echo "✅ Sesión guardada correctamente en la base de datos"
else
    echo "❌ No se encontró la sesión en la base de datos"
    exit 1
fi

# Resumen de pruebas
# -----------------
echo -e "\n=========================================="
echo "       RESUMEN DE PRUEBAS                "
echo "=========================================="
echo "✅ Pruebas de integración completadas exitosamente"
echo "   - Autenticación"
echo "   - Inicialización del cuestionario"
echo "   - Inicio del cuestionario"
echo "   - Persistencia de datos"
echo -e "\nID de sesión utilizado: $session_id"
echo "==========================================" 