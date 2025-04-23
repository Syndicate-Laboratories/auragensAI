#!/usr/bin/env python
"""
Generate Self-signed X.509 Certificate

This script generates a self-signed X.509 certificate that can be used
for testing MongoDB Atlas connections. For production, you should use
a certificate from MongoDB Atlas.
"""

import os
import subprocess
import base64
import tempfile
from pathlib import Path

def generate_cert():
    """Generate a self-signed X.509 certificate using openssl"""
    cert_dir = Path("certs")
    cert_dir.mkdir(exist_ok=True)
    
    key_path = cert_dir / "mongodb.key"
    cert_path = cert_dir / "mongodb.pem"
    
    print("Generating self-signed certificate...")
    
    # Generate private key
    subprocess.run([
        "openssl", "genrsa", 
        "-out", str(key_path), 
        "2048"
    ], check=True)
    
    # Generate certificate
    subprocess.run([
        "openssl", "req", 
        "-new", "-x509", 
        "-key", str(key_path), 
        "-out", str(cert_path), 
        "-days", "3650", 
        "-subj", "/CN=mongodb-client"
    ], check=True)
    
    # Set permissions
    os.chmod(key_path, 0o600)
    os.chmod(cert_path, 0o600)
    
    print(f"✅ Certificate generated at: {cert_path}")
    return cert_path

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
    print("=== Self-signed X.509 Certificate Generator ===")
    
    # Generate certificate
    cert_path = generate_cert()
    
    # Encode certificate
    base64_cert = encode_cert(cert_path)
    
    if base64_cert:
        print(f"\nBase64 Certificate Preview (first 50 chars):")
        print(f"{base64_cert[:50]}...")
        print(f"\nLength: {len(base64_cert)} characters\n")
        
        # Print Heroku command
        print("To set in Heroku:")
        print(f'heroku config:set MONGO_X509_CERT_BASE64="{base64_cert}" --app auragens-ai')
        
        # Save to file for reference
        with open("cert_base64.txt", "w") as f:
            f.write(base64_cert)
        print("\nSaved base64 certificate to cert_base64.txt")
    else:
        print("❌ Failed to encode certificate")

if __name__ == "__main__":
    main() 