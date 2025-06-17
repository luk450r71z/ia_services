#!/bin/bash

# Function to print section headers
print_header() {
    echo "================================================"
    echo "$1"
    echo "================================================"
}

# Function to check if a command was successful
check_status() {
    if [ $? -eq 0 ]; then
        echo "✅ $1 completed successfully"
    else
        echo "❌ $1 failed"
        exit 1
    fi
}

# Start backend server for E2E tests
start_backend() {
    print_header "Starting backend server"
    python src/api/main.py &
    BACKEND_PID=$!
    sleep 5  # Wait for server to start
    echo "Backend server started with PID: $BACKEND_PID"
}

# Start frontend server for E2E tests
start_frontend() {
    print_header "Starting frontend server"
    cd src/frontend
    npm run serve &
    FRONTEND_PID=$!
    cd ../..
    sleep 5  # Wait for server to start
    echo "Frontend server started with PID: $FRONTEND_PID"
}

# Stop servers
cleanup() {
    print_header "Cleaning up servers"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID
        echo "Backend server stopped"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID
        echo "Frontend server stopped"
    fi
}

# Set up trap to ensure cleanup on script exit
trap cleanup EXIT

# Run backend unit tests
print_header "Running Backend Unit Tests"
pytest src/api/tests/test_auth.py src/api/tests/test_questionnaire.py -v -m "unit"
check_status "Backend unit tests"

# Run backend integration tests
print_header "Running Backend Integration Tests"
pytest src/api/tests/test_auth.py src/api/tests/test_questionnaire.py -v -m "integration"
check_status "Backend integration tests"

# Run frontend unit tests
print_header "Running Frontend Unit Tests"
cd src/frontend
npm run test:unit
check_status "Frontend unit tests"
cd ../..

# Start servers for E2E tests
start_backend
start_frontend

# Run E2E tests
print_header "Running E2E Tests"
pytest src/tests/e2e/test_chat_flow.py -v
check_status "E2E tests"

print_header "All tests completed successfully! 🎉" 