#!/bin/bash

# Configuration
# Load .env.dev for the webhook secret if it exists locally, 
# but stripe listen will provide its own temporary secret.
API_URL="http://localhost:8000/api/v1/stripe/webhook"

echo "Starting Stripe CLI listener..."
echo "Forwarding events to: $API_URL"

# You must have the Stripe CLI installed: https://stripe.com/docs/stripe-cli
# And be logged in: stripe login

stripe listen --forward-to "$API_URL"
