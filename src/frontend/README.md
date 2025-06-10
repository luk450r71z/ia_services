# 🤖 Chat UI - Interfaz de Chat con IA

**Un frontend independiente de Chat con IA que NO maneja autenticación**. La autenticación se realiza previamente y el chat UI solo se conecta directamente al WebSocket para comenzar la conversación inmediatamente.

## 🎯 Propósito

El chat UI está diseñado para:
- **Conexión directa** al WebSocket sin autenticación
- **Interfaz moderna** y responsive para conversaciones
- **Integración rápida** desde `webui_url` de endpoints
- **Reconexión automática** en caso de desconexión
- **Estados visuales** claros (carga, error, completado)

## 📁 Estructura del Proyecto

```
src/frontend/
├── index.html                    # Página principal del chat UI
├── chat-ui.js                   # Punto de entrada de la aplicación
├── package.json                 # Configuración del proyecto
├── vite.config.js              # Configuración de Vite
├── public/                     # Archivos estáticos
├── src/                        # Código fuente
│   ├── ChatUIApp.vue          # Componente principal
│   ├── components/
│   │   └── ChatWidget.vue     # Widget de chat
│   └── pages/                 # Páginas adicionales (futuro)
└── README.md                   # Este archivo
```

## 🚀 Instalación y Configuración

### Prerrequisitos

- Node.js 16+ 
- npm 7+

### Instalación

```bash
cd src/frontend
npm install
```

### Configuración de WebSocket

El frontend obtiene la URL del WebSocket de varias formas:

**Opción 1: Session ID (RECOMENDADO)**
```
http://localhost:8080/?session_id=abc123
```
El frontend construye automáticamente: `ws://localhost:8000/api/chat/questionnarie/start/abc123`

**Opción 2: URL completa de WebSocket**
```
http://localhost:8080/?ws_url=ws://localhost:8000/api/chat/questionnarie/start/session_id
```

**Opción 3: Variable global de JavaScript**
```javascript
window.WEBSOCKET_URL = 'ws://localhost:8000/api/chat/questionnarie/start/session_id'
```

**Opción 4: Hash de la URL**
```
http://localhost:8080/#ws://localhost:8000/api/chat/questionnarie/start/session_id
```

### Personalizar Preguntas

Edita el archivo `public/questions.json` para personalizar las preguntas:

```json
[
  "¿Cuáles son tus principales fortalezas técnicas?",
  "¿Por qué te interesa trabajar en esta posición?",
  "Tu pregunta personalizada aquí..."
]
```

## 🎮 Uso

### Desarrollo

```bash
npm run dev
```

El chat UI estará disponible en `http://localhost:8080`

### Producción

```bash
npm run build
```

Los archivos compilados estarán en `dist/` listos para ser servidos desde `webui_url`.

### Servir en producción

```bash
npm run serve
```

Esto inicia un servidor en `http://0.0.0.0:8080` accesible desde cualquier IP.

## 🔧 Configuración Avanzada

### Variables de Entorno

Puedes configurar variables de entorno para diferentes ambientes:

```bash
# .env.development
VITE_API_BASE=http://localhost:8000
VITE_WS_RECONNECT_ATTEMPTS=3

# .env.production  
VITE_API_BASE=https://tu-servidor.com
VITE_WS_RECONNECT_ATTEMPTS=5
```

### Personalización de Estilos

Los estilos principales están en:
- `index.html` - Estilos del preloader y página base
- `src/ChatUIApp.vue` - Estilos del contenedor principal
- `src/components/ChatWidget.vue` - Estilos del chat

### Configuración de Red

Para deployment, ajusta `vite.config.js`:

```javascript
export default defineConfig({
  server: {
    port: 8080,
    host: '0.0.0.0', // Permite acceso externo
    strictPort: true
  },
  base: './', // Para rutas relativas
})
```

## 🔄 Ciclo de Vida

1. **Carga inicial**: Muestra preloader mientras se cargan los componentes
2. **Obtención de WebSocket**: Busca la URL del WebSocket desde parámetros/variables
3. **Conexión directa**: Se conecta al WebSocket sin autenticación
4. **Primer mensaje**: Recibe automáticamente el primer mensaje del agente
5. **Chat activo**: El usuario interactúa con el agente IA
6. **Finalización**: La conversación se completa automáticamente

## 📡 Conectividad

El chat UI **SOLO** usa WebSocket:

- **WebSocket** - Comunicación directa en tiempo real (sin autenticación)
- **NO usa APIs REST** - No hace llamadas HTTP para autenticación
- **Conexión directa** - Se conecta inmediatamente al WebSocket proporcionado

## 🛠️ Desarrollo

### Estructura de Componentes

```vue
<!-- ChatUIApp.vue -->
<template>
  <div class="chat-ui-container">
    <!-- Estados: loading, error, chat, completed -->
    <ChatWidget v-if="chatSession.isActive" />
  </div>
</template>
```

### Estados de la Aplicación

- `loading`: Conectando con el servidor
- `error`: Error en la conexión (con reintento)
- `connected`: Chat activo y funcional  
- `completed`: Conversación finalizada

### Eventos Principales

```javascript
// Eventos emitidos por ChatWidget
@conversation-complete="onConversationComplete"
@message-sent="onMessageSent"

// Manejo en ChatUIApp
const onConversationComplete = (summary) => {
  // Calcular estadísticas, mostrar resumen
}
```

## 📊 Monitoreo y Analytics

### Logs de Consola

El chat UI produce logs detallados:

```javascript
console.log('🚀 Chat UI iniciado desde webui_url')
console.log('🔐 Autenticación exitosa para webui_url')  
console.log('✅ Chat UI conectado correctamente')
```

### Métricas de Conversación

Se trackean automáticamente:
- Duración de la conversación
- Número de mensajes intercambiados
- Hora de inicio y finalización
- Estado de conexión

## 🔒 Seguridad

### Autenticación

El chat UI usa autenticación básica HTTP:

```javascript
const credentials = btoa(`${user}:${password}`)
Authorization: `Basic ${credentials}`
```

### WebSocket Seguro

- Reconexión automática con límites
- Manejo de códigos de error específicos
- Validación de mensajes JSON

## 🐛 Solución de Problemas

### Problemas Comunes

**Error: No se puede conectar al servidor**
```bash
# Verificar que la API esté corriendo
curl http://localhost:8000/api/chat/session/auth

# Verificar configuración de CORS
```

**Error: No se encontró session_id**
```bash
# Usar URL con session_id
http://localhost:8080/?session_id=tu_session_id

# O usar URL completa de WebSocket
http://localhost:8080/?ws_url=ws://localhost:8000/api/chat/questionnarie/start/session_id
```

**Chat no inicia automáticamente**
- Verificar que el endpoint `initiate_questionnarie` retorne `webui_url` con parámetros
- Revisar consola del navegador para errores
- Verificar que el WebSocket server esté corriendo

## 🧪 Testing

### Tests Unitarios

```bash
npm run test
```

### Tests E2E

```bash
npm run test:e2e
```

### Tests de WebSocket

```bash
# Probar conexión manual
wscat -c ws://localhost:8000/api/chat/questionnarie/start/test_session
```

## 📦 Build y Deployment

### Build para Producción

```bash
npm run build:production
```

### Deployment con Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 8080
CMD ["npm", "run", "serve"]
```

### Deployment con Nginx

```nginx
server {
    listen 8080;
    server_name localhost;
    
    location / {
        root /path/to/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

## 🤝 Contribución

Para contribuir al chat UI:

1. **Fork** del repositorio
2. **Crear rama** para feature: `git checkout -b feature/amazing-feature`
3. **Commit** cambios: `git commit -m 'Add amazing feature'`
4. **Push** a la rama: `git push origin feature/amazing-feature`
5. **Abrir Pull Request**

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 👥 Equipo

**Adaptiera Team** - Desarrollo y mantenimiento

---

*Chat UI v1.0.0 - Powered by Vue 3 + Vite* 