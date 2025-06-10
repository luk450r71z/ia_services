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
      
      <div v-if="connectionState === 'connecting'" class="connection-status">
        Conectando al servidor...
      </div>
      
      <div v-if="connectionState === 'reconnecting'" class="connection-status">
        Reintentando conexión...
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
        required: true
      },
      websocket_url: {
        type: String,
        required: true
      },
      serviceType: {
        type: String,
        default: 'questionnarie'
      }
    },
    data() {
      return {
        ws: null,
        userInput: '',
        messages: [],
        conversationCompleted: false,
        connectionState: 'disconnected', // 'disconnected', 'connecting', 'connected', 'reconnecting'
        reconnectAttempts: 0,
        maxReconnectAttempts: 3
      }
    },
    computed: {
      canSendMessage() {
        return this.connectionState === 'connected' && !this.conversationCompleted;
      },
      inputPlaceholder() {
        return this.conversationCompleted 
          ? 'La conversación ha finalizado' 
          : 'Escribe tu respuesta...';
      },
      buttonText() {
        if (this.conversationCompleted) return 'Finalizado';
        if (this.connectionState === 'connected') return 'Enviar';
        return 'Conectando...';
      }
    },
    mounted() {
      console.log(`🚀 ChatWidget montado con sessionId: ${this.sessionId}`);
      this.connectWebSocket();
    },
    beforeUnmount() {
      this.disconnectWebSocket();
    },
    methods: {
      connectWebSocket() {
        if (!this.websocket_url) {
          this.addMessage('system', 'Error: URL de WebSocket no proporcionada');
          return;
        }

        this.connectionState = 'connecting';
        console.log(`🔗 Conectando a WebSocket:`, this.websocket_url);
        
        try {
          this.ws = new WebSocket(this.websocket_url);
          
          this.ws.onopen = () => {
            console.log('✅ Conectado al agente');
            this.connectionState = 'connected';
            this.reconnectAttempts = 0;
          };
          
          this.ws.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);
              this.handleWebSocketMessage(data);
            } catch (error) {
              console.error('❌ Error parsing message:', error);
            }
          };
          
          this.ws.onclose = (event) => {
            console.log('🔌 WebSocket desconectado, código:', event.code);
            this.connectionState = 'disconnected';
            
            // Códigos que NO deben reconectar (errores permanentes)
            if ([4001, 4004, 403, 401].includes(event.code)) {
              this.addMessage('system', 'Conexión cerrada por el servidor');
              return;
            }
            
            // Reconexión automática si la conversación no terminó
            if (!this.conversationCompleted && this.reconnectAttempts < this.maxReconnectAttempts) {
              this.attemptReconnect();
            } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
              this.addMessage('system', 'No se pudo restablecer la conexión');
            }
          };
          
          this.ws.onerror = (error) => {
            console.error('❌ Error de WebSocket:', error);
            this.connectionState = 'disconnected';
          };
          
        } catch (error) {
          console.error('❌ Error al conectar WebSocket:', error);
          this.connectionState = 'disconnected';
          this.addMessage('system', `Error al conectar: ${error.message}`);
        }
      },
      
      attemptReconnect() {
        this.reconnectAttempts++;
        this.connectionState = 'reconnecting';
        
        const delay = Math.min(2000 * this.reconnectAttempts, 8000); // Delay progresivo
        console.log(`🔄 Reintentando conexión en ${delay}ms... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => {
          this.connectWebSocket();
        }, delay);
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
        this.connectionState = 'disconnected';
      },
      
      handleSendMessage() {
        if (this.conversationCompleted) {
          this.addMessage('system', 'La conversación ha finalizado. No se pueden enviar más mensajes.');
          this.userInput = '';
          return;
        }
        
        const message = this.userInput.trim();
        if (!message) return;
        
        this.addMessage('user', message);
        
        if (this.connectionState === 'connected' && this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ content: message }));
          this.$emit('message-sent', message);
        } else {
          this.addMessage('system', 'No hay conexión. Reintentando...');
          this.attemptReconnect();
        }
        
        this.userInput = '';
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