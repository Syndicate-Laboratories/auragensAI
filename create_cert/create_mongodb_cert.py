#!/usr/bin/env python
"""
MongoDB X.509 Certificate Helper Script

This script helps with:
1. Generating an X.509 certificate (if possible)
2. Converting an existing certificate to base64 for Heroku
3. Setting up environment variables for local development
"""

import os
import sys
import base64
import argparse
from pathlib import Path

def cert_to_base64(cert_path):
    """Convert a certificate file to base64 encoding"""
    try:
        with open(cert_path, 'rb') as cert_file:
            cert_content = cert_file.read()
            
        # Encode to base64
        base64_cert = base64.b64encode(cert_content).decode('utf-8')
        return base64_cert
    except Exception as e:
        print(f"Error reading certificate: {str(e)}")
        return None

def create_env_entry(base64_cert):
    """Create a .env file entry for the certificate"""
    return f'MONGO_X509_CERT_BASE64="{base64_cert}"'

def print_heroku_command(base64_cert):
    """Print the Heroku command to set the certificate"""
    # Wrap in quotes and make sure any quotes in the base64 string are escaped
    cmd = f'heroku config:set MONGO_X509_CERT_BASE64="{base64_cert}" --app YOUR_APP_NAME'
    return cmd

def main():
    parser = argparse.ArgumentParser(description="MongoDB X.509 Certificate Helper")
    parser.add_argument('cert_path', type=str, help='Path to the X.509 certificate (.pem file)')
    parser.add_argument('--heroku', action='store_true', help='Print Heroku set command')
    parser.add_argument('--env', action='store_true', help='Print .env file entry')
    parser.add_argument('--save', type=str, help='Save to a file', default=None)
    
    args = parser.parse_args()
    
    # Check if file exists
    cert_path = Path(args.cert_path)
    if not cert_path.exists():
        print(f"Error: Certificate file not found at {cert_path}")
        sys.exit(1)
        
    # Convert certificate to base64
    print(f"Converting certificate: {cert_path}")
    base64_cert = cert_to_base64(cert_path)
    
    if not base64_cert:
        print("Error: Failed to convert certificate to base64")
        sys.exit(1)
    
    # Display base64 certificate snippet for verification
    print(f"\nBase64 Certificate Preview (first 50 chars):")
    print(f"{base64_cert[:50]}...")
    print(f"\nLength: {len(base64_cert)} characters\n")
    
    # Display as requested
    if args.heroku:
        cmd = print_heroku_command(base64_cert)
        print("Heroku Command:")
        print(cmd)
        
    if args.env:
        env_entry = create_env_entry(base64_cert)
        print("\nAdd this to your .env file:")
        print(env_entry)
    
    # Save to file if specified
    if args.save:
        save_path = Path(args.save)
        try:
            with open(save_path, 'w') as f:
                f.write(base64_cert)
            print(f"\nSaved base64 certificate to: {save_path}")
        except Exception as e:
            print(f"Error saving file: {str(e)}")
    
    print("\nDone!")

if __name__ == "__main__":
    main()
