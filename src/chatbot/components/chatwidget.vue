<template>
    <div class="chat-container">
      <div id="messages" ref="messagesContainer" class="messages-area">
        <div 
          v-for="(message, index) in messages" 
          :key="index" 
          :class="['message', message.role]"
        >
          <strong v-if="message.role === 'user'">👤 Tú:</strong>
          <strong v-else-if="message.role === 'agent'">🤖 Agente:</strong>
          <strong v-else-if="message.role === 'system'">⚠️ Sistema:</strong>
          {{ message.content }}
        </div>
      </div>
      
      <div class="input-container">
        <textarea 
          id="user-input" 
          v-model="userInput"
          @keydown.enter.prevent="handleEnterKey"
          :placeholder="conversationCompleted ? 'La conversación ha finalizado' : 'Escribe tu respuesta...'"
          :disabled="!isConnected || conversationCompleted"
        ></textarea>
        <button 
          @click="handleButtonClick" 
          :disabled="!isConnected || !userInput.trim() || conversationCompleted"
          class="send-button"
        >
          {{ conversationCompleted ? 'Finalizado' : (isConnected ? 'Enviar' : 'Conectando...') }}
        </button>
      </div>
      
      <div v-if="!isConnected" class="connection-status">
        Conectando al servidor...
      </div>
      
      <div v-if="conversationCompleted" class="completion-status">
        ✅ Conversación completada. El chat se cerrará automáticamente.
      </div>
    </div>
  </template>
  
  <script>
  export default {
    name: 'ChatWidget',
    props: {
      sessionId: {
        type: String,
        default: 'default-session'
      },
      resource_uri: {
        type: String,
        required: true
      },
      serviceType: {
        type: String,
        default: 'auto' // 'auto' para obtener dinámicamente, o especificar tipo directo
      },

    },
    data() {
      return {
        ws: null,
        isConnected: false,
        userInput: '',
        messages: [],
        conversationCompleted: false // Flag para controlar si la conversación terminó
      }
    },
    computed: {
      apiBaseUrl() {
        // Extraer la base URL del resource_uri
        if (this.resource_uri) {
          try {
            const url = new URL(this.resource_uri);
            return `${url.protocol}//${url.host}`;
          } catch (error) {
            console.error('❌ Error extrayendo base URL:', error);
            return 'http://127.0.0.1:8000'; // fallback
          }
        }
        return 'http://127.0.0.1:8000'; // fallback por defecto
      }
    },
    async mounted() {
      console.log(`🚀 ChatWidget montado con sessionId: ${this.sessionId}`);
      console.log('📝 Sesión ya debería estar inicializada por test.vue');
      
      const started = await this.startConversationalService();
      if (!started) {
        this.addMessage('system', 'No se pudo iniciar el servicio conversacional. Por favor, recarga la página.');
      }
    },
    beforeUnmount() {
      this.disconnectWebSocket();
    },
    methods: {
      async startConversationalService() {
        try {
          console.log(`🚀 Iniciando servicio conversacional para sesión: ${this.sessionId}`);
          
          // Usar el tipo de servicio proporcionado directamente o intentar obtenerlo dinámicamente
          let serviceType;
          
          if (!this.serviceType || this.serviceType === 'auto') {
            console.log('⚠️ No se proporcionó service-type, intentando obtenerlo dinámicamente...');
            try {
              serviceType = await this.getServiceTypeFromSession();
            } catch (error) {
              console.error('❌ No se pudo obtener el tipo de servicio:', error.message);
              this.addMessage('system', `Error: No se pudo determinar el tipo de servicio. ${error.message}`);
              return false;
            }
          } else {
            serviceType = this.serviceType;
            console.log(`✅ Usando service-type proporcionado: ${serviceType}`);
          }
          
          console.log(`ℹ️ Tipo de servicio: ${serviceType}`);
          console.log(`ℹ️ Resource URI: ${this.resource_uri}`);
          
          

          
          const response = await fetch(this.resource_uri, {
            method: 'POST',
            headers: {
              'accept': 'application/json',
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              id_session: this.sessionId,
              type: serviceType
            })
          });
          
          console.log(`📨 Response status: ${response.status}`);
          
          if (!response.ok) {
            const errorText = await response.text();
            console.log(`❌ Error response: ${errorText}`);
            throw new Error(`Error al iniciar servicio: ${response.status} - ${errorText}`);
          }
          
          const data = await response.json();
          console.log('✅ Servicio conversacional iniciado correctamente:', data);
          
          // Debug: verificar qué contiene la respuesta
          console.log('🔍 Debug - websocket_endpoint:', data.websocket_endpoint);
          console.log('🔍 Debug - welcome_message:', data.welcome_message);
          
          // Obtener el endpoint WebSocket directamente de la respuesta
          if (data.websocket_endpoint) {
            console.log(`🔗 WebSocket URL obtenida: ${data.websocket_endpoint}`);
            
            // Agregar mensaje de bienvenida si está disponible
            if (data.welcome_message) {
              this.addMessage('agent', data.welcome_message);
              console.log('✅ Mensaje de bienvenida agregado');
            }
            
            this.connectWebSocket(data.websocket_endpoint);
          } else {
            console.error('❌ No se encontró websocket_endpoint en la respuesta del servicio');
            console.log('📝 Respuesta completa:', JSON.stringify(data, null, 2));
            this.addMessage('system', 'Error: No se pudo obtener el endpoint WebSocket del servicio');
          }
          
          return true;
        } catch (error) {
          console.error('❌ Error iniciando servicio:', error);
          this.addMessage('system', `Error al iniciar servicio conversacional: ${error.message}`);
          return false;
        }
      },
      
      async getServiceTypeFromSession() {
        try {
          // Usar la URL base proporcionada como prop
          const sessionUrl = `${this.apiBaseUrl}/api/chat/session/${this.sessionId}`;
          
          console.log(`🔍 Consultando tipo de servicio desde: ${sessionUrl}`);
          
          const response = await fetch(sessionUrl, {
            method: 'GET',
            headers: {
              'accept': 'application/json'
            }
          });
          
          if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudo obtener información de la sesión`);
          }
          
          const sessionData = await response.json();
          const type = sessionData.type;
          
          if (!type) {
            throw new Error('La sesión no tiene un tipo de servicio definido');
          }
          
          console.log(`✅ Tipo de servicio obtenido de la sesión: ${type}`);
          return type;
          
        } catch (error) {
          console.error(`❌ Error obteniendo tipo de servicio:`, error);
          throw error;
        }
      },
      
      connectWebSocket(wsUrl) {
        try {
          console.log('🔗 Conectando a WebSocket:', wsUrl);
          
          // Conexión directa al WebSocket
          this.ws = new WebSocket(wsUrl);
          
          this.ws.onopen = function() {
            console.log('✅ Conectado al agente RRHH');
            this.isConnected = true;
          }.bind(this);
          
          this.ws.onmessage = function(event) {
            console.log('📨 Mensaje recibido:', event.data);
            const data = JSON.parse(event.data);
            
            // Manejar diferentes tipos de mensajes
            if (data.type === 'agent_response') {
                const isComplete = data.data && data.data.is_complete;
                console.log('🔍 Verificando is_complete:', isComplete, 'data.data:', data.data, 'Estado actual conversationCompleted:', this.conversationCompleted);
                
                this.addMessage('agent', data.content);
                
                if (isComplete) {
                    // Marcar la conversación como completada INMEDIATAMENTE
                    this.conversationCompleted = true;
                    console.log('🔒 Conversación marcada como completada. Mensajes bloqueados. Estado:', this.conversationCompleted);
                    
                    // Emitir evento para que el componente padre maneje el cierre
                    this.$emit('conversation-complete', data.data.summary);
                }
            } else if (data.type === 'system') {
                console.log('🔧 Mensaje del sistema:', data.content);
                this.addMessage('system', data.content);
            } else if (data.type === 'typing_indicator') {
                console.log('⏱️ Agente escribiendo:', data.is_typing);
            } else if (data.type === 'error') {
                console.error('❌ Error del servidor:', data.content);
                this.addMessage('system', `Error: ${data.content}`);
            }
          }.bind(this);
          
          this.ws.onclose = function(event) {
            console.log('🔌 WebSocket desconectado:', event.code, event.reason);
            this.isConnected = false;
            
            if (event.code === 403) {
                console.error('❌ Acceso denegado (403) - Verifica el endpoint y configuración');
                this.addMessage('system', 'Error: Acceso denegado al servidor');
            } else if (!event.wasClean) {
              // Intentar reconectar después de 3 segundos si no fue intencional
              setTimeout(() => {
                console.log('🔄 Intentando reconectar...');
                this.connectWebSocket();
              }, 3000);
            }
          }.bind(this);
          
          this.ws.onerror = function(error) {
            console.error('❌ Error de WebSocket:', error);
            this.isConnected = false;
            this.addMessage('system', 'Error de conexión con el servidor');
          }.bind(this);
          
        } catch (error) {
          console.error('❌ Error al conectar WebSocket:', error);
          this.isConnected = false;
          this.addMessage('system', `Error al inicializar: ${error.message}`);
        }
      },
      
      disconnectWebSocket() {
        if (this.ws) {
          this.ws.close();
          this.ws = null;
        }
      },
      
      sendMessage() {
        const message = this.userInput.trim();
        
        console.log('🚀 sendMessage() llamado. Mensaje:', message, 'conversationCompleted:', this.conversationCompleted, 'isConnected:', this.isConnected);
        
        // Verificar si la conversación ya está completada
        if (this.conversationCompleted) {
          console.log('⚠️ Intento de envío bloqueado: conversación completada');
          this.addMessage('system', 'La conversación ha finalizado. No se pueden enviar más mensajes.');
          this.userInput = ''; // Limpiar el input
          return;
        }
        
        if (message && this.isConnected) {
          console.log('✅ Enviando mensaje al servidor:', message);
          
          // Agregar mensaje del usuario
          this.addMessage('user', message);
          
          // Enviar mensaje directo al servidor
          this.ws.send(JSON.stringify({
            content: message
          }));
          
          // Limpiar input
          this.userInput = '';
          
          // Emitir evento de mensaje enviado
          this.$emit('message-sent', message);
        } else {
          console.log('❌ No se puede enviar mensaje. message:', !!message, 'isConnected:', this.isConnected);
        }
      },
      
      handleEnterKey() {
        console.log('⌨️ Enter presionado. conversationCompleted:', this.conversationCompleted);
        if (!this.conversationCompleted) {
          this.sendMessage();
        } else {
          console.log('⚠️ Enter bloqueado: conversación completada');
        }
      },
      
      handleButtonClick() {
        console.log('🖱️ Botón presionado. conversationCompleted:', this.conversationCompleted);
        if (!this.conversationCompleted) {
          this.sendMessage();
        } else {
          console.log('⚠️ Botón bloqueado: conversación completada');
        }
      },
      
      addMessage(role, content) {
        this.messages.push({
          role,
          content,
          timestamp: new Date()
        });
        
        // Scroll automático
        this.$nextTick(() => {
          this.scrollToBottom();
        });
      },
      
      scrollToBottom() {
        const container = this.$refs.messagesContainer;
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      },
      
      clearChat() {
        this.messages = [];
      }
    }
  }
  </script>
  
  <style scoped>
  .chat-container {
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
    font-family: Arial, sans-serif;
    border: 1px solid #ddd;
    border-radius: 10px;
    background-color: #fff;
  }
  
  .messages-area {
    height: 400px;
    overflow-y: auto;
    border: 1px solid #eee;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 15px;
    background-color: #fafafa;
  }
  
  .message {
    margin: 10px 0;
    padding: 12px;
    border-radius: 8px;
    max-width: 80%;
    word-wrap: break-word;
    color: #000;
    font-size: 14px;
    line-height: 1.4;
  }
  
  .message.user {
    background: #e3f2fd;
    margin-left: auto;
    text-align: right;
    border-bottom-right-radius: 4px;
    color: #000;
  }
  
  .message.agent {
    background: #f1f8e9;
    margin-right: auto;
    border-bottom-left-radius: 4px;
    color: #000;
  }
  
  .message.system {
    background: #ffebee;
    margin: 0 auto;
    text-align: center;
    border-radius: 8px;
    color: #c62828;
    font-style: italic;
    max-width: 90%;
  }
  
  .input-container {
    display: flex;
    gap: 10px;
    align-items: flex-end;
  }
  
  #user-input {
    flex: 1;
    min-height: 50px;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 8px;
    resize: vertical;
    font-family: inherit;
    font-size: 14px;
  }
  
  #user-input:focus {
    outline: none;
    border-color: #2196f3;
    box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.2);
  }
  
  .send-button {
    padding: 12px 20px;
    background-color: #2196f3;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: bold;
    transition: background-color 0.2s;
  }
  
  .send-button:hover:not(:disabled) {
    background-color: #1976d2;
  }
  
  .send-button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
  }
  
  .connection-status {
    text-align: center;
    padding: 10px;
    background-color: #fff3cd;
    border: 1px solid #ffeaa7;
    border-radius: 4px;
    margin-top: 10px;
    color: #856404;
  }
  
  .completion-status {
    text-align: center;
    padding: 10px;
    background-color: #d1ecf1;
    border: 1px solid #bee5eb;
    border-radius: 4px;
    margin-top: 10px;
    color: #0c5460;
    font-weight: bold;
  }
  
  /* Scrollbar personalizada */
  .messages-area::-webkit-scrollbar {
    width: 6px;
  }
  
  .messages-area::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 3px;
  }
  
  .messages-area::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 3px;
  }
  
  .messages-area::-webkit-scrollbar-thumb:hover {
    background: #a8a8a8;
  }
  </style> 