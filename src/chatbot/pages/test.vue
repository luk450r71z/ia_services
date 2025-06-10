<template>
  <div class="container">
    <h1>Chat en Tiempo Real</h1>
    
    <!-- Sección de autenticación -->
    <div v-if="!chatSession.isActive" class="section">
      <h2>Autenticación</h2>
      <p>Presiona el botón para iniciar la conversación</p>
      <button 
        @click="iniciarConversacion" 
        :disabled="loading"
        class="start-button"
      >
        {{ loading ? 'Iniciando...' : 'Iniciar Conversación' }}
      </button>
      
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
      
      <div v-if="chatSession.completed" class="completion-message">
        ✅ Conversación completada exitosamente. El chat se ha cerrado.
      </div>
    </div>
    
    <!-- Sección de Chat Widget -->
    <div v-if="chatSession.isActive" class="section">
      <div class="success-message">
        ✅ Sesión iniciada correctamente
      </div>
      <ChatWidget 
        :session-id="chatSession.id"
        :websocket_url="chatSession.websocketUrl"
        :service-type="config.type"
        @conversation-complete="onConversationComplete"
      />
    </div>
  </div>
</template>

<script setup>
import ChatWidget from '../components/chatwidget.vue'
import { ref, reactive } from 'vue'

// Configuración centralizada
const config = {
  apiBase: 'http://localhost:8000',
  credentials: {
    user: 'fabian',
    password: 'secure_password'
  },
  type: 'questionnarie',
  defaultQuestions: [
    "¿Cuáles son tus principales fortalezas técnicas?",
    "¿Por qué te interesa trabajar en esta posición?",
    "¿Tienes alguna pregunta para nosotros?"
  ],
  configs: {
    webhook_url: "",
    email: ["santiago.ferrero@adaptiera.team", "lucas.ortiz@adaptiera.team"],
    avatar: false,
  }
}

// Estados simplificados
const loading = ref(false)
const error = ref('')

// Estado de sesión consolidado
const chatSession = reactive({
  id: '',
  websocketUrl: '',
  isActive: false,
  completed: false
})

// Función simplificada para obtener preguntas
const getQuestions = async () => {
  try {
    const response = await fetch('/questions.json')
    return response.ok ? await response.json() : config.defaultQuestions
  } catch {
    return config.defaultQuestions
  }
}

// Función principal simplificada
const iniciarConversacion = async () => {
  error.value = ''
  chatSession.completed = false
  loading.value = true
  
  try {
    const questions = await getQuestions()
    const sessionData = await createAndInitializeSession(questions)
    
    chatSession.id = sessionData.id_session
    chatSession.websocketUrl = sessionData.urls?.websocket_url
    
    if (!chatSession.websocketUrl) {
      throw new Error('No se pudo obtener websocket_url')
    }
    
    chatSession.isActive = true
  } catch (err) {
    error.value = err.message || 'Error en la inicialización'
  } finally {
    loading.value = false
  }
}

// Función unificada para crear e inicializar sesión
const createAndInitializeSession = async (questions) => {
  // Paso 1: Crear sesión
  const credentials = btoa(`${config.credentials.user}:${config.credentials.password}`)
  
  const authResponse = await fetch(`${config.apiBase}/api/chat/session/auth`, {
    method: 'POST',
    headers: {
      'accept': 'application/json',
      'Authorization': `Basic ${credentials}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      type: config.type,
      content: { questions },
      configs: config.configs
    })
  })
  
  if (!authResponse.ok) {
    const errorText = await authResponse.text()
    throw new Error(`Error al crear sesión: ${authResponse.status} - ${errorText}`)
  }
  
  const authData = await authResponse.json()
  
  // Paso 2: Inicializar servicio
  const initResponse = await fetch(`${config.apiBase}/api/chat/${config.type}/initiate`, {
    method: 'POST',
    headers: {
      'accept': 'application/json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      id_session: authData.id_session
    })
  })
  
  if (!initResponse.ok) {
    const errorText = await initResponse.text()
    throw new Error(`Error al inicializar servicio: ${initResponse.status} - ${errorText}`)
  }
  
  return await initResponse.json()
}

// Función para manejar finalización del chat
const onConversationComplete = () => {
  chatSession.isActive = false
  chatSession.id = ''
  chatSession.websocketUrl = ''
  chatSession.completed = true
  error.value = ''
}
</script>

<style>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  font-family: sans-serif;
  text-align: center;
}

.section {
  margin: 3rem 0;
  padding: 2rem;
  border-radius: 12px;
  background-color: #f8f9fa;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.start-button {
  background-color: #28a745;
  color: white;
  border: none;
  padding: 12px 24px;
  font-size: 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.3s;
  margin-top: 1rem;
}

.start-button:hover:not(:disabled) {
  background-color: #218838;
}

.start-button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.error-message {
  color: #dc3545;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  padding: 12px;
  margin-top: 1rem;
}

.success-message {
  color: #155724;
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 1rem;
}

.completion-message {
  color: #0c5460;
  background-color: #d1ecf1;
  border: 1px solid #bee5eb;
  border-radius: 4px;
  padding: 12px;
  margin-top: 1rem;
  font-weight: bold;
}
</style>
  