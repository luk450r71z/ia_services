import { createApp } from 'vue'
import ChatUIApp from './pages/ChatUIApp.vue'

console.log('🤖 Iniciando Chat UI...')

// Configuraciones globales del chat-ui
const config = {
  name: 'Chat UI',
  version: '1.0.0',
  author: 'Adaptiera Team',
  environment: import.meta.env.MODE || 'development',
  description: 'Chat UI independiente servido desde webui_url del endpoint questionnarie/initiate'
}

console.log('📋 Configuración del chat-ui:', config)

// Crear aplicación Vue
const app = createApp(ChatUIApp)

// Propiedades globales
app.config.globalProperties.$config = config

// Configuración de desarrollo
if (config.environment === 'development') {
  app.config.devtools = true
  console.log('🔧 Modo desarrollo activado')
}

// Manejo de errores global
app.config.errorHandler = (error, vm, info) => {
  console.error('❌ Error global de Vue:', error)
  console.error('📍 Información del error:', info)
  console.error('🔧 Instancia del componente:', vm)
  
  // En producción, podrías enviar errores a un servicio de monitoreo
  if (config.environment === 'production') {
    // Aquí podrías integrar con servicios como Sentry, LogRocket, etc.
    console.log('📊 Error reportado al sistema de monitoreo')
  }
}

// Montaje de la aplicación
try {
  app.mount('#app')
  console.log('✅ Chat UI montado correctamente en #app')
  console.log('🌐 Servicio disponible desde webui_url')
} catch (error) {
  console.error('❌ Error al montar el chat UI:', error)
} 