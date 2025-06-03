# IA Services - Chatbot

Servicio de chatbot para la plataforma IA Services.

## Desarrollo Local

### Prerequisitos
- Node.js 18+
- npm

### Instalación
```bash
npm install
```

### Desarrollo
```bash
npm run dev
```
La aplicación estará disponible en: http://localhost:3000

### Build
```bash
npm run build
```

## Docker

### Construir imagen
```bash
docker build -t ia-services-chatbot .
```

### Ejecutar contenedor
```bash
docker run -p 8080:80 ia-services-chatbot
```

La aplicación estará disponible en: http://localhost:8080

## Estructura del Proyecto

```
src/chatbot/
├── index.html          # Punto de entrada HTML
├── src/
│   ├── main.js        # Punto de entrada JavaScript
│   ├── App.vue        # Componente principal
│   ├── components/    # Componentes reutilizables
│   └── pages/         # Páginas de la aplicación
├── package.json       # Dependencias del proyecto
└── Dockerfile         # Configuración Docker
``` 