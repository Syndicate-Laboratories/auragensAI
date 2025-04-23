#!/usr/bin/env python
"""
MongoDB Connection Test Script using X.509 Authentication
Based on the documentation example
"""

import os
import sys
import logging
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import ssl
import tempfile
import base64
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mongodb_test")

# Load environment variables
load_dotenv(override=True)

def create_test_certificate():
    """Create a self-signed certificate for testing if needed"""
    cert_path = os.getenv("MONGO_X509_CERT_PATH", "certs/mongodb.pem")
    cert_exists = os.path.isfile(cert_path)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(cert_path), exist_ok=True)
    
    if not cert_exists:
        logger.info(f"Certificate not found at {cert_path}, creating a self-signed certificate...")
        try:
            # Create a self-signed certificate
            cmd = [
                "openssl", "req", "-new", "-x509", "-days", "365", "-nodes",
                "-out", cert_path,
                "-keyout", cert_path,
                "-subj", "/CN=AuragensAI/O=AuragensAI/C=US"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Self-signed certificate created at {cert_path}")
                return cert_path, True
            else:
                logger.error(f"Failed to create certificate: {result.stderr}")
                return None, False
        except Exception as e:
            logger.error(f"Error creating certificate: {str(e)}")
            return None, False
    else:
        logger.info(f"Using existing certificate at {cert_path}")
        return cert_path, True

def test_connection():
    """Test MongoDB connection using the documentation example"""
    # URI directly from the documentation
    uri = "mongodb+srv://auragensai.6zehw.mongodb.net/?authSource=%24external&authMechanism=MONGODB-X509&retryWrites=true&w=majority&appName=AuragensAI"
    
    # Try connection with different certificate configurations
    certificate_path, cert_exists = create_test_certificate()
    
    if not cert_exists:
        logger.error("Failed to prepare certificate")
        return False
    
    try:
        logger.info(f"Attempting connection to {uri} with certificate at {certificate_path}")
        client = MongoClient(
            uri,
            tls=True,
            tlsCertificateKeyFile=certificate_path,
            server_api=ServerApi('1')
        )
        
        # Test connection by pinging the server
        client.admin.command('ping')
        logger.info("✅ Successfully connected to MongoDB!")
        
        # Try to access the database
        db = client['Auragens_AI']
        collections = db.list_collection_names()
        logger.info(f"Available collections: {collections}")
        
        # Print counts for each collection
        for collection_name in collections:
            count = db[collection_name].count_documents({})
            logger.info(f"Collection '{collection_name}' has {count} documents")
        
        return True
    except Exception as e:
        logger.error(f"❌ Connection failed: {str(e)}")
        
        # Try alternative connection method without certificate
        try:
            logger.info("Attempting connection without certificate...")
            client = MongoClient(
                uri,
                tls=True,
                tlsAllowInvalidCertificates=True,
                server_api=ServerApi('1')
            )
            client.admin.command('ping')
            logger.info("✅ Successfully connected to MongoDB without certificate!")
            
            # Try to access the database
            db = client['Auragens_AI']
            collections = db.list_collection_names()
            logger.info(f"Available collections: {collections}")
            
            return True
        except Exception as alt_error:
            logger.error(f"❌ Alternative connection also failed: {str(alt_error)}")
            return False

def main():
    logger.info("=== MongoDB Connection Test ===")
    
    if test_connection():
        logger.info("✅ MongoDB connection test completed successfully")
    else:
        logger.error("❌ MongoDB connection test failed")
        
        # Provide recommendations
        logger.info("\nRecommendations:")
        logger.info("1. Verify your MongoDB Atlas cluster is running and accessible")
        logger.info("2. Check network connectivity (firewalls, VPNs, etc.)")
        logger.info("3. Verify the MongoDB URI is correct")
        logger.info("4. Ensure your X.509 certificate is valid and corresponds to a user with access to the cluster")
        logger.info("5. Try connecting from MongoDB Compass to confirm cluster accessibility")

if __name__ == "__main__":
    main() 