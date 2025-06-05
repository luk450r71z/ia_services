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