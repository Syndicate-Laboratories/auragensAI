#!/usr/bin/env python
"""
Heroku Startup Script for Setting Up MongoDB Connection
This script prepares the MongoDB connection on Heroku startup,
including certificate handling, database initialization, and environment verification.
"""

import os
import sys
import logging
import base64
import tempfile
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("heroku_setup")

def setup_certificate():
    """Set up the X.509 certificate from environment variables"""
    logger.info("Setting up X.509 certificate...")
    
    cert_base64 = os.getenv("MONGO_X509_CERT_BASE64")
    if not cert_base64:
        logger.error("❌ MONGO_X509_CERT_BASE64 environment variable not found")
        logger.error("Please set this variable with your base64-encoded certificate")
        return False
    
    try:
        # Create the certs directory if it doesn't exist
        os.makedirs("certs", exist_ok=True)
        logger.info("Created 'certs' directory")
        
        # Decode the base64 certificate
        cert_content = base64.b64decode(cert_base64)
        
        # Save to a standard file path
        cert_path = "certs/mongodb.pem"
        with open(cert_path, "wb") as cert_file:
            cert_file.write(cert_content)
        
        # Also save to the specific X.509 certificate path
        specific_cert_path = "certs/X509-cert-4832015629630048359.pem"
        with open(specific_cert_path, "wb") as specific_file:
            specific_file.write(cert_content)
        
        logger.info(f"✅ Certificate saved to {cert_path} and {specific_cert_path}")
        
        # Set proper permissions
        try:
            os.chmod(cert_path, 0o600)
            os.chmod(specific_cert_path, 0o600)
            logger.info("Set proper certificate permissions (600)")
        except Exception as perm_error:
            logger.warning(f"Unable to set certificate permissions: {str(perm_error)}")
        
        # Log the first few lines of the certificate for verification
        with open(cert_path, "r") as cert_file:
            cert_lines = cert_file.readlines()[:5]
            logger.info("Certificate content preview (first 5 lines):")
            for i, line in enumerate(cert_lines):
                logger.info(f"  {i+1}: {line.strip()}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error setting up certificate: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def verify_environment():
    """Verify essential environment variables"""
    logger.info("Verifying environment variables...")
    
    required_vars = [
        "MONGO_URI",
        "MONGO_X509_CERT_BASE64"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your Heroku config")
        return False
    
    # Mask and log important variables
    mongo_uri = os.getenv("MONGO_URI", "")
    masked_uri = mongo_uri[:30] + "..." if mongo_uri else "Not set"
    logger.info(f"MongoDB URI: {masked_uri}")
    
    cert_base64 = os.getenv("MONGO_X509_CERT_BASE64", "")
    has_cert = "Yes" if cert_base64 else "No"
    logger.info(f"Has X.509 Certificate: {has_cert}")
    
    return True

def main():
    """Main function to set up the environment for Heroku"""
    logger.info("=== Heroku MongoDB Setup Script ===")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Python version: {sys.version}")
    
    # Step 1: Verify environment variables
    if not verify_environment():
        logger.error("❌ Environment verification failed")
        return False
    
    # Step 2: Set up certificate
    if not setup_certificate():
        logger.error("❌ Certificate setup failed")
        return False
    
    logger.info("✅ Heroku setup completed successfully")
    logger.info("Application should now be able to connect to MongoDB")
    
    # Log timestamps for debugging
    timestamp = datetime.now().isoformat()
    logger.info(f"Setup completed at: {timestamp}")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            logger.error("❌ Heroku setup script failed")
            # Don't exit with error to allow application to continue
    except Exception as e:
        logger.error(f"❌ Unhandled exception in Heroku setup script: {str(e)}")
        logger.error(traceback.format_exc()) 