#!/usr/bin/env python3
"""
Saxo Bank OAuth2 Refresh Token Rotation Script

This script rotates the refresh token for Saxo Bank's OpenAPI.
It uses the PKCE flow to obtain a new refresh token and updates
the GitHub secret accordingly.
"""

import base64
import hashlib
import os
import requests
import secrets
import sys

CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "live")

BASE_URL = "https://gateway.saxobank.com/sim/openapi" if ENVIRONMENT == "sim" else "https://gateway.saxobank.com/openapi"
TOKEN_ENDPOINT = f"{BASE_URL}/token"
AUTH_ENDPOINT = f"{BASE_URL}/auth"
REDIRECT_URI = "https://localhost:8080/callback"


def generate_code_verifier() -> str:
    """Generate a code verifier for PKCE."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')


def generate_code_challenge(verifier: str) -> str:
    """Generate a code challenge from the verifier."""
    sha256 = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(sha256).decode('utf-8').rstrip('=')


def refresh_token() -> str:
    """Refresh the access token using the refresh token."""
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': REFRESH_TOKEN,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'm': '0',  # Required for refresh token rotation
    }
    
    response = requests.post(TOKEN_ENDPOINT, data=data, timeout=30)
    
    if response.status_code != 200:
        print(f"Error refreshing token: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    token_data = response.json()
    new_refresh_token = token_data.get('refresh_token')
    
    if not new_refresh_token:
        print("No refresh token in response")
        sys.exit(1)
    
    with open(os.environ['GITHUB_ENV'], 'a') as f:
        f.write(f"NEW_REFRESH_TOKEN={new_refresh_token}\n")
    
    print(f"Successfully rotated refresh token for {ENVIRONMENT} environment")
    return new_refresh_token


if __name__ == "__main__":
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("Missing required environment variables")
        sys.exit(1)
    
    refresh_token()
