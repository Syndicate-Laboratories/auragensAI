#!/usr/bin/env python
"""
Encode Existing X.509 Certificate

This script takes an existing certificate file and encodes it to base64
for use with Heroku environment variables.
"""

import base64
import sys

CERT_PATH = "/Users/jamesutley/auragensAI/auragensAI/certs/X509-cert-4832015629630048359.pem"

def encode_cert(cert_path):
    """Read certificate and encode to base64"""
    try:
        with open(cert_path, 'rb') as cert_file:
            cert_content = cert_file.read()
            
        # Encode to base64
        base64_cert = base64.b64encode(cert_content).decode('utf-8')
        return base64_cert
    except Exception as e:
        print(f"Error encoding certificate: {str(e)}")
        return None

def main():
    print("=== Encode Existing X.509 Certificate ===")
    print(f"Certificate path: {CERT_PATH}")
    
    # Encode certificate
    base64_cert = encode_cert(CERT_PATH)
    
    if base64_cert:
        print(f"\nBase64 Certificate Preview (first 50 chars):")
        print(f"{base64_cert[:50]}...")
        print(f"\nLength: {len(base64_cert)} characters\n")
        
        # Print Heroku command
        print("To set in Heroku:")
        heroku_cmd = f'heroku config:set MONGO_X509_CERT_BASE64="{base64_cert}" --app auragens-ai'
        print(heroku_cmd)
        
        # Save to file for reference
        with open("cert_base64.txt", "w") as f:
            f.write(base64_cert)
        print("\nSaved base64 certificate to cert_base64.txt")
    else:
        print("❌ Failed to encode certificate")

if __name__ == "__main__":
    main() 