#!/usr/bin/env python3
"""
Authenticate with Google Drive API locally.
Run this script OUTSIDE of Docker to generate token.json

Usage:
    python backend/scripts/authenticate_google_drive.py
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from infrastructure.google_drive_client import GoogleDriveClient


def main():
    print("🔐 Google Drive Authentication")
    print("=" * 50)
    print()
    
    # Create client
    client = GoogleDriveClient()
    
    print(f"📁 Credentials directory: {client.credentials_dir}")
    print(f"🔑 Client secret: {client.client_secret_path}")
    print(f"🎫 Token file: {client.token_path}")
    print()
    
    # Check if client_secret.json exists
    if not client.client_secret_path.exists():
        print("❌ ERROR: client_secret.json not found!")
        print(f"   Expected location: {client.client_secret_path}")
        print()
        print("📋 To fix this:")
        print("   1. Download client_secret.json from Google Cloud Console")
        print("   2. Place it in: backend/credentials/client_secret.json")
        print()
        print("   See docs/GOOGLE_DRIVE_SETUP.md for detailed instructions")
        sys.exit(1)
    
    print("✅ client_secret.json found")
    print()
    
    # Authenticate
    try:
        print("🚀 Starting OAuth 2.0 flow...")
        print("   A browser window will open for authentication")
        print()
        
        client.authenticate()
        
        print()
        print("=" * 50)
        print("✅ Authentication successful!")
        print()
        print(f"🎫 Token saved to: {client.token_path}")
        print()
        print("📋 Next steps:")
        print("   1. Copy token.json to Docker volume (if using Docker)")
        print("   2. Or the application will use it automatically")
        print()
        print("🧪 Test the connection:")
        print("   python -c \"from infrastructure.google_drive_client import get_drive_client; "
              "client = get_drive_client(); client.authenticate(); "
              "print('Files:', len(client.list_files_in_folder('1Jo5doFrRgTscczqR0c6bsS2H0a7pS2ZR')))\"")
        
    except Exception as e:
        print()
        print("=" * 50)
        print(f"❌ Authentication failed: {e}")
        print()
        print("💡 Troubleshooting:")
        print("   - Make sure client_secret.json is valid")
        print("   - Check that Google Drive API is enabled in Google Cloud Console")
        print("   - Verify OAuth consent screen is configured")
        sys.exit(1)


if __name__ == "__main__":
    main()
