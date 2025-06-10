# IA Services 🤖

**Plataforma de servicios de inteligencia artificial con agente conversacional**

## 📋 Descripción

IA Services es una plataforma completa que combina un backend robusto en FastAPI con un frontend interactivo en Vue.js para proporcionar servicios de inteligencia artificial, especialmente enfocado en chatbots conversacionales para entrevistas y otras aplicaciones.

## 🏗️ Arquitectura del Proyecto

```
ia_services/
├── src/
│   ├── api/                      # Backend FastAPI
│   │   ├── main.py              # Punto de entrada principal de la API
│   │   ├── requirements.txt     # Dependencias de Python
│   │   ├── auth/                # Sistema de autenticación
│   │   │   ├── router.py        # Endpoints de autenticación
│   │   │   ├── config.py        # Configuración de autenticación
│   │   │   ├── models/          # Modelos de datos
│   │   │   └── db/              # Base de datos SQLite
│   │   └── conversational_agent/ # Agente conversacional
│   │       ├── router.py        # WebSocket y endpoints del chat
│   │       ├── websocket_manager.py # Gestor de conexiones WebSocket
│   │       ├── agents/          # Agentes de IA
│   │       ├── models/          # Esquemas de datos del chat
│   │       └── utils/           # Utilidades
│   └── chatbot/                 # Frontend Vue.js
│       ├── package.json         # Dependencias de Node.js
│       ├── vite.config.js       # Configuración de Vite
│       ├── index.html           # Página principal del frontend
│       ├── src/
│       │   ├── main.js          # Punto de entrada de Vue
│       │   └── App.vue          # Componente principal
│       ├── components/          # Componentes reutilizables
│       └── pages/               # Páginas de la aplicación
└── envs/
    └── data/                    # Base de datos SQLite
```

## ✨ Características Principales

### 🔐 Sistema de Autenticación
- **Autenticación HTTP Basic**: Autenticación básica con usuario y contraseña
- **Gestión de sesiones**: Control de sesiones activas por usuario en SQLite
- **Servicios configurables**: Soporte para diferentes tipos de agentes conversacionales
- **Estados de sesión**: Control de estados (new, initiated, started, complete, expired)

### 💬 Agente Conversacional
- **WebSocket en tiempo real**: Comunicación bidireccional instantánea
- **Gestión de sesiones**: Manejo automático de múltiples conversaciones
- **Arquitectura escalable**: Diseñado para múltiples usuarios simultáneos
- **Logging integrado**: Seguimiento completo de conversaciones

### 🎨 Frontend Interactivo
- **Vue.js 3**: Framework moderno y reactivo
- **Interfaz de chat**: Widget de chat responsive y moderno
- **Conexión automática**: Reconexión automática en caso de pérdida de conexión
- **Experiencia de usuario fluida**: Interfaz intuitiva y fácil de usar

## 🚀 Instalación y Configuración

### Requisitos Previos
- Python 3.8+
- Node.js 18+ 
- npm o yarn
- Git

### 1. Clonar el Repositorio
```bash
git clone <url-del-repositorio>
cd ia_services
```

### 2. Configurar el Backend

#### Instalar Dependencias de Python
```bash
cd src/api
pip install -r requirements.txt
```

#### Ejecutar el Servidor API
```bash
cd src/api
python main.py
```

El servidor estará disponible en: `http://localhost:8000`

### 3. Configurar el Frontend

#### Instalar Dependencias de Node.js
```bash
cd src/chatbot
npm install
# o si prefieres yarn
yarn install
```

#### Ejecutar el Servidor de Desarrollo
```bash
cd src/chatbot
npm run dev
# o si prefieres yarn
yarn dev
```

El frontend estará disponible en: `http://localhost:3000`

#### Construir para Producción
```bash
cd src/chatbot
npm run build
# o si prefieres yarn
yarn build
```

## 📚 API Documentation

### Endpoints Principales

#### Autenticación
- `POST /api/chat/session/auth` - Crear nueva sesión con autenticación básica
- `GET /api/chat/session/{session_id}` - Obtener información de una sesión existente
- `POST /api/chat/service/initiate` - Inicializar servicio en sesión existente

#### Chat Conversacional
- `WebSocket /api/chat/ws/{session_id}` - Conexión WebSocket para chat
- `POST /api/chat/session/start` - Iniciar sesión de chat
- `GET /api/chat/session/{session_id}/status` - Obtener estado de sesión

### Documentación Interactiva
Una vez ejecutando el servidor, visita:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔧 Configuración

### Variables de Entorno (Backend)
Crea un archivo `.env` en el directorio `src/api/` con:
```env
GROQ_API_KEY=tu_clave_de_groq_api
```

### Configuración del Frontend
El frontend se conecta automáticamente al backend en `localhost:8000`. Para cambiar la URL, modifica las configuraciones en los componentes Vue.

## 🧪 Uso Básico

### 1. Autenticación
```javascript
// Crear sesión con autenticación básica
const response = await fetch('/api/chat/session/auth', {
    method: 'POST',
    headers: { 
        'Authorization': 'Basic ' + btoa('usuario:contraseña')
    }
});
```

### 2. Iniciar Chat
```javascript
// Conectar WebSocket
const ws = new WebSocket('ws://localhost:8000/api/chat/ws/session-id');

// Enviar mensaje
ws.send(JSON.stringify({
    content: 'Hola, ¿cómo estás?'
}));
```

### 3. Interfaz Web
1. Ejecuta `python src/api/main.py` para el backend
2. Ejecuta `npm run dev` en `src/chatbot/` para el frontend
3. Abre `http://localhost:5173` en tu navegador (puerto por defecto de Vite)
4. Usa el widget de chat para interactuar con el agente

## 🛠️ Tecnologías Utilizadas

### Backend
- **FastAPI**: Framework web moderno y rápido
- **WebSockets**: Comunicación en tiempo real
- **SQLite**: Base de datos ligera para sesiones
- **Uvicorn**: Servidor ASGI de alto rendimiento
- **LangChain**: Framework para aplicaciones de IA
- **Groq**: API de modelos de lenguaje

### Frontend
- **Vue.js 3**: Framework progresivo de JavaScript
- **Vite**: Build tool rápido y moderno
- **HTML5/CSS3**: Estructura y estilos modernos
- **WebSocket API**: Conexión en tiempo real con el backend

## 🚀 Despliegue

### Desarrollo Local
```bash
# Terminal 1: Backend
cd src/api
python main.py

# Terminal 2: Frontend
cd src/chatbot
npm run dev
```

### Producción
```bash
# Construir el frontend
npm run build

# Servir archivos estáticos con el backend o servidor web
```

Para producción, considera:
- Usar un servidor web como Nginx
- Configurar HTTPS
- Usar una base de datos externa
- Implementar Redis para sesiones
- Configurar logging apropiado

## 📋 Scripts Disponibles

### Frontend
- `npm run dev` - Servidor de desarrollo con hot reload
- `npm run build` - Construir para producción
- `npm run preview` - Vista previa de la build de producción

### Backend
- `python src/api/main.py` - Ejecutar servidor de desarrollo
- `uvicorn src.api.main:app --reload` - Alternativa con uvicorn

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 📞 Soporte

Para soporte y preguntas:
- Crea un issue en GitHub
- Contacta al equipo de desarrollo

---

**Desarrollado con ❤️ usando FastAPI, Vue.js y Vite**

# IA Services Microservices Deployment

Este proyecto implementa una solución basada en microservicios para el sistema IA Services, consistiendo en:

1. **IA Services API** (`ia_services`): Backend que proporciona endpoints para autenticación y gestión de cuestionarios.
2. **IA Chatbot** (`ia_chatbot`): Frontend basado en Vue.js que consume los servicios del API.

## Estructura del Proyecto

```
.
├── envs/                  # Configuración y scripts para despliegue
│   ├── data/              # Volumen para persistencia (contiene sessions.db)
│   ├── docker-compose.yml # Orquestación de contenedores
│   ├── start.sh           # Script para iniciar servicios
│   ├── stop.sh            # Script para detener servicios
│   ├── logs.sh            # Script para ver logs
│   ├── status.sh          # Script para verificar estado
│   ├── health_check.sh    # Script para verificación de salud
│   ├── run_tests.sh       # Script para ejecutar todas las pruebas
│   ├── deploy_with_tests.sh  # Script para despliegue con pruebas integradas
│   ├── ci_test.sh         # Script para pruebas en entornos CI/CD
│   └── integration_test.sh   # Script para pruebas de integración
├── src/
│   ├── api/               # Servicio de API (FastAPI)
│   │   ├── main.py        # Punto de entrada
│   │   ├── Dockerfile     # Configuración para contenedor
│   │   ├── requirements.txt # Dependencias
│   │   └── tests/         # Pruebas del API
│   └── chatbot/           # Servicio de Chatbot (Vue.js)
│       ├── Dockerfile     # Configuración para contenedor
│       ├── package.json   # Dependencias
│       └── tests/         # Pruebas del Chatbot
```

## Requisitos

- Docker y Docker Compose
- Git
- Python 3.9+
- Node.js 16+
- Bash (para scripts de prueba y despliegue)

## Endpoints del API

- `POST /api/chat/session/auth` - Crear sesión
- `POST /api/chat/questionnarie/initiate` - Iniciar cuestionario
- `POST /api/chat/questionnarie/start` - Comenzar cuestionario

## Despliegue con Pruebas Integradas

### Método recomendado: Despliegue automatizado con pruebas

Ejecuta el script de despliegue con pruebas integradas:

```bash
cd envs
bash deploy_with_tests.sh
```

Este script realiza las siguientes acciones:
1. Ejecuta las pruebas unitarias del API
2. Ejecuta las pruebas unitarias del Chatbot
3. Construye las imágenes Docker
4. Detiene los servicios existentes
5. Inicia los nuevos servicios
6. Verifica que los servicios estén funcionando correctamente

### Pruebas de integración

Para ejecutar solo las pruebas de integración en un entorno ya desplegado:

```bash
cd envs
bash integration_test.sh
```

Este script prueba:
1. La autenticación y creación de sesión
2. La inicialización del cuestionario
3. El inicio del cuestionario
4. La persistencia de datos en la base de datos

### Pruebas para entornos de CI/CD

Para ejecutar pruebas en un entorno de integración continua:

```bash
cd envs
bash ci_test.sh
```

## Métodos de Despliegue Manual

### Iniciar los servicios

```bash
cd envs
docker-compose up -d
```

### Verificar estado

```bash
cd envs
docker-compose ps
```

### Ver logs

```bash
cd envs
docker-compose logs          # Ver logs de todos los servicios
docker-compose logs ia_services  # Ver logs del servicio API
docker-compose logs ia_chatbot   # Ver logs del servicio Chatbot
```

### Verificar salud de los servicios

```bash
cd envs
docker-compose exec ia_services curl http://localhost:8000/
docker-compose exec ia_chatbot wget -qO- http://localhost:80/
```

### Detener los servicios

```bash
cd envs
docker-compose down
```

## Pruebas Manuales

### Pruebas del API

```bash
cd src/api
python -m pytest tests/test_api.py -v
```

### Pruebas del Chatbot

```bash
cd src/chatbot
npm install
npm test
```

## Volumen de Datos

Los datos persistentes, incluyendo `sessions.db`, se almacenan en el volumen `envs/data` que se monta en los contenedores.

## Arquitectura

```
┌────────────────┐     ┌────────────────┐
│                │     │                │
│   ia_chatbot   │────▶│   ia_services  │
│   (Frontend)   │     │   (Backend)    │
│                │     │                │
└────────────────┘     └────────┬───────┘
                                │
                                ▼
                        ┌────────────────┐
                        │                │
                        │  sessions.db   │
                        │   (Volumen)    │
                        │                │
                        └────────────────┘
```

## Solución de Problemas

### Error en la prueba del Chatbot con vitest

Si encuentras el error "vitest no se reconoce como un comando", ejecuta:

```bash
cd src/chatbot
npm install
```

### Contenedor en estado unhealthy

Si un contenedor aparece como "unhealthy", verifica los logs:

```bash
docker logs ia_services
```

Y asegúrate de que las comprobaciones de salud están configuradas correctamente en `docker-compose.yml`.

### Problemas con los scripts de Bash en Windows

Si estás en Windows y tienes problemas para ejecutar los scripts de Bash, puedes usar:

1. WSL (Windows Subsystem for Linux)
2. Git Bash
3. Docker Desktop con WSL2