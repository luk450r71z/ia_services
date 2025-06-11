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
      websocket_url: {
        type: String,
        required: true
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
      console.log(`🚀 ChatWidget montado`);
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
        console.log(`🔗 Conectando a WebSocket desde chat-ui:`, this.websocket_url);
        
        try {
          this.ws = new WebSocket(this.websocket_url);
          
          this.ws.onopen = () => {
            console.log('✅ Conectado al agente desde chat-ui');
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
            console.log('🔒 Conversación completada en chat-ui');
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
    max-width: 100%;
    margin: 0;
    padding: 25px;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #fff;
    border-radius: 0;
  }
  
  .messages-area {
    height: 450px;
    overflow-y: auto;
    border: 2px solid #e0e7ff;
    border-radius: 15px;
    padding: 20px;
    margin-bottom: 20px;
    background: linear-gradient(135deg, #fafbff 0%, #f0f4ff 100%);
  }
  
  .message {
    margin: 15px 0;
    padding: 15px 18px;
    border-radius: 18px;
    max-width: 85%;
    word-wrap: break-word;
    color: #2d3748;
    font-size: 15px;
    line-height: 1.5;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    animation: fadeInUp 0.3s ease-out;
  }
  
  .message.user {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    margin-left: auto;
    text-align: right;
    border-bottom-right-radius: 6px;
  }
  
  .message.agent {
    background: linear-gradient(135deg, #f1f8e9 0%, #e8f5e8 100%);
    margin-right: auto;
    border-bottom-left-radius: 6px;
    border-left: 4px solid #4caf50;
  }
  
  .message.system {
    background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
    margin: 10px auto;
    text-align: center;
    border-radius: 12px;
    color: #856404;
    font-style: italic;
    max-width: 95%;
    border: 1px solid #ffc107;
  }
  
  .input-container {
    display: flex;
    gap: 15px;
    align-items: flex-end;
    padding: 15px;
    background: rgba(0, 0, 0, 0.02);
    border-radius: 15px;
  }
  
  #user-input {
    flex: 1;
    min-height: 60px;
    padding: 15px 18px;
    border: 2px solid #e0e7ff;
    border-radius: 12px;
    resize: vertical;
    font-family: inherit;
    font-size: 15px;
    background: white;
    transition: all 0.3s ease;
  }
  
  #user-input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }
  
  .send-button {
    padding: 15px 25px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    font-weight: 600;
    font-size: 15px;
    transition: all 0.3s ease;
    min-width: 100px;
  }
  
  .send-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
  }
  
  .send-button:disabled {
    background: #cbd5e0;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
  
  .connection-status, .completion-status {
    text-align: center;
    padding: 12px 20px;
    border-radius: 10px;
    margin-top: 15px;
    font-weight: 600;
    font-size: 14px;
  }
  
  .connection-status {
    background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
    border: 1px solid #ffc107;
    color: #856404;
  }
  
  .completion-status {
    background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
    border: 1px solid #17a2b8;
    color: #0c5460;
  }
  
  .messages-area::-webkit-scrollbar {
    width: 8px;
  }
  
  .messages-area::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
    border-radius: 4px;
  }
  
  .messages-area::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 4px;
  }
  
  .messages-area::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
  }
  
  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  /* Responsive design */
  @media (max-width: 768px) {
    .chat-container {
      padding: 15px;
    }
    
    .messages-area {
      height: 350px;
      padding: 15px;
    }
    
    .message {
      max-width: 95%;
      padding: 12px 15px;
      font-size: 14px;
    }
    
    .input-container {
      padding: 10px;
      gap: 10px;
    }
    
    #user-input {
      min-height: 50px;
      padding: 12px 15px;
      font-size: 14px;
    }
    
    .send-button {
      padding: 12px 20px;
      min-width: 80px;
      font-size: 14px;
    }
  }
  </style> 