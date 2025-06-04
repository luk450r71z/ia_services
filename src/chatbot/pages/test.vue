<template>
  <div class="container">
    <h1>Chat en Tiempo Real</h1>
    
    <!-- Sección de autenticación -->
    <div v-if="!isAuthenticated" class="section">
      <h2>Autenticación</h2>
      <p>Presiona el botón para iniciar la conversación</p>
      <button 
        @click="iniciarConversacion" 
        :disabled="isInitializing"
        class="start-button"
      >
        {{ isInitializing ? 'Iniciando...' : 'Iniciar Conversación' }}
      </button>
      
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>
    </div>
    
    <!-- Sección de Chat Widget (solo se muestra cuando está autenticado) -->
    <div v-if="isAuthenticated" class="section">
      <div class="success-message">
        ✅ Sesión iniciada correctamente
      </div>
      <ChatWidget 
        :websocket-url="websocketUrl"
        :auth-token="authToken"
        :session-id="id_session"
        :questions="PREGUNTAS_PERSONALIZADAS"
        @message-sent="onMessageSent"
        @conversation-complete="onConversationComplete"
      />
    </div>
  </div>
</template>

<script setup>
import ChatWidget from '../components/chatwidget.vue'
import { ref } from 'vue'

// Estados reactivos
const isAuthenticated = ref(false)
const isInitializing = ref(false)
const authToken = ref(null)
const errorMessage = ref('')

// Configuración de la API
const API_BASE_URL = 'http://127.0.0.1:8000'

const SERVICE_CONFIG = {
  id_service: "3f91e6c2-1d43-4a77-9c17-6ab872a4b2db",
  password: "secure_password",
  user: "fabian"
}

// Preguntas personalizadas - extraer solo el texto
const PREGUNTAS_PERSONALIZADAS = [
  "¿Cuál es tu experiencia con Python?",
  "¿Has trabajado con FastAPI anteriormente?",
  "¿Cuáles son tus principales fortalezas técnicas?",
  "¿Por qué te interesa trabajar en esta posición?",
  "¿Tienes alguna pregunta para nosotros?"
]

// Generar un ID de sesión único para testing
const id_session = 'aedcd2e4-0c44-4d2d-95f0-bec8dd505b79'
const websocketUrl = 'ws://localhost:8000/api/chat/ws/' + id_session

// Función principal para iniciar conversación
const iniciarConversacion = async () => {
  isInitializing.value = true
  errorMessage.value = ''
  
  try {
    const token = await obtenerToken()
    
    if (!token) {
      throw new Error('No se pudo obtener el token de autenticación')
    }
    
    // Pasar el token y session_id al ChatWidget
    authToken.value = token
    isAuthenticated.value = true
    console.log('✅ Token obtenido correctamente')
    
  } catch (error) {
    console.error('Error al obtener token:', error)
    errorMessage.value = error.message || 'Error al obtener token'
  } finally {
    isInitializing.value = false
  }
}

// Función para obtener el token
const obtenerToken = async () => {
  // Codificar credenciales en Base64 para HTTP Basic Auth
  const credentials = btoa(`${SERVICE_CONFIG.user}:${SERVICE_CONFIG.password}`)
  
  const response = await fetch(`${API_BASE_URL}/api/chat/session/auth`, {
    method: 'POST',
    headers: {
      'accept': 'application/json',
      'Authorization': `Basic ${credentials}`
    }
  })
  
  if (!response.ok) {
    throw new Error(`Error al obtener token: ${response.status} ${response.statusText}`)
  }
  
  const data = await response.json()
  return data.id_session // Según el esquema SessionResponse
}

// Funciones para manejar eventos del ChatWidget
const onMessageSent = (message) => {
  console.log('Mensaje enviado:', message)
}

const onConversationComplete = (progress) => {
  console.log('Conversación completada:', progress)
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
</style>
  