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
        <br>
        <small>Puedes iniciar una nueva conversación presionando el botón.</small>
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
const errorMessage = ref('')
const conversationCompleted = ref(false)

// Configuración de la API
const SERVICE_CONFIG = {
  base_url: 'http://127.0.0.1:8000',
  password: "secure_password",
  user: "fabian",
  type: "questionnarie" // Tipo de servicio configurable
}

// Preguntas personalizadas - extraer solo el texto
const PREGUNTAS_PERSONALIZADAS = [
  "¿Cuál es tu experiencia con Python?",
  "¿Has trabajado con FastAPI anteriormente?",
  "¿Cuáles son tus principales fortalezas técnicas?",
  "¿Por qué te interesa trabajar en esta posición?",
  "¿Tienes alguna pregunta para nosotros?"
]

// ID de sesión se generará dinámicamente en la autenticación
const id_session = ref('') // Se llenará después de la autenticación
const resource_uri = ref('') // Se establecerá durante la inicialización

// Función principal para iniciar conversación
const iniciarConversacion = async () => {
  errorMessage.value = ''
  conversationCompleted.value = false
  
  try {
    // Paso 1: Obtener token y crear sesión
    console.log('🔐 Paso 1: Autenticación...')
    const sessionId = await obtenerToken()
    
    if (!sessionId) {
      throw new Error('No se pudo obtener el token de autenticación')
    }
    
    // Paso 2: Inicializar servicio con preguntas
    console.log('🔧 Paso 2: Inicializando servicio con preguntas...')
    isInitializing.value = true
    const serviceData = await inicializarServicio(sessionId)
    console.log('🔍 DEBUG - serviceData completo:', serviceData)

    // Todo listo para el ChatWidget
    id_session.value = sessionId
    resource_uri.value = serviceData.urls?.resource_uri
    
    console.log('🔍 DEBUG - resource_uri asignado:', resource_uri.value)
    
    if (!resource_uri.value) {
      throw new Error('No se pudo obtener resource_uri de la respuesta del servicio')
    }
    
    isAuthenticated.value = true
    console.log('✅ Servicio inicializado correctamente. ChatWidget puede iniciar.')
    
  } catch (error) {
    console.error('❌ Error en inicialización:', error)
    errorMessage.value = error.message || 'Error en la inicialización'
  } finally {
    isInitializing.value = false
  }
}

// Función para obtener el token (Paso 1)
const obtenerToken = async () => {
  // Codificar credenciales en Base64 para HTTP Basic Auth
  const credentials = btoa(`${SERVICE_CONFIG.user}:${SERVICE_CONFIG.password}`) // TODO: en archivo .env
  
  const response = await fetch(`${SERVICE_CONFIG.base_url}/api/chat/session/auth`, {
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
  console.log('✅ Sesión creada:', data.id_session)
  return data.id_session
}

// Función para inicializar servicio con preguntas (Paso 2)
const inicializarServicio = async (sessionId) => {
      const response = await fetch(`${SERVICE_CONFIG.base_url}/api/chat/${SERVICE_CONFIG.type}/initiate`, {
    method: 'POST',
    headers: {
      'accept': 'application/json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      id_session: sessionId,
      type: SERVICE_CONFIG.type,
      content: {
        questions: PREGUNTAS_PERSONALIZADAS
      },
      configs: {
        "webhook_url" : "",
        "email"       : ["lucasd@gmail.com","santi@gmail.com"],
        "avatar"      : false,
      }
    })
  })
  
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Error al inicializar servicio: ${response.status} - ${errorText}`)
  }
  
  const data = await response.json()
  console.log('✅ Servicio inicializado:', data)
  return data
}

// Funciones para manejar eventos del ChatWidget
const onMessageSent = (message) => {
  console.log('Mensaje enviado:', message)
}

const onConversationComplete = (progress) => {
  console.log('Conversación completada:', progress)
  
  // Cerrar el ChatWidget y no aceptar más respuestas
  isAuthenticated.value = false
  
  // Resetear el estado para permitir una nueva conversación si es necesario
  id_session.value = ''
  resource_uri.value = ''
  
  // Mostrar mensaje de que la conversación ha terminado
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
  