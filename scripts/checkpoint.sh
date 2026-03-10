#!/bin/bash

# Configuration
CONFIG_REPO_DIR=".config-history"
FILES_TO_TRACK=(".env.dev" ".env.prod" "deploy.sh" "docker-compose.prod.yml" "nginx.prod.conf")

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Initialize if not exists
if [ ! -d "$CONFIG_REPO_DIR" ]; then
    echo -e "${BLUE}[INFO]${NC} Initializing local configuration history repository..."
    mkdir -p "$CONFIG_REPO_DIR"
    cd "$CONFIG_REPO_DIR" || exit
    git init -q
    # Configure local user for the sidecar repo
    git config user.name "Karin Bank Config Bot"
    git config user.email "config-bot@karinbank.local"
    # Ensure no remote is added
    cd ..
fi

# Sync files to the hidden repo
echo -e "${BLUE}[INFO]${NC} Syncing sensitive files to local history..."
for file in "${FILES_TO_TRACK[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$CONFIG_REPO_DIR/"
    else
        echo -e "${BLUE}[SKIP]${NC} $file not found."
    fi
done

# Commit changes in the sidecar repo
cd "$CONFIG_REPO_DIR" || exit
git add .

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo -e "${GREEN}[OK]${NC} No changes detected in configurations."
else
    MESSAGE="${1:-"Checkpoint at $(date '+%Y-%m-%d %H:%M:%S')"}"
    git commit -m "$MESSAGE" -q
    echo -e "${GREEN}[SUCCESS]${NC} Configuration checkpoint created: $MESSAGE"
fi

cd ..
