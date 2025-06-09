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
      
      <div v-if="conversationCompleted" class="completion-message">
        ✅ Conversación completada exitosamente. El chat se ha cerrado.
      </div>
    </div>
    
    <!-- Sección de Chat Widget (solo se muestra cuando está autenticado) -->
    <div v-if="isAuthenticated" class="section">
      <div class="success-message">
        ✅ Sesión iniciada correctamente
      </div>
      <ChatWidget 
        :session-id="id_session"
        :resource_uri="resource_uri"
        :service-type="SERVICE_CONFIG.type"
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
const errorMessage = ref('')
const conversationCompleted = ref(false)

// Configuración de la API
const SERVICE_CONFIG = {
  password: "secure_password",
  user: "fabian",
  type: "questionnarie" // Tipo de servicio configurable
}

// Preguntas cargadas desde JSON
const preguntasPersonalizadas = ref([])

// ID de sesión se generará dinámicamente en la autenticación
const id_session = ref('') // Se llenará después de la autenticación
const resource_uri = ref('') // Se establecerá durante la inicialización

// Función para cargar preguntas
const cargarPreguntas = async () => {
  try {
    const response = await fetch('/questions.json')
    if (!response.ok) throw new Error(`Error ${response.status}`)
    preguntasPersonalizadas.value = await response.json()
  } catch (error) {
    preguntasPersonalizadas.value = [
      "¿Cuáles son tus principales fortalezas técnicas?",
      "¿Por qué te interesa trabajar en esta posición?",
      "¿Tienes alguna pregunta para nosotros?"
    ]
  }
}

// Función principal para iniciar conversación
const iniciarConversacion = async () => {
  errorMessage.value = ''
  conversationCompleted.value = false
  isInitializing.value = true
  
  try {
    const sessionId = await obtenerToken()
    await cargarPreguntas()
    const serviceData = await inicializarServicio(sessionId)

    id_session.value = sessionId
    resource_uri.value = serviceData.urls?.resource_uri
    
    if (!resource_uri.value) {
      throw new Error('No se pudo obtener resource_uri')
    }
    
    isAuthenticated.value = true
  } catch (error) {
    errorMessage.value = error.message || 'Error en la inicialización'
  } finally {
    isInitializing.value = false
  }
}

// Función para obtener el token (Paso 1)
const obtenerToken = async () => {
  const credentials = btoa(`${SERVICE_CONFIG.user}:${SERVICE_CONFIG.password}`)
  
  const response = await fetch(`http://localhost:8000/api/chat/session/auth`, {
    method: 'POST',
    headers: {
      'accept': 'application/json',
      'Authorization': `Basic ${credentials}`
    }
  })
  
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Error al obtener token: ${response.status} - ${errorText}`)
  }
  
  const data = await response.json()
  return data.id_session
}

// Función para inicializar servicio con preguntas (Paso 2)
const inicializarServicio = async (sessionId) => {
  const response = await fetch(`http://localhost:8000/api/chat/${SERVICE_CONFIG.type}/initiate`, {
    method: 'POST',
    headers: {
      'accept': 'application/json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      id_session: sessionId,
      type: SERVICE_CONFIG.type,
      content: {
        questions: preguntasPersonalizadas.value
      },
      configs: {
        "webhook_url": "",
        "email": ["lucasd@gmail.com", "santiago.ferrero@adaptiera.com"],
        "avatar": false,
      }
    })
  })
  
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Error al inicializar servicio: ${response.status} - ${errorText}`)
  }
  
  return await response.json()
}

// Funciones para manejar eventos del ChatWidget
const onConversationComplete = () => {
  isAuthenticated.value = false
  id_session.value = ''
  resource_uri.value = ''
  errorMessage.value = ''
  conversationCompleted.value = true
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
  