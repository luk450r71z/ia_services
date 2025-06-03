# IA Services 🤖

**Plataforma de servicios de inteligencia artificial con agente conversacional**

## 📋 Descripción

IA Services es una plataforma completa que combina un backend robusto en FastAPI con un frontend interactivo en Vue.js para proporcionar servicios de inteligencia artificial, especialmente enfocado en chatbots conversacionales para entrevistas y otras aplicaciones.

## 🏗️ Arquitectura del Proyecto

```
ia_services/
├── api/                          # Backend FastAPI
│   ├── main.py                   # Punto de entrada principal de la API
│   ├── auth/                     # Sistema de autenticación
│   │   ├── router.py            # Endpoints de autenticación y servicios
│   │   ├── config.py            # Configuración de autenticación
│   │   ├── models/              # Modelos de datos
│   │   ├── db/                  # Base de datos
│   │   └── session/             # Manejo de sesiones JWT
│   └── conversational_agent/    # Agente conversacional
│       ├── router.py            # WebSocket y endpoints del chat
│       └── models/              # Esquemas de datos del chat
├── src/                         # Frontend Vue.js
│   ├── main.js                 # Punto de entrada de Vue
│   ├── App.vue                 # Componente principal
│   └── chatbot/                # Componentes del chatbot
│       ├── components/         # Componentes reutilizables
│       └── pages/              # Páginas de la aplicación
├── index.html                  # Página principal del frontend
├── package.json                # Dependencias de Node.js
├── vite.config.js              # Configuración de Vite
├── requirements.txt            # Dependencias de Python
└── assets/                     # Recursos estáticos
```

## ✨ Características Principales

### 🔐 Sistema de Autenticación
- **Autenticación JWT**: Tokens seguros para acceso a servicios
- **Gestión de sesiones**: Control de sesiones activas por usuario
- **Discovery de servicios**: Endpoint para descubrir servicios disponibles
- **Múltiples servicios**: Soporte para diferentes tipos de IA

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
pip install -r requirements.txt
```

#### Ejecutar el Servidor API
```bash
cd api
python main.py
```

El servidor estará disponible en: `http://localhost:8000`

### 3. Configurar el Frontend

#### Instalar Dependencias de Node.js
```bash
npm install
# o si prefieres yarn
yarn install
```

#### Ejecutar el Servidor de Desarrollo
```bash
npm run dev
# o si prefieres yarn
yarn dev
```

El frontend estará disponible en: `http://localhost:3000`

#### Construir para Producción
```bash
npm run build
# o si prefieres yarn
yarn build
```

## 📚 API Documentation

### Endpoints Principales

#### Autenticación
- `POST /auth/session/token` - Obtener token de acceso
- `POST /auth/session/init` - Inicializar sesión de servicio

#### Servicios
- `GET /services/discovery` - Descubrir servicios disponibles

#### Chat Conversacional
- `WebSocket /chat/ws/{session_id}` - Conexión WebSocket para chat
- `GET /chat/sessions/active` - Obtener sesiones activas
- `DELETE /chat/sessions/{session_id}` - Cerrar sesión específica

### Documentación Interactiva
Una vez ejecutando el servidor, visita:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔧 Configuración

### Variables de Entorno (Backend)
Crea un archivo `.env` en el directorio `api/` con:
```env
SECRET_KEY=tu_clave_secreta_jwt
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Configuración del Frontend
El frontend se conecta automáticamente al backend en `localhost:8000`. Para cambiar la URL, modifica las configuraciones en los componentes Vue.

## 🧪 Uso Básico

### 1. Autenticación
```javascript
// Solicitar token de acceso
const response = await fetch('/auth/session/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        user: 'usuario',
        password: 'contraseña',
        id_service: 'uuid-del-servicio'
    })
});
```

### 2. Iniciar Chat
```javascript
// Conectar WebSocket
const ws = new WebSocket('ws://localhost:8000/chat/ws/session-id');

// Enviar mensaje
ws.send(JSON.stringify({
    content: 'Hola, ¿cómo estás?'
}));
```

### 3. Interfaz Web
1. Ejecuta `npm run dev` para el frontend
2. Ejecuta `python api/main.py` para el backend  
3. Abre `http://localhost:3000` en tu navegador
4. Haz clic en "Iniciar Conversación"
5. Comienza a chatear con el agente

## 🛠️ Tecnologías Utilizadas

### Backend
- **FastAPI**: Framework web moderno y rápido
- **WebSockets**: Comunicación en tiempo real
- **JWT**: Autenticación segura
- **Uvicorn**: Servidor ASGI de alto rendimiento
- **Python-multipart**: Manejo de formularios

### Frontend
- **Vue.js 3**: Framework progresivo de JavaScript
- **Vite**: Build tool rápido y moderno
- **HTML5/CSS3**: Estructura y estilos modernos
- **WebSocket API**: Conexión en tiempo real con el backend

## 🚀 Despliegue

### Desarrollo Local
```bash
# Terminal 1: Backend
cd api
python main.py

# Terminal 2: Frontend
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
- `python api/main.py` - Ejecutar servidor de desarrollo
- `uvicorn api.main:app --reload` - Alternativa con uvicorn

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