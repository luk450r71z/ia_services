#!/bin/bash

echo "Checking health of all services..."
echo "=================================="

# Check if services are running
echo "Checking if containers are running..."
if docker-compose ps | grep -q "ia_services.*Up"; then
  echo "✅ API service is running"
else
  echo "❌ API service is not running"
fi

if docker-compose ps | grep -q "ia_chatbot.*Up"; then
  echo "✅ Chatbot service is running"
else
  echo "❌ Chatbot service is not running"
fi

# Check API endpoints
echo "=================================="
echo "Checking API endpoints..."
API_ROOT=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)
if [ "$API_ROOT" == "200" ]; then
  echo "✅ API root endpoint is responding (200 OK)"
else
  echo "❌ API root endpoint is not responding (got $API_ROOT)"
fi

# Check Chatbot UI
echo "=================================="
echo "Checking Chatbot UI..."
CHATBOT_UI=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/)
if [ "$CHATBOT_UI" == "200" ]; then
  echo "✅ Chatbot UI is responding (200 OK)"
else
  echo "❌ Chatbot UI is not responding (got $CHATBOT_UI)"
fi

echo "=================================="
echo "Health check completed." 