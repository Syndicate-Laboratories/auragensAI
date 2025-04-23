#!/usr/bin/env python
"""
MongoDB X.509 Certificate Generator
This script creates a proper X.509 certificate for MongoDB authentication
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("cert_generator")

def create_certificate():
    """Create X.509 certificate for MongoDB authentication"""
    cert_dir = "certs"
    cert_path = os.path.join(cert_dir, "mongodb.pem")
    key_path = os.path.join(cert_dir, "mongodb.key")
    csr_path = os.path.join(cert_dir, "mongodb.csr")
    
    # Create directory if it doesn't exist
    os.makedirs(cert_dir, exist_ok=True)
    
    # Step 1: Remove existing files if they exist
    logger.info("Cleaning up any existing certificate files...")
    for file_path in [cert_path, key_path, csr_path]:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Removed existing file: {file_path}")
    
    # Step 2: Generate private key
    logger.info("Generating private key...")
    key_cmd = [
        "openssl", "genrsa",
        "-out", key_path,
        "2048"
    ]
    try:
        subprocess.run(key_cmd, check=True, capture_output=True)
        logger.info(f"Private key generated at {key_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate private key: {e.stderr.decode()}")
        return False
    
    # Step 3: Create Certificate Signing Request (CSR)
    logger.info("Creating Certificate Signing Request (CSR)...")
    csr_cmd = [
        "openssl", "req", "-new",
        "-key", key_path,
        "-out", csr_path,
        "-subj", "/CN=auragensai/O=AuragensAI/C=US"
    ]
    try:
        subprocess.run(csr_cmd, check=True, capture_output=True)
        logger.info(f"CSR created at {csr_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create CSR: {e.stderr.decode()}")
        return False
    
    # Step 4: Create self-signed certificate
    logger.info("Creating self-signed certificate...")
    cert_cmd = [
        "openssl", "x509", "-req",
        "-days", "365",
        "-in", csr_path,
        "-signkey", key_path,
        "-out", cert_path
    ]
    try:
        subprocess.run(cert_cmd, check=True, capture_output=True)
        logger.info(f"Certificate created at {cert_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create certificate: {e.stderr.decode()}")
        return False
    
    # Step 5: Combine key and certificate into a single PEM file
    logger.info("Creating combined PEM file...")
    with open(cert_path, 'r') as cert_file:
        cert_content = cert_file.read()
    
    with open(key_path, 'r') as key_file:
        key_content = key_file.read()
    
    with open(cert_path, 'w') as pem_file:
        pem_file.write(key_content)
        pem_file.write(cert_content)
    
    logger.info(f"Combined PEM file created at {cert_path}")
    
    # Step 6: Set appropriate permissions
    try:
        os.chmod(cert_path, 0o600)  # Only owner can read/write
        logger.info(f"Set permissions on {cert_path} to 600 (owner read/write)")
    except Exception as e:
        logger.warning(f"Failed to set permissions: {str(e)}")
    
    # Clean up temporary files
    if os.path.exists(csr_path):
        os.remove(csr_path)
    
    return True

def main():
    logger.info("=== MongoDB X.509 Certificate Generator ===")
    
    if create_certificate():
        logger.info("✅ Certificate generation completed successfully")
        logger.info(f"Certificate path: {os.path.abspath('certs/mongodb.pem')}")
        logger.info("\nTo use this certificate with MongoDB:")
        logger.info("1. Add your certificate to MongoDB Atlas X.509 authentication")
        logger.info("2. Make sure your MONGO_URI includes 'authMechanism=MONGODB-X509'")
        logger.info("3. Update your code to use 'tlsCertificateKeyFile=<path_to_certificate>'")
    else:
        logger.error("❌ Certificate generation failed")

if __name__ == "__main__":
    main() 