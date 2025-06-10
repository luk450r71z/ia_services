#!/bin/bash

echo "Running all tests..."
echo "===================="

echo "Running API tests..."
cd ../src/api
bash run_tests.sh

echo "===================="
echo "Running Chatbot tests..."
cd ../chatbot
bash run_tests.sh

echo "===================="
echo "All tests completed." 