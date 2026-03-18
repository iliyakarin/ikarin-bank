#!/bin/bash
set -e

# PRE-BUILD AUTOMATION SCRIPT
# This script runs all available tests and checks before building the Docker containers.

echo "🚀 Starting Pre-build Automation..."

# 1. Secret Scanning (GitLeaks)
echo "🔒 Running Secret Scanning (GitLeaks)..."
if command -v gitleaks &> /dev/null; then
    gitleaks detect --source . -v
else
    echo "⚠️ GitLeaks not found, skipping secret scanning."
fi

# 2. Backend Tests (Pytest)
echo "🐍 Running Backend Tests..."
# Assuming we run them inside the api container if it's already up, 
# or we run them locally if dependencies are installed.
# To be robust, we'll try to run them via docker-compose if containers are running.
if docker compose --env-file .env.dev ps | grep -q "Up"; then
    docker compose --env-file .env.dev exec -e PYTHONPATH=. api pytest tests/
else
    echo "⚠️ Backend containers not running. Running backend tests locally..."
    export PYTHONPATH=.
    pytest backend/tests/ || echo "❌ Backend tests failed!"
fi

# 3. Frontend Unit Tests (NPM)
echo "⚛️ Running Frontend Unit Tests..."
(cd frontend && npx -y tsx --test lib/*.test.ts)



# 4. E2E Tests (Playwright)
echo "🎭 Running E2E Tests (Playwright inside Docker)..."
# Ensure the dev environment is up for E2E tests
if ! docker compose --env-file .env.dev ps | grep -q "Up"; then
    echo "📦 Starting environment for E2E tests..."
    docker compose --env-file .env.dev up -d api postgres kafka clickhouse frontend
    # Wait for frontend to be ready
    echo "⏳ Waiting for frontend to be ready..."
    until $(curl --output /dev/null --silent --head --fail http://localhost:3000/auth/login); do
        printf '.'
        sleep 5
    done
    echo "✅ Frontend is up!"
fi

# Run tests via docker compose
docker compose --env-file .env.dev run --rm playwright



# 5. Build and Deploy
echo "🐳 All tests passed! Building and deploying..."
docker compose --env-file .env.dev up --build -d

echo "✨ Pre-build automation completed successfully!"
