<template>
    <div class="chat-container">
      <div id="messages" ref="messagesContainer" class="messages-area">
        <div 
          v-for="(message, index) in messages" 
          :key="index" 
          :class="['message', message.role]"
        >
          <strong v-if="message.role === 'user'">👤 You:</strong>
          <strong v-else-if="message.role === 'agent'">🤖 Agent:</strong>
          <strong v-else-if="message.role === 'system'">⚠️ System:</strong>
          {{ message.content }}
        </div>
      </div>
      
      <!-- Controles dinámicos según answerType -->
      <div v-if="currentAnswerType && currentOptions && currentOptions.length > 0" class="options-container">
        <!-- Single Choice - Botones -->
        <div v-if="currentAnswerType === 'single_choice'" class="single-choice-container">
          <div class="options-title">Select one option:</div>
          <div class="options-buttons">
            <button 
              v-for="option in currentOptions" 
              :key="option"
              @click="selectSingleChoice(option)"
              :class="['option-button', { 'selected': selectedSingleChoice === option }]"
            >
              {{ option }}
            </button>
          </div>
          <button 
            @click="sendSelection"
            :disabled="!hasValidSelection"
            class="send-selection-button"
          >
            Send Selection
          </button>
        </div>
        
        <!-- Multiple Choice - Checkboxes -->
        <div v-else-if="currentAnswerType === 'multiple_choice'" class="multiple-choice-container">
          <div class="options-title">Select one or more options:</div>
          <div class="options-checkboxes">
            <label 
              v-for="option in currentOptions" 
              :key="option"
              class="checkbox-label"
            >
              <input 
                type="checkbox" 
                :value="option"
                v-model="selectedMultipleChoices"
                class="checkbox-input"
              >
              <span class="checkbox-text">{{ option }}</span>
            </label>
          </div>
          <button 
            @click="sendSelection"
            :disabled="!hasValidSelection"
            class="send-selection-button"
          >
            Send Selection ({{ selectionCount }})
          </button>
        </div>
      </div>
      
      <!-- Input de texto normal -->
      <div v-else class="input-container">
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
        Connecting to server...
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
      },
      disabled: {
        type: Boolean,
        default: false
      }
    },
    data() {
      return {
        ws: null,
        userInput: '',
        messages: [],
        conversationCompleted: false,
        connectionState: 'disconnected', // 'disconnected', 'connecting', 'connected'
        currentAnswerType: null,
        currentOptions: [],
        selectedSingleChoice: null,
        selectedMultipleChoices: []
      }
    },
    computed: {
      canSendMessage() {
        return this.connectionState === 'connected' && !this.conversationCompleted && !this.disabled;
      },
      inputPlaceholder() {
        if (this.disabled || this.conversationCompleted) {
          return 'The conversation has ended';
        }
        return 'Type your response...';
      },
      buttonText() {
        if (this.disabled || this.conversationCompleted) return 'Ended';
        if (this.connectionState === 'connected') return 'Send';
        return 'Connecting...';
      },
      hasValidSelection() {
        if (this.currentAnswerType === 'single_choice') {
          return !!this.selectedSingleChoice;
        }
        if (this.currentAnswerType === 'multiple_choice') {
          return this.selectedMultipleChoices.length > 0;
        }
        return false;
      },
      selectionCount() {
        return this.selectedMultipleChoices.length;
      }
    },
    mounted() {
      console.log(`🚀 ChatWidget mounted for chat-ui URL: ${this.websocket_url}`);
      if (this.websocket_url) {
        this.connectWebSocket();
      } else {
        console.error('❌ No WebSocket URL provided');
        this.$emit('connection-state-change', 'error');
      }
    },
    beforeUnmount() {
      this.disconnectWebSocket();
    },
    methods: {
      connectWebSocket() {
        if (!this.websocket_url) {
          this.addMessage('system', 'Error: WebSocket URL not provided');
          this.$emit('connection-state-change', 'error');
          return;
        }

        this.connectionState = 'connecting';
        console.log(`🔗 Connecting to WebSocket from chat-ui:`, this.websocket_url);
        this.$emit('connection-state-change', 'connecting');
        
        try {
          if (this.ws) {
            console.log('🔄 Closing existing connection before creating new one');
            this.ws.close();
          }
          
          this.ws = new WebSocket(this.websocket_url);
          
          this.ws.onopen = () => {
            console.log('✅ Connected to agent from chat-ui');
            this.connectionState = 'connected';
            this.$emit('connection-state-change', 'connected');
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
            console.log('🔌 WebSocket disconnected, code:', event.code);
            this.connectionState = 'disconnected';
            this.$emit('connection-state-change', 'disconnected');
            this.addMessage('system', 'Connection closed');
          };
          
          this.ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            this.connectionState = 'disconnected';
            this.$emit('connection-state-change', 'disconnected');
            this.addMessage('system', 'Connection error');
          };
          
        } catch (error) {
          console.error('❌ Error connecting to WebSocket:', error);
          this.connectionState = 'disconnected';
          this.$emit('connection-state-change', 'error');
          this.addMessage('system', `Connection error: ${error.message}`);
        }
      },
      
      handleWebSocketMessage(data) {
        console.log('📨 ChatWidget received message:', data.type, data);
        
        if (data.type === 'agent_response') {
          const isComplete = data.data?.is_complete;
          const isWelcome = data.data?.is_welcome;
          const isCurrentState = data.data?.is_current_state;
          const answerType = data.data?.answerType;
          const options = data.data?.options;
          
          // Solo agregar mensaje si no es un estado actual (para evitar duplicados)
          if (!isCurrentState) {
            this.addMessage('agent', data.content);
          }
          
          // Actualizar el tipo de respuesta y opciones actuales
          this.currentAnswerType = answerType;
          this.currentOptions = options || [];
          
          // Limpiar selecciones anteriores
          this.selectedSingleChoice = null;
          this.selectedMultipleChoices = [];
          
          if (isComplete) {
            this.conversationCompleted = true;
            console.log('🔒 Conversation completed in chat-ui');
            this.$emit('conversation-complete', data.data.summary);
            
            // Cerrar automáticamente el widget después de 3 segundos
            setTimeout(() => {
              this.$emit('close-widget');
            }, 3000);
          }
        } else if (data.type === 'user_message') {
          this.addMessage('user', data.content);
        } else if (data.type === 'ui_config') {
          console.log('🔧 ChatWidget received ui_config:', data);
          this.$emit('ui-config', data);
        } else if (data.type === 'error') {
          console.error('❌ Server error:', data.content);
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
        if (this.disabled || this.conversationCompleted) {
          this.addMessage('system', 'The conversation has ended. No more messages can be sent.');
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
          this.addMessage('system', 'No connection available');
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
      },
      
      selectSingleChoice(option) {
        this.selectedSingleChoice = option;
      },
      
      sendSelection() {
        let content = '';
        
        if (this.currentAnswerType === 'single_choice' && this.selectedSingleChoice) {
          content = this.selectedSingleChoice;
        } else if (this.currentAnswerType === 'multiple_choice' && this.selectedMultipleChoices.length > 0) {
          content = this.selectedMultipleChoices.join(', ');
        }
        
        if (content) {
          this.addMessage('user', content);
          
          // Enviar al WebSocket
          if (this.connectionState === 'connected' && this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ content }));
            this.$emit('message-sent', content);
          }
          
          // Limpiar estado
          this.selectedSingleChoice = null;
          this.selectedMultipleChoices = [];
          this.currentAnswerType = null;
          this.currentOptions = [];
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
    height: calc(100vh - 180px);
    overflow-y: auto;
    padding: 20px;
    background: #f8f9fa;
    border-radius: 12px;
    margin-bottom: 20px;
  }
  
  .message {
    margin-bottom: 15px;
    padding: 12px 16px;
    border-radius: 12px;
    max-width: 85%;
    word-wrap: break-word;
  }
  
  .message.user {
    background: #007bff;
    color: white;
    margin-left: auto;
  }
  
  .message.agent {
    background: #e9ecef;
    color: #212529;
    margin-right: auto;
  }
  
  .message.system {
    background: #dc3545;
    color: white;
    margin: 10px auto;
    text-align: center;
    max-width: 95%;
  }
  
  .input-container {
    display: flex;
    gap: 10px;
    position: relative;
  }
  
  textarea {
    flex: 1;
    padding: 12px;
    border: 2px solid #dee2e6;
    border-radius: 12px;
    resize: none;
    height: 60px;
    font-family: inherit;
    font-size: 16px;
    transition: border-color 0.3s ease;
  }
  
  textarea:focus {
    outline: none;
    border-color: #007bff;
  }
  
  textarea:disabled {
    background: #e9ecef;
    cursor: not-allowed;
  }
  
  .send-button {
    padding: 0 25px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.3s ease;
  }
  
  .send-button:hover:not(:disabled) {
    background: #0056b3;
    transform: translateY(-2px);
  }
  
  .send-button:disabled {
    background: #6c757d;
    cursor: not-allowed;
  }
  
  .connection-status {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 10px 20px;
    border-radius: 20px;
    font-size: 14px;
    z-index: 1000;
  }
  
  .options-container {
    margin-bottom: 20px;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 12px;
    border: 1px solid #dee2e6;
  }
  
  .single-choice-container,
  .multiple-choice-container {
    margin-bottom: 10px;
  }
  
  .options-title {
    font-weight: 600;
    margin-bottom: 10px;
    color: #495057;
    font-size: 14px;
  }
  
  .options-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 15px;
  }
  
  .options-checkboxes {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 15px;
  }
  
  .option-button {
    padding: 10px 16px;
    border: 2px solid #dee2e6;
    border-radius: 8px;
    background: white;
    color: #495057;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s ease;
    min-width: 80px;
  }
  
  .option-button:hover {
    border-color: #007bff;
    background: #f8f9fa;
  }
  
  .option-button.selected {
    background: #007bff;
    color: white;
    border-color: #007bff;
  }
  
  .checkbox-label {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    background: white;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  
  .checkbox-label:hover {
    background: #f8f9fa;
    border-color: #007bff;
  }
  
  .checkbox-input {
    margin-right: 8px;
    transform: scale(1.2);
  }
  
  .checkbox-text {
    font-size: 14px;
    color: #495057;
  }
  
  .send-selection-button {
    padding: 10px 20px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 600;
    font-size: 14px;
    transition: all 0.2s ease;
  }
  
  .send-selection-button:hover:not(:disabled) {
    background: #0056b3;
    transform: translateY(-1px);
  }
  
  .send-selection-button:disabled {
    background: #6c757d;
    cursor: not-allowed;
    transform: none;
  }
  </style> 