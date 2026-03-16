#!/bin/bash

# Configuration
# Load .env.dev for the webhook secret if it exists locally, 
# but gateway listen will provide its own temporary secret.
API_URL="http://localhost:8000/api/v1/gateway/webhook"

echo "Starting Gateway CLI listener..."
echo "Forwarding events to: $API_URL"

# You must have the Gateway CLI installed: https://gateway.com/docs/gateway-cli
# And be logged in: gateway login

gateway listen --forward-to "$API_URL"
