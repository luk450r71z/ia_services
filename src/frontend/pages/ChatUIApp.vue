<template>
  <div class="chat-ui-container">
    <!-- Estado de carga -->
    <div v-if="loading" class="loading-section">
      <div class="loading-spinner"></div>
      <h2>{{ loadingMessage }}</h2>
      <p class="connection-info">
        Estado: <span class="status" :class="connectionState">{{ connectionState }}</span>
      </p>
    </div>

    <!-- Estado de error -->
    <div v-else-if="error && !chatSession.isActive" class="error-section">
      <h2>❌ Error de Conexión</h2>
      <p class="error-message">{{ error }}</p>
      <div class="error-actions">
        <button @click="iniciarChatUI" class="retry-button">
          🔄 Reintentar Conexión
        </button>
      </div>
    </div>

    <!-- Estado de chat activo o completado -->
    <div v-else-if="chatSession.isActive || chatSession.completed" class="chat-section">
      <div class="header">
        <div class="header-main">
          <div class="header-text">
            <h1 class="header-title">🤖 Chat IA</h1>
            <p class="header-subtitle">Chat UI Independiente - Adaptiera</p>
          </div>
          
          <!-- Avatar independiente del ChatWidget -->
          <div v-if="showAvatar" class="header-avatar">
            <Avatar 
              :name="avatarConfig.name"
              :src="avatarConfig.url"
              size="lg"
            />
            <span class="avatar-label">{{ avatarConfig.name }}</span>
          </div>
        </div>
        
        <div class="connection-status">
          <span class="status-indicator" :class="connectionState"></span>
          <span class="status-text">
            {{ chatSession.completed ? 'Conversación Finalizada' : 
               connectionState === 'connected' ? 'Conectado' : 'Conectando...' }}
          </span>
        </div>
        
        <!-- DEBUG: Mostrar estado de configuración -->
        <div class="debug-info">
          <small>
            👤 Avatar: {{ showAvatar ? 'ON' : 'OFF' }}
            {{ avatarConfig.url ? ` | 🖼️ Con imagen` : ` | 📝 Solo iniciales` }}
            {{ chatSession.completed ? ' | 🔒 Chat Finalizado' : '' }}
          </small>
        </div>
      </div>

      <ChatWidget 
        :websocket_url="chatSession.websocketUrl"
        :disabled="chatSession.completed"
        @conversation-complete="onConversationComplete"
        @message-sent="onMessageSent"
        @ui-config="handleUIConfigMessage"
        class="chat-widget"
      />

      <div class="footer">
        <small>Chat UI sin autenticación | Powered by Adaptiera Team</small>
      </div>
    </div>
  </div>
</template>

<script setup>
import ChatWidget from '../components/ChatWidget.vue'
import Avatar from '../components/Avatar.vue'
import { ref, reactive, onMounted, computed } from 'vue'

// Estados del chat-ui
const loading = ref(false)
const error = ref('')
const connectionState = ref('disconnected')
const loadingMessage = ref('Preparando conexión...')

// Estado de sesión
const chatSession = reactive({
  websocketUrl: '',
  isActive: false,
  completed: false,
  startTime: null
})



// Configuración de Avatar
const showAvatar = ref(false)
const avatarConfig = ref({
  show: false,
  url: null,
  name: 'Asistente IA'
})


// Función para configurar avatar desde WebSocket
const handleUIConfigMessage = (data) => {
  console.log('📥 ChatUIApp recibió evento ui-config:', data)
  if (data.type === 'ui_config' && data.data) {
    const avatarData = data.data.avatar
    
    if (typeof avatarData === 'boolean') {
      // Configuración simple: solo true/false
      showAvatar.value = avatarData
      avatarConfig.value.show = avatarData
      console.log('👤 Avatar:', showAvatar.value ? 'habilitado' : 'deshabilitado')
    } else if (typeof avatarData === 'object' && avatarData !== null) {
      // Configuración avanzada: objeto con propiedades
      showAvatar.value = Boolean(avatarData.show)
      avatarConfig.value = {
        show: showAvatar.value,
        url: avatarData.url || avatarData.image || null,
        name: avatarData.name || 'Asistente IA'
      }
      console.log('👤 Avatar configurado:', avatarConfig.value)
    } else {
      showAvatar.value = false
      avatarConfig.value.show = false
      console.log('👤 Avatar deshabilitado')
    }
  } else {
    console.log('⚠️ ui_config inválido:', data)
  }
}

// Inicialización automática al montar el componente
onMounted(() => {
  console.log('🚀 Chat UI iniciado desde webui_url')
  chatSession.startTime = new Date()
  iniciarChatUI()
})

// Función para obtener la URL del WebSocket
const getWebSocketUrl = () => {
  // Extraer id_session de la ruta, asumiendo formato /{id_session}
  const pathParts = window.location.pathname.split('/').filter(Boolean)
  const idSession = pathParts[0] // Primer segmento después de /
  if (idSession) {
    const wsUrl = `ws://localhost:8000/api/chat/questionnaire/start/${idSession}`
    console.log('🔗 URL de WebSocket construida desde pathname:', wsUrl)
    return wsUrl
  }
  throw new Error('No se encontró id_session en la ruta. Usa una URL como http://localhost:8080/{id_session}')
}

// Función principal del chat-ui (simplificada)
const iniciarChatUI = async () => {
  error.value = ''
  loading.value = true
  connectionState.value = 'connecting'
  
  try {
    loadingMessage.value = 'Obteniendo URL de WebSocket...'
    chatSession.websocketUrl = getWebSocketUrl()
    console.log('🔗 URL de WebSocket configurada:', chatSession.websocketUrl)
    
    loadingMessage.value = 'Conectando...'
    await new Promise(resolve => setTimeout(resolve, 500))
    
    console.log('✅ Chat UI listo')
    chatSession.isActive = true
    connectionState.value = 'connected'
    
  } catch (err) {
    console.error('❌ Error en chat UI:', err)
    error.value = err.message || 'Error al inicializar el chat UI'
    connectionState.value = 'error'
  } finally {
    loading.value = false
  }
}



// Manejadores de eventos
const onConversationComplete = (summary) => {
  console.log('🏁 Conversación completada:', summary)
  
  // Marcar conversación como completada sin cambiar la vista
  chatSession.completed = true
  connectionState.value = 'completed'
  error.value = ''
  console.log('🔒 Chat bloqueado - conversación finalizada')
}

const onMessageSent = (message) => {
  console.log('📤 Mensaje enviado desde chat UI:', message)
}


</script>

<style scoped>
.chat-ui-container {
  min-height: 100vh;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.loading-section {
  text-align: center;
  color: white;
  padding: 50px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  max-width: 400px;
  width: 100%;
}

.loading-spinner {
  width: 70px;
  height: 70px;
  border: 5px solid rgba(255, 255, 255, 0.3);
  border-left: 5px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 25px;
}



.connection-info {
  margin-top: 15px;
  font-size: 14px;
  opacity: 0.9;
}

.status {
  font-weight: 600;
  text-transform: capitalize;
}

.status.connecting { color: #ffc107; }
.status.connected { color: #4CAF50; }
.status.reconnecting { color: #ff9800; }
.status.error { color: #f44336; }
.status.failed { color: #d32f2f; }

.error-section {
  text-align: center;
  color: white;
  padding: 50px;
  border-radius: 20px;
  background: rgba(244, 67, 54, 0.1);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(244, 67, 54, 0.3);
  max-width: 500px;
  width: 100%;
}

.error-message {
  margin: 20px 0;
  padding: 15px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  font-weight: 500;
}

.error-actions {
  margin-top: 25px;
}

.retry-button {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.3);
  padding: 12px 25px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
}

.retry-button:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}



.chat-section {
  width: 100%;
  max-width: 1200px;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  color: white;
  padding: 20px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(15px);
  border-radius: 15px 15px 0 0;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 15px;
}

.header-text {
  text-align: left;
  flex: 1;
}

.header-avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.avatar-label {
  font-size: 0.85em;
  font-weight: 600;
  opacity: 0.9;
  text-align: center;
}



.header-title {
  margin: 0 0 10px 0;
  font-size: 2.5em;
  font-weight: 700;
}

.header-subtitle {
  margin: 0 0 15px 0;
  font-size: 1.1em;
  opacity: 0.9;
}

.connection-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-indicator.connected {
  background: #4CAF50;
}

.status-indicator.connecting {
  background: #ffc107;
}

.status-text {
  font-size: 0.9em;
  font-weight: 500;
}



.debug-info {
  margin-top: 10px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  font-size: 0.8em;
  opacity: 0.8;
}

.chat-widget {
  flex: 1;
  border-radius: 0;
  border-top: none;
}

.footer {
  text-align: center;
  color: white;
  padding: 15px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(15px);
  border-radius: 0 0 15px 15px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-top: none;
  opacity: 0.8;
}



@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Responsive */
@media (max-width: 768px) {
  .chat-ui-container {
    padding: 10px;
  }
  
  .header-title {
    font-size: 2em;
  }
  
  .header-main {
    flex-direction: column;
    align-items: center;
    gap: 15px;
  }
  
  .header-text {
    text-align: center;
  }
}
</style> 