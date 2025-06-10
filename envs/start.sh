#!/bin/bash

echo "Starting IA Services containers..."
docker-compose up -d
echo "Containers started. Use 'docker-compose ps' to check status."
