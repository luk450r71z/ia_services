# Function to print section headers
function Write-Header {
    param([string]$text)
    Write-Host "================================================"
    Write-Host $text
    Write-Host "================================================"
}

# Function to check if a command was successful
function Test-CommandStatus {
    param([string]$operation)
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ $operation completed successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ $operation failed" -ForegroundColor Red
        exit 1
    }
}

# Start backend server for E2E tests
function Start-BackendServer {
    Write-Header "Starting backend server"
    Start-Process python -ArgumentList "src/api/main.py" -NoNewWindow
    $script:backendProcess = Get-Process python | Sort-Object StartTime | Select-Object -Last 1
    Start-Sleep -Seconds 5  # Wait for server to start
    Write-Host "Backend server started with PID: $($script:backendProcess.Id)"
}

# Start frontend server for E2E tests
function Start-FrontendServer {
    Write-Header "Starting frontend server"
    Push-Location src/frontend
    Start-Process npm -ArgumentList "run serve" -NoNewWindow
    $script:frontendProcess = Get-Process node | Sort-Object StartTime | Select-Object -Last 1
    Pop-Location
    Start-Sleep -Seconds 5  # Wait for server to start
    Write-Host "Frontend server started with PID: $($script:frontendProcess.Id)"
}

# Stop servers
function Stop-TestServers {
    Write-Header "Cleaning up servers"
    if ($script:backendProcess) {
        Stop-Process -Id $script:backendProcess.Id -Force
        Write-Host "Backend server stopped"
    }
    if ($script:frontendProcess) {
        Stop-Process -Id $script:frontendProcess.Id -Force
        Write-Host "Frontend server stopped"
    }
}

# Set up cleanup on script exit
$script:backendProcess = $null
$script:frontendProcess = $null
try {
    # Run backend unit tests
    Write-Header "Running Backend Unit Tests"
    pytest src/api/tests/test_auth.py src/api/tests/test_questionnaire.py -v -m "unit"
    Test-CommandStatus "Backend unit tests"

    # Run backend integration tests
    Write-Header "Running Backend Integration Tests"
    pytest src/api/tests/test_auth.py src/api/tests/test_questionnaire.py -v -m "integration"
    Test-CommandStatus "Backend integration tests"

    # Run frontend unit tests
    Write-Header "Running Frontend Unit Tests"
    Push-Location src/frontend
    npm run test:unit
    Test-CommandStatus "Frontend unit tests"
    Pop-Location

    # Start servers for E2E tests
    Start-BackendServer
    Start-FrontendServer

    # Run E2E tests
    Write-Header "Running E2E Tests"
    pytest src/tests/e2e/test_chat_flow.py -v
    Test-CommandStatus "E2E tests"

    Write-Header "All tests completed successfully! 🎉"
} finally {
    Stop-TestServers
} 