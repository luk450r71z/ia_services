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
            
            <!-- Opción "Comment" con campo de texto -->
            <label class="checkbox-label">
              <input 
                type="checkbox" 
                value="comment"
                v-model="selectedMultipleChoices"
                class="checkbox-input"
              >
              <span class="checkbox-text">Comment:</span>
            </label>
            
            <!-- Campo de texto para "Comment" -->
            <div v-if="selectedMultipleChoices.includes('comment')" class="comment-input-container">
              <textarea 
                v-model="commentText"
                placeholder="Please specify..."
                class="comment-textarea"
                rows="2"
              ></textarea>
            </div>
          </div>
          <button 
            @click="sendSelection"
            :disabled="!hasValidSelection"
            class="send-selection-button"
          >
            Send Selection ({{ selectedMultipleChoices.length }})
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
        connectionState: 'disconnected', // 'disconnected', 'connecting', 'connected'
        currentAnswerType: null,
        currentOptions: [],
        selectedSingleChoice: null,
        selectedMultipleChoices: [],
        commentText: '',
        // Métricas de comportamiento del usuario
        userMetrics: {
          mouseOutsideCount: 0,
          mouseInsideCount: 0,
          appHiddenCount: 0,
          appVisibleCount: 0,
          sessionStartTime: Date.now()
        }
      }
    },
    computed: {
      canSendMessage() {
        return this.connectionState === 'connected' && !this.disabled;
      },
      inputPlaceholder() {
        if (this.disabled) {
          return 'The conversation has ended';
        }
        return 'Type your response...';
      },
      buttonText() {
        if (this.disabled) return 'Ended';
        if (this.connectionState === 'connected') return 'Send';
        return 'Connecting...';
      },
      hasValidSelection() {
        if (this.currentAnswerType === 'single_choice') {
          return !!this.selectedSingleChoice;
        }
        if (this.currentAnswerType === 'multiple_choice') {
          // Verificar que haya al menos una selección válida
          const hasValidChoices = this.selectedMultipleChoices.some(choice => {
            if (choice === 'comment' && this.commentText.trim().length > 0) {
              return true;
            }
            return true;
          });
          return hasValidChoices;
        }
        return false;
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
      
      // Configurar listener global para detectar pérdida de foco en todo el componente
      this.setupFocusDetection();
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
            this.addMessage('system', 'This chat session has ended.');
          };
          
          this.ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            this.connectionState = 'disconnected';
            this.$emit('connection-state-change', 'disconnected');
          };
          
        } catch (error) {
          this.connectionState = 'disconnected';
          this.$emit('connection-state-change', 'error');
          this.addMessage('system', 'Connection error');
        }
      },
      
      handleWebSocketMessage(data) {
        console.log('📨 ChatWidget received message:', data.type, data);
        
        if (data.type === 'agent_response') {
          const isComplete = data.data?.is_complete;
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
          this.commentText = '';
          
          if (isComplete) {
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
        if (this.disabled) {
          this.addMessage('system', 'The conversation has ended. No more messages can be sent.');
          this.userInput = '';
          return;
        }
        
        const message = this.userInput.trim();
        if (!message) return;
        
        this.addMessage('user', message);
        
        if (this.connectionState === 'connected' && this.ws?.readyState === WebSocket.OPEN) {
          const messageWithMetrics = this.createMessageWithMetrics(message);
          
          this.ws.send(JSON.stringify(messageWithMetrics));
          this.$emit('message-sent', message);
          
          console.log('📊 Métricas enviadas:', messageWithMetrics.metrics);
        } else {
          this.addMessage('system', 'No connection available');
        }
        
        this.userInput = '';
      },
      
      addMessage(role, content) {
        this.messages.push({
          role,
          content
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
          // Procesar las opciones seleccionadas, incluyendo "comment"
          const selections = this.selectedMultipleChoices.map(choice => {
            if (choice === 'comment' && this.commentText.trim()) {
              return this.commentText.trim();
            }
            return choice;
          }).filter(choice => choice !== 'comment' || this.commentText.trim());
          
          content = selections.join(', ');
        }
        
        if (content) {
          this.addMessage('user', content);
          
          // Enviar al WebSocket
          if (this.connectionState === 'connected' && this.ws?.readyState === WebSocket.OPEN) {
            const messageWithMetrics = this.createMessageWithMetrics(content);
            
            this.ws.send(JSON.stringify(messageWithMetrics));
            this.$emit('message-sent', content);
            
            console.log('📊 Métricas enviadas:', messageWithMetrics.metrics);
          }
          
          // Limpiar estado
          this.selectedSingleChoice = null;
          this.selectedMultipleChoices = [];
          this.commentText = '';
          this.currentAnswerType = null;
          this.currentOptions = [];
        }
      },

      // Helper para generar métricas del usuario
      generateUserMetrics() {
        const sessionDuration = Date.now() - this.userMetrics.sessionStartTime;
        return {
          mouseOutsideCount: this.userMetrics.mouseOutsideCount,
          mouseInsideCount: this.userMetrics.mouseInsideCount,
          appHiddenCount: this.userMetrics.appHiddenCount,
          appVisibleCount: this.userMetrics.appVisibleCount,
          sessionDurationMs: sessionDuration,
          sessionDurationSeconds: Math.round(sessionDuration / 1000)
        };
      },
      
      // Helper para crear mensaje con métricas
      createMessageWithMetrics(content) {
        return {
          content,
          metrics: this.generateUserMetrics()
        };
      },

      setupFocusDetection() {
        // Detectar la posición del mouse en tiempo real
        document.addEventListener('mousemove', (event) => {
          const chatContainer = this.$el;
          if (chatContainer && !chatContainer.contains(event.target)) {
            console.log('🔗 ChatWidget mouse outside:');
            this.userMetrics.mouseOutsideCount++;
            this.$emit('mouse-outside', {
              x: event.clientX,
              y: event.clientY,
              target: event.target.tagName
            });
          } else if (chatContainer && chatContainer.contains(event.target)) {
            console.log('🔗 ChatWidget mouse inside:');
            this.userMetrics.mouseInsideCount++;
            this.$emit('mouse-inside', {
              x: event.clientX,
              y: event.clientY,
              target: event.target.tagName
            });
          }
        });
        
        // Detectar cambios de pestaña y minimización
        document.addEventListener('visibilitychange', () => {
          if (document.hidden) {
            console.log('🔒 ChatWidget app hidden');
            this.userMetrics.appHiddenCount++;
            this.$emit('app-hidden');
          } else {
            console.log('🔗 ChatWidget app visible');
            this.userMetrics.appVisibleCount++;
            this.$emit('app-visible');
          }
        });
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
    width: fit-content;
    word-wrap: break-word;
  }
  
  .message.user {
    background: #718096;
    color: white;
    margin-left: auto;
    text-align: right;
    min-width: 60px;
  }
  
  .message.agent {
    background: #e2e8f0;
    color: #2d3748;
    margin-right: auto;
    text-align: left;
    min-width: 60px;
  }
  
  .message.system {
    background: #4a5568;
    color: white;
    margin: 10px auto;
    text-align: center;
    min-width: 200px;
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
    border: 2px solid #e2e8f0;
    border-radius: 12px;
    resize: none;
    height: 60px;
    font-family: inherit;
    font-size: 16px;
    transition: border-color 0.3s ease;
  }
  
  textarea:focus {
    outline: none;
    border-color: #4a5568;
  }
  
  textarea:disabled {
    background: #f7fafc;
    cursor: not-allowed;
  }
  
  .send-button {
    padding: 0 25px;
    background: #4a5568;
    color: white;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.3s ease;
  }
  
  .send-button:hover:not(:disabled) {
    background: #2d3748;
    transform: translateY(-2px);
  }
  
  .send-button:disabled {
    background: #a0aec0;
    cursor: not-allowed;
  }
  
  .connection-status {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(45, 55, 72, 0.9);
    color: white;
    padding: 10px 20px;
    border-radius: 20px;
    font-size: 14px;
    z-index: 1000;
  }
  
  .options-container {
    margin-bottom: 20px;
    padding: 15px;
    background: #f7fafc;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
  }
  
  .single-choice-container,
  .multiple-choice-container {
    margin-bottom: 10px;
  }
  
  .options-title {
    font-weight: 600;
    margin-bottom: 10px;
    color: #4a5568;
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
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    background: white;
    color: #4a5568;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s ease;
    min-width: 80px;
  }
  
  .option-button:hover {
    border-color: #4a5568;
    background: #f7fafc;
  }
  
  .option-button.selected {
    background: #4a5568;
    color: white;
    border-color: #4a5568;
  }
  
  .checkbox-label {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    background: white;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  
  .checkbox-label:hover {
    background: #f7fafc;
    border-color: #4a5568;
  }
  
  .checkbox-input {
    margin-right: 8px;
    transform: scale(1.2);
  }
  
  .checkbox-text {
    font-size: 14px;
    color: #4a5568;
  }
  
  .send-selection-button {
    padding: 10px 20px;
    background: #4a5568;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 600;
    font-size: 14px;
    transition: all 0.2s ease;
  }
  
  .send-selection-button:hover:not(:disabled) {
    background: #2d3748;
    transform: translateY(-1px);
  }
  
  .send-selection-button:disabled {
    background: #a0aec0;
    cursor: not-allowed;
    transform: none;
  }
  
  .comment-input-container {
    margin-top: 10px;
    padding: 10px;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    background: #f8f9fa;
  }
  
  .comment-textarea {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    resize: none;
    font-family: inherit;
    font-size: 14px;
    transition: border-color 0.2s ease;
  }
  
  .comment-textarea:focus {
    outline: none;
    border-color: #4a5568;
  }
  </style> 