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
          @keydown.enter.prevent="handleSendMessage"
          :placeholder="inputPlaceholder"
          :disabled="!canSendMessage"
        ></textarea>
        <button 
          @click="handleSendMessage" 
          :disabled="!canSendMessage || !userInput.trim()"
          class="send-button"
        >
          {{ buttonText }}
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
        default: 'auto'
      }
    },
    data() {
      return {
        ws: null,
        isConnected: false,
        userInput: '',
        messages: [],
        conversationCompleted: false
      }
    },
    computed: {
      apiBaseUrl() {
        if (this.resource_uri) {
          try {
            const url = new URL(this.resource_uri);
            return `${url.protocol}//${url.host}`;
          } catch (error) {
            console.error('❌ Error extrayendo base URL:', error);
            return 'http://127.0.0.1:8000';
          }
        }
        return 'http://127.0.0.1:8000';
      },
      canSendMessage() {
        return this.isConnected && !this.conversationCompleted;
      },
      inputPlaceholder() {
        return this.conversationCompleted 
          ? 'La conversación ha finalizado' 
          : 'Escribe tu respuesta...';
      },
      buttonText() {
        if (this.conversationCompleted) return 'Finalizado';
        return this.isConnected ? 'Enviar' : 'Conectando...';
      }
    },
    async mounted() {
      console.log(`🚀 ChatWidget montado con sessionId: ${this.sessionId}`);
      
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
          
          const serviceType = await this.getServiceType();
          
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
          
          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Error al iniciar servicio: ${response.status} - ${errorText}`);
          }
          
          const data = await response.json();
          console.log('✅ Servicio conversacional iniciado correctamente');
          
          if (data.websocket_endpoint) {
            this.connectWebSocket(data.websocket_endpoint);
            return true;
          } else {
            this.addMessage('system', 'Error: No se pudo obtener el endpoint WebSocket del servicio');
            return false;
          }
          
        } catch (error) {
          console.error('❌ Error iniciando servicio:', error);
          this.addMessage('system', `Error al iniciar servicio conversacional: ${error.message}`);
          return false;
        }
      },
      
      async getServiceType() {
        if (this.serviceType && this.serviceType !== 'auto') {
          return this.serviceType;
        }
        
        try {
          const sessionUrl = `${this.apiBaseUrl}/api/chat/session/${this.sessionId}`;
          const response = await fetch(sessionUrl, {
            method: 'GET',
            headers: { 'accept': 'application/json' }
          });
          
          if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudo obtener información de la sesión`);
          }
          
          const sessionData = await response.json();
          if (!sessionData.type) {
            throw new Error('La sesión no tiene un tipo de servicio definido');
          }
          
          return sessionData.type;
          
        } catch (error) {
          console.error(`❌ Error obteniendo tipo de servicio:`, error);
          throw error;
        }
      },
      
      connectWebSocket(wsUrl) {
        try {
          console.log('🔗 Conectando a WebSocket:', wsUrl);
          
          this.ws = new WebSocket(wsUrl);
          
          this.ws.onopen = () => {
            console.log('✅ Conectado al agente');
            this.isConnected = true;
          };
          
          this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
          };
          
          this.ws.onclose = (event) => {
            console.log('🔌 WebSocket desconectado');
            this.isConnected = false;
            
            if (event.code === 403) {
              this.addMessage('system', 'Error: Acceso denegado al servidor');
            } else if (!event.wasClean && !this.conversationCompleted) {
              setTimeout(() => this.connectWebSocket(wsUrl), 3000);
            }
          };
          
          this.ws.onerror = (error) => {
            console.error('❌ Error de WebSocket:', error);
            this.isConnected = false;
            this.addMessage('system', 'Error de conexión con el servidor');
          };
          
        } catch (error) {
          console.error('❌ Error al conectar WebSocket:', error);
          this.isConnected = false;
          this.addMessage('system', `Error al inicializar: ${error.message}`);
        }
      },
      
      handleWebSocketMessage(data) {
        if (data.type === 'agent_response') {
          const isComplete = data.data?.is_complete;
          this.addMessage('agent', data.content);
          
          if (isComplete) {
            this.conversationCompleted = true;
            console.log('🔒 Conversación completada');
            this.$emit('conversation-complete', data.data.summary);
          }
        } else if (data.type === 'system') {
          this.addMessage('system', data.content);
        } else if (data.type === 'error') {
          console.error('❌ Error del servidor:', data.content);
          this.addMessage('system', `Error: ${data.content}`);
        }
      },
      
      disconnectWebSocket() {
        if (this.ws) {
          this.ws.close();
          this.ws = null;
        }
      },
      
      handleSendMessage() {
        if (this.conversationCompleted) {
          this.addMessage('system', 'La conversación ha finalizado. No se pueden enviar más mensajes.');
          this.userInput = '';
          return;
        }
        
        const message = this.userInput.trim();
        if (message && this.isConnected) {
          this.addMessage('user', message);
          
          this.ws.send(JSON.stringify({
            content: message
          }));
          
          this.userInput = '';
          this.$emit('message-sent', message);
        }
      },
      
      addMessage(role, content) {
        this.messages.push({
          role,
          content,
          timestamp: new Date()
        });
        
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
  }
  
  .message.agent {
    background: #f1f8e9;
    margin-right: auto;
    border-bottom-left-radius: 4px;
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
  
  .connection-status, .completion-status {
    text-align: center;
    padding: 10px;
    border-radius: 4px;
    margin-top: 10px;
    font-weight: bold;
  }
  
  .connection-status {
    background-color: #fff3cd;
    border: 1px solid #ffeaa7;
    color: #856404;
  }
  
  .completion-status {
    background-color: #d1ecf1;
    border: 1px solid #bee5eb;
    color: #0c5460;
  }
  
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