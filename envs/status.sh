#!/bin/bash

echo "Checking IA Services status..."
echo "============================"
docker-compose ps
echo "============================"

echo "Checking API health..."
curl -s http://localhost:8000/ || echo "API service is not responding!"

echo "Checking Chatbot health..."
curl -s -I http://localhost:5000/ | head -n 1 || echo "Chatbot service is not responding!"
