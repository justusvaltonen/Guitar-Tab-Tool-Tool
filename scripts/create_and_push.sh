#!/usr/bin/env bash
# Automates GitHub repo creation and initial push
# Requires: GITHUB_TOKEN env var (fine-grained token with repo:write)

set -euo pipefail

REPO_NAME="${1:-guitar-tab-tool-tool}"
DESCRIPTION="${2:-A lightweight command-line toolkit for working with guitar tablature}"

echo "🚀 Setting up repo: justusvaltonen/$REPO_NAME"

# Validate token is set
if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "❌ ERROR: GITHUB_TOKEN environment variable not set"
    echo "   Set it with: export GITHUB_TOKEN=ghp_your_token_here"
    exit 1
fi

# Check if repo already exists
CHECK_RESPONSE=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/justusvaltonen/$REPO_NAME")

if echo "$CHECK_RESPONSE" | grep -q '"full_name":'; then
    echo "ℹ️ Repository already exists, using existing..."
    REPO_URL="https://github.com/justusvaltonen/$REPO_NAME"
else
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
    REPO_URL=$(echo "$RESPONSE" | grep -o '\"clone_url\":\"[^\"]*\"' | cut -d'"' -f4)
    echo "✅ Repo created: $REPO_URL"
fi

# Initialize Git repo if not already done
if [ ! -d ".git" ]; then
    git init -b main
    git remote add origin "$REPO_URL"
fi

# Force HTTPS push using token in URL
echo "📦 Pushing to: $REPO_URL"
git push "https://$GITHUB_TOKEN@github.com/justusvaltonen/$REPO_NAME" main 2>/dev/null || {
    echo "❌ Git push failed. Ensure the token has repo:write permissions."
    exit 1
}

echo "🎉 Successfully pushed to: $REPO_URL"
echo "📝 To update later: git push origin main"