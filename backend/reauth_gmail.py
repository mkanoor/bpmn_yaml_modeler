#!/usr/bin/env python3
"""
Re-authenticate Gmail API

This script deletes the old token and forces re-authentication with correct scopes.
Run this if you see "invalid_scope" errors.
"""

import os
import sys

def main():
    print("Gmail Re-authentication Tool")
    print("=" * 50)

    # Check for credentials.json
    if not os.path.exists('credentials.json'):
        print("❌ ERROR: credentials.json not found!")
        print("   Please download from Google Cloud Console")
        print("   See: GMAIL_API_INTEGRATION.md for instructions")
        sys.exit(1)

    print("✓ Found credentials.json")

    # Delete token.json if it exists
    if os.path.exists('token.json'):
        os.remove('token.json')
        print("✓ Deleted old token.json")
    else:
        print("ℹ No existing token.json to delete")

    print()
    print("Now starting OAuth flow...")
    print("This will open your browser for authorization.")
    print()

    # Import and authenticate
    try:
        from gmail_service import get_gmail_service

        print("Authenticating with Gmail API...")
        service = get_gmail_service()

        if service.authenticate():
            print()
            print("=" * 50)
            print("✅ SUCCESS! Gmail is now authenticated.")
            print("=" * 50)
            print()
            print("New token.json has been created with correct scopes:")
            print("  • gmail.send")
            print("  • gmail.readonly")
            print("  • gmail.modify")
            print()
            print("You can now run workflows that send emails!")
            print()
        else:
            print()
            print("❌ Authentication failed!")
            print("   Check the error messages above.")
            sys.exit(1)

    except Exception as e:
        print()
        print(f"❌ ERROR: {e}")
        print()
        print("Troubleshooting:")
        print("1. Make sure credentials.json is valid")
        print("2. Check that Gmail API is enabled in Google Cloud Console")
        print("3. Verify the OAuth consent screen is configured")
        print("4. See GMAIL_API_INTEGRATION.md for setup instructions")
        sys.exit(1)

if __name__ == '__main__':
    main()
