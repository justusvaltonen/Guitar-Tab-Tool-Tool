#!/usr/bin/env bash
# Automates GitHub repo creation and initial push
# Requires: GITHUB_TOKEN env var (fine-grained token with repo:write)

set -euo pipefail

REPO_NAME="${1:-generic-testing-repo-name}"
DESCRIPTION="${2:-A test repository for automation}"

echo "🚀 Creating repo: justusvaltonen/$REPO_NAME"

# Validate token is set
if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "❌ ERROR: GITHUB_TOKEN environment variable not set"
    echo "   Set it with: export GITHUB_TOKEN=ghp_your_token_here"
    exit 1
fi

# Create repo via GitHub API
RESPONSE=$(curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/user/repos \
  -d "{
    \"name\": \"$REPO_NAME\",
    \"description\": \"$DESCRIPTION\",
    \"private\": false,
    \"auto_init\": false
  }")

# Check if creation succeeded
if echo "$RESPONSE" | grep -q '"message":.*"Validation Failed"'; then
    echo "❌ Failed to create repo:"
    echo "$RESPONSE" | python3 -m json.tool
    exit 1
fi

# Get the clone URL
CLONE_URL=$(echo "$RESPONSE" | grep -o '"clone_url":"[^"]*"' | cut -d'"' -f4)
echo "✅ Repo created: $CLONE_URL"

# Initialize local repo if not already done
if [ ! -d ".git" ]; then
    git init
    git add .
    git commit -m "Initial commit"
fi

# Add remote and push
git remote remove origin 2>/dev/null || true
git remote add origin "$CLONE_URL"
git branch -M main
git push -u origin main

echo "🎉 Successfully pushed to: $CLONE_URL"
echo "📝 To update later: git push origin main"