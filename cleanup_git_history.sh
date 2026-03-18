#!/bin/bash

# Script to remove .env files from git history
# This removes .env.dev and .env.prod from all commits

echo "Removing .env files from git history..."

# Create a backup branch first
git branch backup-before-cleanup

# Use git filter-branch to remove the files
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env.dev .env.prod" \
  --prune-empty --tag-name-filter cat -- --all

# Clean up refs
git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo "Cleanup complete!"
echo "Please verify the changes and then force push:"
echo "git push origin --force --all"