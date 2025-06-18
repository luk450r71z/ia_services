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
        Connecting to server...
      </div>
      
      <div v-if="connectionState === 'reconnecting'" class="connection-status">
        Retrying connection...
      </div>
      
      <div v-if="conversationCompleted" class="completion-status">
        ✅ Conversation completed. The chat will close automatically.
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
        connectionState: 'disconnected', // 'disconnected', 'connecting', 'connected', 'reconnecting'
        reconnectAttempts: 0,
        maxReconnectAttempts: 3
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
      }
    },
    mounted() {
      console.log(`🚀 ChatWidget mounted for chat-ui URL: ${this.websocket_url}`);
      this.connectWebSocket();
    },
    beforeUnmount() {
      this.disconnectWebSocket();
    },
    methods: {
      connectWebSocket() {
        if (!this.websocket_url) {
          this.addMessage('system', 'Error: WebSocket URL not provided');
          return;
        }

        this.connectionState = 'connecting';
        console.log(`🔗 Connecting to WebSocket from chat-ui:`, this.websocket_url);
        
        try {
          this.ws = new WebSocket(this.websocket_url);
          
          this.ws.onopen = () => {
            console.log('✅ Connected to agent from chat-ui');
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
            console.log('🔌 WebSocket disconnected, code:', event.code);
            this.connectionState = 'disconnected';
            
            // Codes that should NOT reconnect (permanent errors)
            if ([4001, 4004, 403, 401].includes(event.code)) {
              this.addMessage('system', 'Connection closed by server');
              return;
            }
            
            // Automatic reconnection if conversation hasn't ended
            if (!this.conversationCompleted && this.reconnectAttempts < this.maxReconnectAttempts) {
              this.attemptReconnect();
            } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
              this.addMessage('system', 'Could not restore connection');
            }
          };
          
          this.ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            this.connectionState = 'disconnected';
          };
          
        } catch (error) {
          console.error('❌ Error connecting to WebSocket:', error);
          this.connectionState = 'disconnected';
          this.addMessage('system', `Connection error: ${error.message}`);
        }
      },
      
      attemptReconnect() {
        this.reconnectAttempts++;
        this.connectionState = 'reconnecting';
        
        const delay = Math.min(2000 * this.reconnectAttempts, 8000); // Progressive delay
        console.log(`🔄 Retrying connection in ${delay}ms... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => {
          this.connectWebSocket();
        }, delay);
      },
      
      handleWebSocketMessage(data) {
        console.log('📨 ChatWidget received message:', data.type, data);
        
        if (data.type === 'agent_response') {
          const isComplete = data.data?.is_complete;
          const isWelcome = data.data?.is_welcome;
          
          this.addMessage('agent', data.content);
          
          if (isComplete) {
            this.conversationCompleted = true;
            console.log('🔒 Conversation completed in chat-ui');
            this.$emit('conversation-complete', data.data.summary);
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
          this.addMessage('system', 'No connection. Retrying...');
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
  
  .completion-status {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(40, 167, 69, 0.9);
    color: white;
    padding: 10px 20px;
    border-radius: 20px;
    font-size: 14px;
    z-index: 1000;
  }
  </style> 