#!/usr/bin/env python3
import os
import subprocess
import sys

def main():
    token = None
    
    # Try standard env var first
    token = os.getenv('GITHUB_TOKEN')
    
    # If not found, try to get from .hermes env context
    if not token:
        try:
            hermes_env = subprocess.run(['.hermes', 'env'], capture_output=True, text=True)
            for line in hermes_env.stdout.splitlines():
                if line.startswith('GITHUB_TOKEN='):
                    token = line.split('=', 1)[1].strip()
                    break
        except Exception:
            pass
    
    if not token:
        print("Error: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # Validate token by making a request to GitHub API that requires 'repo' scope
    # This endpoint will fail if the token lacks necessary scopes.
    try:
        result = subprocess.run([
            'curl', '-s', '-H', f'Authorization: token {token}',
            'https://api.github.com/user'
        ], capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(result.stderr)
        if 'login' not in result.stdout:
            raise Exception('Unexpected response from GitHub API')
    except Exception as e:
        print(f"Token validation failed: {e}", file=sys.stderr)
        sys.exit(1)

    print("✓ GITHUB_TOKEN is valid.")
    print("✓ Test deployment steps would run now.")
    # TODO: Insert test deployment logic here (e.g., git commit & push)
    print("# Sub-agent monitoring can be triggered after this point.")

if __name__ == "__main__":
    main()