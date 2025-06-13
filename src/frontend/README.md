# 🤖 AI Chat Frontend

**An independent AI Chat frontend that does NOT handle authentication**. Authentication is performed beforehand and the chat UI only connects directly to the WebSocket to start the conversation immediately.

## 🎯 Purpose

The chat UI is designed to:
- **Direct connection** to WebSocket without authentication
- **Immediate start** of conversation
- **Quick integration** from `webui_url` of endpoints
- **Automatic reconnection** in case of disconnection

## 📁 Project Structure

```
frontend/
├── index.html                    # Main chat UI page
├── chat-ui.js                   # Application entry point
├── package.json                 # Project configuration
├── vite.config.js              # Vite configuration
├── public/                     # Static files
├── src/                        # Source code
│   ├── components/            # Vue components
│   │   ├── ChatWidget.vue    # Main chat component
│   │   └── Avatar.vue        # Avatar component
│   └── pages/                 # Additional pages (future)
└── dist/                      # Build output
```

## 🚀 Installation and Configuration

### Prerequisites

- Node.js 16+
- npm or yarn
- Modern web browser

### Installation

```bash
# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build
```

### WebSocket Configuration

The frontend supports multiple ways to configure the WebSocket URL:

**Option 1: Session ID (RECOMMENDED)**
```javascript
// Access via URL: http://localhost:8080/abc123
// The frontend automatically builds: ws://localhost:8000/api/chat/questionnaire/start/abc123
```

**Option 2: Complete WebSocket URL**
```javascript
// Access via URL: http://localhost:8080?ws=ws://localhost:8000/api/chat/questionnaire/start/abc123
```

**Option 3: JavaScript Global Variable**
```javascript
window.CHAT_WS_URL = 'ws://localhost:8000/api/chat/questionnaire/start/abc123'
```

**Option 4: URL Hash**
```javascript
// Access via URL: http://localhost:8080#ws://localhost:8000/api/chat/questionnaire/start/abc123
```

### Development

The chat UI will be available at `http://localhost:8080`

### Production

Build the project:
```bash
npm run build
```

The compiled files will be in `dist/` ready to be served from `webui_url`.

### Serve in Production

```bash
# Using Python
python -m http.server 8080 --directory dist

# Using Node
npx serve dist
```

## 🔧 Advanced Configuration

### Environment Variables

```env
VITE_WS_URL=ws://localhost:8000/api/chat/questionnaire/start
VITE_API_URL=http://localhost:8000/api
```

### Customization

The chat UI can be customized through:

1. CSS variables in `index.html`
2. Component props in `ChatWidget.vue`
3. WebSocket messages for dynamic configuration

### Style Customization

Main styles are in:
- `index.html` - Preloader and base page styles
- `ChatWidget.vue` - Chat component styles
- `Avatar.vue` - Avatar component styles

### Network Configuration

The chat UI follows this flow:

1. **Initialization**: Loads configuration from URL/parameters
2. **WebSocket Acquisition**: Gets WebSocket URL from parameters/variables
3. **Direct Connection**: Connects to WebSocket without authentication
4. **First Message**: Automatically receives first message from agent
5. **Active Chat**: User interacts with AI agent
6. **Completion**: Conversation completes automatically

### Technical Details

- **WebSocket** - Direct real-time communication (no authentication)
- **NO REST APIs** - No HTTP calls for authentication
- **Direct Connection** - Immediately connects to provided WebSocket

### Application States

The chat UI has these states:
- `disconnected`: Initial state
- `connecting`: Establishing connection
- `connected`: Active chat
- `error`: Connection error (with retry)
- `reconnecting`: Attempting to reconnect
- `completed`: Conversation ended

### Event Handling

```javascript
// Example: Handle conversation completion
chatWidget.on('conversation-complete', (summary) => {
  // Calculate statistics, show summary
})

// Example: Handle UI configuration
chatWidget.on('ui-config', (config) => {
  // Update UI based on configuration
})
```

### Authentication

The chat UI uses HTTP basic authentication:
```javascript
// Example: Basic auth header
const auth = btoa('username:password')
const headers = { 'Authorization': `Basic ${auth}` }
```

### Error Handling

The chat UI includes:
- Automatic reconnection with limits
- Specific error code handling
- JSON message validation

## 🐛 Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
```bash
# Check if API is running
curl http://localhost:8000/health

# Check CORS configuration
curl -I http://localhost:8000/api/chat/questionnaire/start/abc123
```

2. **Session ID Not Found**
```bash
# Check if session exists
curl http://localhost:8000/api/chat/questionnaire/initiate/abc123
```

3. **Chat Doesn't Start Automatically**
- Verify that the `initiate_questionnaire` endpoint returns `webui_url` with parameters
- Check WebSocket server is running

### Debug Mode

Enable debug mode to see detailed logs:
```javascript
// In browser console
localStorage.setItem('debug', 'true')
```

### Manual Testing

```bash
# Test WebSocket connection
wscat -c ws://localhost:8000/api/chat/questionnaire/start/abc123

# Test API endpoints
curl http://localhost:8000/api/chat/questionnaire/initiate/abc123
```

### Production Build

1. **Build the Project**
```bash
npm run build
```

2. **Verify Build**
```bash
# Check dist directory
ls -la dist/

# Test production build locally
npx serve dist
```

3. **Deploy**
```bash
# Example: Deploy to static hosting
rsync -avz dist/ user@server:/var/www/html/
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is under the MIT License - see the [LICENSE](LICENSE) file for details. 