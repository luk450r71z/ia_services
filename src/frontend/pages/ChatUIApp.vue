<template>
  <div class="chat-ui-container">
    <div class="chat-section">
      <div class="header">
        <div class="header-main">
          <div class="header-text">
            <h1 class="header-title">🤖 AI Chat</h1>
            <p class="header-subtitle">Independent Chat UI - Adaptiera</p>
          </div>
          
          <!-- Avatar independent from ChatWidget -->
          <div v-if="avatarConfig.show" class="header-avatar">
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
            {{ chatSession.completed ? 'Conversation Ended' : 
               connectionState === 'connected' ? 'Connected' : 'Connecting...' }}
          </span>
        </div>
      </div>

      <ChatWidget 
        v-if="chatSession.websocketUrl"
        :websocket_url="chatSession.websocketUrl"
        :disabled="chatSession.completed"
        @conversation-complete="onConversationComplete"
        @message-sent="onMessageSent"
        @ui-config="handleUIConfigMessage"
        @close-widget="onCloseWidget"
        @connection-state-change="onConnectionStateChange"
        class="chat-widget"
      />

      <!-- Mensaje de finalización cuando el widget se cierra -->
      <div v-if="chatSession.completed" class="completion-message">
        <div class="completion-content">
          <h2>✅ Questionnaire Completed</h2>
          <p>Thank you for completing the questionnaire. The conversation has ended.</p>
        </div>
      </div>

      <div class="footer">
        <small>Powered by Adaptiera Team</small>
      </div>
    </div>
  </div>
</template>

<script setup>
import ChatWidget from '../components/ChatWidget.vue'
import Avatar from '../components/Avatar.vue'
import { ref, reactive, onMounted } from 'vue'

// Session state
const chatSession = reactive({
  websocketUrl: '',
  completed: false
})

// Connection state (controlled by ChatWidget)
const connectionState = ref('connecting')

// Avatar configuration
const avatarConfig = ref({
  show: false,
  url: null,
  name: 'AI Assistant'
})

// Function to configure avatar from WebSocket
const handleUIConfigMessage = (data) => {
  console.log('📥 ChatUIApp received ui-config event:', data)
  if (data.type === 'ui_config' && data.data) {
    const avatarData = data.data.avatar
    
    if (typeof avatarData === 'boolean') {
      avatarConfig.value.show = avatarData
      console.log('👤 Avatar:', avatarData ? 'enabled' : 'disabled')
    } else if (typeof avatarData === 'object' && avatarData !== null) {
      avatarConfig.value = {
        show: Boolean(avatarData.show),
        url: avatarData.url || avatarData.image || null,
        name: avatarData.name || 'AI Assistant'
      }
      console.log('👤 Avatar configured:', avatarConfig.value)
    } else {
      avatarConfig.value.show = false
      console.log('👤 Avatar disabled')
    }
  } else {
    console.log('⚠️ Invalid ui_config:', data)
  }
}

// Function to get WebSocket URL
const getWebSocketUrl = () => {
  const pathParts = window.location.pathname.split('/').filter(Boolean)
  const idSession = pathParts[0]
  if (!idSession) {
    throw new Error('No id_session found in route. Use a URL like http://localhost:8080/{id_session}')
  }
  return `ws://localhost:8000/api/chat/questionnaire/start/${idSession}`
}

// Event handlers
const onConversationComplete = (summary) => {
  console.log('🏁 Conversation completed:', summary)
  chatSession.completed = true
  connectionState.value = 'completed'
  console.log('🔒 Chat locked - conversation ended')
}

const onMessageSent = (message) => {
  console.log('📤 Message sent from chat UI:', message)
}

const onCloseWidget = () => {
  console.log('🔒 Chat Widget closed')
  chatSession.completed = true
  connectionState.value = 'completed'
}

const onConnectionStateChange = (state) => {
  console.log('🔗 ChatWidget connection state changed:', state)
  connectionState.value = state
}

// Initialize on mount
onMounted(async () => {
  console.log('🚀 Chat UI started')
  try {
    chatSession.websocketUrl = getWebSocketUrl()
    console.log('🔗 WebSocket URL configured:', chatSession.websocketUrl)
  } catch (err) {
    console.error('❌ Error getting WebSocket URL:', err)
    connectionState.value = 'error'
  }
})
</script>

<style>
/* Estilos globales */
:root {
  background: #4a5568;
}

html, 
body {
  margin: 0;
  padding: 0;
  background: #4a5568;
  min-height: 100vh;
}
</style>

<style scoped>
.chat-ui-container {
  min-height: 100vh;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: #4a5568;
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.chat-section {
  width: 100%;
  max-width: 1200px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
}

.header {
  color: #2d3748;
  padding: 20px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(15px);
  border-radius: 15px 15px 0 0;
  border: 1px solid #e2e8f0;
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
  color: #4a5568;
}

.header-title {
  margin: 0 0 10px 0;
  font-size: 2.5em;
  font-weight: 700;
  color: #2d3748;
}

.header-subtitle {
  margin: 0;
  font-size: 1.1em;
  opacity: 0.8;
  color: #4a5568;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9em;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #a0aec0;
}

.status-indicator.connected {
  background-color: #4a5568;
}

.status-indicator.disconnected,
.status-indicator.error {
  background-color: #718096;
}

.status-text {
  opacity: 0.8;
  color: #4a5568;
}

.completion-message {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(8px);
  background: rgba(74, 85, 104, 0.7);
  z-index: 1000;
}

.completion-content {
  background: white;
  padding: 40px;
  border-radius: 15px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  max-width: 500px;
  width: 90%;
  text-align: center;
  border: 1px solid #e2e8f0;
}

.completion-content h2 {
  margin: 0 0 15px 0;
  color: #4a5568;
}

.completion-content p {
  margin: 0;
  color: #2d3748;
  font-size: 1.1em;
  line-height: 1.5;
}

.footer {
  text-align: center;
  padding: 20px;
  color: #4a5568;
  opacity: 0.7;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style> 