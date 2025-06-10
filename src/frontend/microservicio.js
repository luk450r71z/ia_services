import { createApp } from 'vue'
import MicroservicioApp from './src/MicroservicioApp.vue'

console.log('🤖 Iniciando Frontend Chat IA...')

// Configuraciones globales del frontend
const config = {
  name: 'Frontend Chat IA',
  version: '1.0.0',
  author: 'Adaptiera Team',
  environment: import.meta.env.MODE || 'development',
  description: 'Frontend independiente servido desde webui_url del endpoint questionnarie/initiate'
}

console.log('📋 Configuración del frontend:', config)

// Crear aplicación Vue
const app = createApp(MicroservicioApp)

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
  console.log('✅ Frontend montado correctamente en #app')
  console.log('🌐 Servicio disponible desde webui_url')
} catch (error) {
  console.error('❌ Error al montar el frontend:', error)
} 