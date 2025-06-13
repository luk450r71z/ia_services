import { createApp } from 'vue'
import ChatUIApp from './pages/ChatUIApp.vue'

console.log('🤖 Starting Chat UI...')

// Global chat-ui configurations
const config = {
  name: 'Chat UI',
  version: '1.0.0',
  author: 'Adaptiera Team',
  environment: import.meta.env.MODE || 'development',
  description: 'Independent Chat UI served from webui_url of questionnaire/initiate endpoint'
}

console.log('📋 Chat UI configuration:', config)

// Create Vue application
const app = createApp(ChatUIApp)

// Global properties
app.config.globalProperties.$config = config

// Development configuration
if (config.environment === 'development') {
  app.config.devtools = true
  console.log('🔧 Development mode activated')
}

// Global error handling
app.config.errorHandler = (error, vm, info) => {
  console.error('❌ Vue global error:', error)
  console.error('📍 Error information:', info)
  console.error('🔧 Component instance:', vm)
  
  // In production, you could send errors to a monitoring service
  if (config.environment === 'production') {
    // Here you could integrate with services like Sentry, LogRocket, etc.
    console.log('📊 Error reported to monitoring system')
  }
}

// Application mounting
try {
  app.mount('#app')
  console.log('✅ Chat UI successfully mounted in #app')
  console.log('🌐 Service available from webui_url')
} catch (error) {
  console.error('❌ Error mounting chat UI:', error)
} 