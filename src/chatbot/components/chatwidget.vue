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
          @keydown.enter.prevent="sendMessage"
          placeholder="Escribe tu respuesta..."
          :disabled="!isConnected"
        ></textarea>
        <button 
          @click="sendMessage" 
          :disabled="!isConnected || !userInput.trim()"
          class="send-button"
        >
          {{ isConnected ? 'Enviar' : 'Conectando...' }}
        </button>
      </div>
      
      <div v-if="!isConnected" class="connection-status">
        Conectando al servidor...
      </div>
    </div>
  </template>
  
  <script>
  export default {
    name: 'ChatWidget',
    props: {
      jobOffer: {
        type: String,
        default: null
      },
      websocketUrl: {
        type: String,
        default: 'ws://localhost:8000/conversational_agent/ws/default-session'
      },
      authToken: {
        type: String,
        default: null
      },
      sessionId: {
        type: String,
        default: 'default-session'
      },
      questions: {
        type: Array,
        required: true
      }
    },
    data() {
      return {
        ws: null,
        isConnected: false,
        userInput: '',
        messages: [],
        API_BASE_URL: 'http://127.0.0.1:8000'
      }
    },
    async mounted() {
      console.log(`🚀 ChatWidget montado con sessionId: ${this.sessionId}`);
      const initialized = await this.initializeAgent();
      if (initialized) {
        // Pequeño delay para asegurar que el servidor procese la inicialización
        await new Promise(resolve => setTimeout(resolve, 1000));
        this.connectWebSocket();
      } else {
        this.addMessage('system', 'No se pudo inicializar la conversación. Por favor, recarga la página.');
      }
    },
    beforeUnmount() {
      this.disconnectWebSocket();
    },
    methods: {
      async initializeAgent() {
        try {
          console.log(`🔧 Inicializando agente para sesión: ${this.sessionId}`);
          console.log(`📝 Preguntas a enviar:`, this.questions);
          console.log(`🌐 URL del endpoint: ${this.API_BASE_URL}/api/chat/sessions/${this.sessionId}/start`);
          
          const requestBody = { questions: this.questions };
          console.log(`📤 Request body:`, JSON.stringify(requestBody));
          
          const response = await fetch(`${this.API_BASE_URL}/api/chat/sessions/${this.sessionId}/start`, {
            method: 'POST',
            headers: {
              'accept': 'application/json',
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
          });
          
          console.log(`📨 Response status: ${response.status}`);
          
          if (!response.ok) {
            const errorText = await response.text();
            console.log(`❌ Error response: ${errorText}`);
            throw new Error(`Error al inicializar agente: ${response.status} - ${errorText}`);
          }
          
          const data = await response.json();
          console.log('✅ Agente inicializado correctamente:', data);
          return true;
        } catch (error) {
          console.error('❌ Error inicializando agente:', error);
          this.addMessage('system', `Error al inicializar conversación: ${error.message}`);
          return false;
        }
      },
      connectWebSocket() {
        try {
          console.log('🔗 Conectando a WebSocket:', this.websocketUrl);
          
          // Conexión directa al WebSocket
          this.ws = new WebSocket(this.websocketUrl);
          
          this.ws.onopen = function() {
            console.log('✅ Conectado al agente RRHH');
            this.isConnected = true;
          }.bind(this);
          
          this.ws.onmessage = function(event) {
            console.log('📨 Mensaje recibido:', event.data);
            const data = JSON.parse(event.data);
            
            // Manejar diferentes tipos de mensajes
            if (data.type === 'agent_response') {
                this.addMessage('agent', data.content);
                
                if (data.is_complete) {
                    this.$emit('conversation-complete', data.summary);
                }
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
        
        if (message && this.isConnected) {
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