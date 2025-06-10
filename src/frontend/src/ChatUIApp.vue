<template>
  <div class="chat-ui-container">
    <!-- Estado de carga -->
    <div v-if="loading" class="loading-section">
      <div class="loading-spinner"></div>
      <h2>{{ loadingMessage }}</h2>
      <div class="loading-progress">
        <div class="progress-bar" :style="{ width: loadingProgress + '%' }"></div>
      </div>
      <p class="connection-info">
        Estado: <span class="status" :class="connectionState">{{ connectionState }}</span>
      </p>
    </div>

    <!-- Estado de error -->
    <div v-else-if="error && !chatSession.isActive" class="error-section">
      <h2>❌ Error de Conexión</h2>
      <p class="error-message">{{ error }}</p>
      <div class="error-actions">
        <button @click="reiniciarServicio" class="retry-button">
          🔄 Reintentar Conexión
        </button>
        <p class="retry-info" v-if="retryCount > 0">
          Intento {{ retryCount }} de {{ config.maxRetries }}
        </p>
      </div>
    </div>

    <!-- Estado de chat activo -->
    <div v-else-if="chatSession.isActive" class="chat-section">
      <div class="header">
        <h1 class="header-title">🤖 Chat IA</h1>
        <p class="header-subtitle">Chat UI Independiente - Adaptiera</p>
        <div class="connection-status">
          <span class="status-indicator" :class="connectionState"></span>
          <span class="status-text">{{ connectionState === 'connected' ? 'Conectado' : 'Conectando...' }}</span>
        </div>
      </div>

      <ChatWidget 
        :websocket_url="chatSession.websocketUrl"
        @conversation-complete="onConversationComplete"
        @message-sent="onMessageSent"
        class="chat-widget"
      />

      <div class="footer">
        <small>Chat UI sin autenticación | Powered by Adaptiera Team</small>
      </div>
    </div>

    <!-- Estado de conversación completada -->
    <div v-else-if="chatSession.completed" class="completion-section">
      <h2>🎉 ¡Conversación Completada!</h2>
      <div class="stats-card">
        <h3>📊 Estadísticas de la Conversación</h3>
        <div v-if="conversationStats" class="stats-grid">
          <div class="stat-item">
            <span class="stat-label">Duración:</span>
            <span class="stat-value">{{ conversationStats.duration }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Mensajes:</span>
            <span class="stat-value">{{ conversationStats.messageCount }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Finalizado:</span>
            <span class="stat-value">{{ conversationStats.endTime }}</span>
          </div>
        </div>
      </div>
      <div class="completion-actions">
        <button @click="reiniciarServicio" class="restart-button">
          🔄 Nueva Conversación
        </button>
        <button @click="exportarConversacion" class="export-button">
          📥 Exportar Conversación
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import ChatWidget from './components/ChatWidget.vue'
import { ref, reactive, onMounted, computed } from 'vue'

// Configuración específica del chat-ui
const config = {
  autoRetry: true,
  maxRetries: 3,
  retryDelay: 2000
}

// Estados del chat-ui
const loading = ref(false)
const error = ref('')
const retryCount = ref(0)
const connectionState = ref('disconnected')
const loadingMessage = ref('Preparando conexión...')
const loadingProgress = ref(0)

// Estado de sesión
const chatSession = reactive({
  websocketUrl: '',
  isActive: false,
  completed: false,
  startTime: null
})

// Estadísticas de conversación
const conversationStats = ref(null)

// Progreso de carga calculado
const progressSteps = [
  { message: 'Preparando conexión...', progress: 20 },
  { message: 'Obteniendo URL de WebSocket...', progress: 50 },
  { message: 'Estableciendo conexión...', progress: 80 },
  { message: '¡Conectado! Esperando primer mensaje...', progress: 100 }
]

// Inicialización automática al montar el componente
onMounted(() => {
  console.log('🚀 Chat UI iniciado desde webui_url')
  chatSession.startTime = new Date()
  iniciarChatUI()
})

// Función para obtener la URL del WebSocket
const getWebSocketUrl = () => {
  const urlParams = new URLSearchParams(window.location.search)
  
  // Opción 1: Construir URL desde session_id (NUEVO MÉTODO PRINCIPAL)
  const sessionId = urlParams.get('session_id') || urlParams.get('id_session')
  if (sessionId) {
    const wsUrl = `ws://localhost:8000/api/chat/questionnarie/start/${sessionId}`
    console.log('🔗 URL de WebSocket construida desde session_id:', wsUrl)
    return wsUrl
  }
  
  // Opción 2: Desde parámetros de URL completa (método anterior)
  const wsUrl = urlParams.get('ws_url') || urlParams.get('websocket_url')
  if (wsUrl) {
    console.log('🔗 URL de WebSocket obtenida desde parámetros de URL')
    return wsUrl
  }
  
  // Opción 3: Desde variable global
  if (window.WEBSOCKET_URL) {
    console.log('🔗 URL de WebSocket obtenida desde variable global')
    return window.WEBSOCKET_URL
  }
  
  // Opción 4: Desde hash de la URL
  const hash = window.location.hash.substring(1)
  if (hash && (hash.startsWith('ws://') || hash.startsWith('wss://'))) {
    console.log('🔗 URL de WebSocket obtenida desde hash de URL')
    return hash
  }
  
  throw new Error('No se encontró session_id o URL de WebSocket. Proporciona el session_id mediante: ?session_id=... o la URL completa mediante: ?ws_url=...')
}

// Función para actualizar progreso de carga
const updateLoadingProgress = (stepIndex) => {
  if (stepIndex < progressSteps.length) {
    const step = progressSteps[stepIndex]
    loadingMessage.value = step.message
    loadingProgress.value = step.progress
  }
}

// Función principal del chat-ui
const iniciarChatUI = async () => {
  if (retryCount.value >= config.maxRetries) {
    error.value = `Se alcanzó el máximo de intentos (${config.maxRetries}). Verifica la URL del WebSocket.`
    connectionState.value = 'failed'
    return
  }

  error.value = ''
  chatSession.completed = false
  loading.value = true
  connectionState.value = 'connecting'
  
  try {
    console.log(`🔄 Intento de conexión ${retryCount.value + 1}/${config.maxRetries}`)
    
    // Progreso: Preparando conexión
    updateLoadingProgress(0)
    await new Promise(resolve => setTimeout(resolve, 300))
    
    // Progreso: Obteniendo URL de WebSocket
    updateLoadingProgress(1)
    chatSession.websocketUrl = getWebSocketUrl()
    console.log('🔗 URL de WebSocket configurada:', chatSession.websocketUrl)
    await new Promise(resolve => setTimeout(resolve, 400))
    
    // Progreso: Estableciendo conexión
    updateLoadingProgress(2)
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // Progreso: Conectado
    updateLoadingProgress(3)
    await new Promise(resolve => setTimeout(resolve, 300))
    
    console.log('✅ Chat UI listo para conectar al WebSocket')
    chatSession.isActive = true
    connectionState.value = 'connected'
    retryCount.value = 0
    
  } catch (err) {
    console.error('❌ Error en chat UI:', err)
    error.value = err.message || 'Error al inicializar el chat UI'
    connectionState.value = 'error'
    retryCount.value++
    
    // Auto-retry solo si no es un error de configuración
    if (config.autoRetry && retryCount.value < config.maxRetries && !err.message?.includes('No se encontró URL')) {
      const delay = Math.min(config.retryDelay * retryCount.value, 8000)
      console.log(`🔄 Reintentando en ${delay}ms...`)
      connectionState.value = 'reconnecting'
      setTimeout(() => {
        iniciarChatUI()
      }, delay)
    }
  } finally {
    loading.value = false
  }
}



// Manejadores de eventos
const onConversationComplete = (summary) => {
  console.log('🏁 Conversación completada:', summary)
  
  // Calcular estadísticas de la conversación
  const endTime = new Date()
  const duration = Math.round((endTime - chatSession.startTime) / 1000 / 60)
  conversationStats.value = {
    duration: `${duration} minutos`,
    messageCount: summary?.messageCount || 'N/A',
    endTime: endTime.toLocaleString()
  }
  
  chatSession.isActive = false
  chatSession.websocketUrl = ''
  chatSession.completed = true
  connectionState.value = 'completed'
  error.value = ''
}

const onMessageSent = (message) => {
  console.log('📤 Mensaje enviado desde chat UI:', message)
}

const reiniciarServicio = () => {
  console.log('🔄 Reiniciando chat UI...')
  retryCount.value = 0
  chatSession.isActive = false
  chatSession.completed = false
  chatSession.websocketUrl = ''
  chatSession.startTime = new Date()
  connectionState.value = 'disconnected'
  conversationStats.value = null
  loadingProgress.value = 0
  iniciarChatUI()
}

const exportarConversacion = () => {
  // Funcionalidad para exportar la conversación
  const data = {
    timestamp: new Date().toISOString(),
    stats: conversationStats.value,
    chatUI: 'chat-ia',
    version: '1.0.0'
  }
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `conversacion-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  
  console.log('📥 Conversación exportada')
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

.loading-progress {
  margin-top: 20px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  height: 8px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  border-radius: 10px;
  transition: width 0.5s ease;
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

.retry-info {
  margin-top: 10px;
  font-size: 14px;
  opacity: 0.8;
}

.chat-section {
  width: 100%;
  max-width: 1200px;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  text-align: center;
  color: white;
  padding: 20px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(15px);
  border-radius: 15px 15px 0 0;
  border: 1px solid rgba(255, 255, 255, 0.2);
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
  margin-top: 10px;
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

.completion-section {
  text-align: center;
  color: white;
  padding: 50px;
  border-radius: 20px;
  background: rgba(76, 175, 80, 0.1);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(76, 175, 80, 0.3);
  max-width: 600px;
  width: 100%;
}

.stats-card {
  margin: 30px 0;
  padding: 25px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 15px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.stats-grid {
  display: grid;
  gap: 15px;
  margin-top: 20px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.stat-label {
  font-weight: 600;
  opacity: 0.9;
}

.stat-value {
  font-weight: 700;
  color: #4CAF50;
}

.completion-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 30px;
}

.restart-button, .export-button {
  padding: 12px 25px;
  border-radius: 10px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
  color: white;
}

.restart-button {
  background: rgba(76, 175, 80, 0.2);
}

.export-button {
  background: rgba(33, 150, 243, 0.2);
}

.restart-button:hover, .export-button:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.3);
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
  
  .completion-actions {
    flex-direction: column;
    align-items: stretch;
  }
  
  .restart-button, .export-button {
    width: 100%;
  }
}
</style> 