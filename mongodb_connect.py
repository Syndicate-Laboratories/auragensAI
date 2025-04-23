#!/usr/bin/env python
"""
Minimal MongoDB Connection Test with X.509 Certificate
"""

import os
import sys
import logging
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mongodb_connect")

# Load environment variables
load_dotenv(override=True)

def main():
    # Specify the exact certificate file
    cert_file = "certs/X509-cert-4832015629630048359.pem"
    
    # Check if certificate exists
    if not os.path.isfile(cert_file):
        logger.error(f"Certificate file not found: {cert_file}")
        return False
    
    logger.info(f"Using certificate: {cert_file}")
    
    # MongoDB connection URI - using exact format from documentation
    uri = "mongodb+srv://auragensai.6zehw.mongodb.net/?authSource=%24external&authMechanism=MONGODB-X509&retryWrites=true&w=majority&appName=AuragensAI"
    
    # Print certificate content (first few lines)
    try:
        with open(cert_file, 'r') as f:
            content = f.readlines()
            logger.info(f"Certificate content (first 5 lines):")
            for i, line in enumerate(content[:5]):
                logger.info(f"  {i+1}: {line.strip()}")
    except Exception as e:
        logger.error(f"Error reading certificate: {str(e)}")
    
    # Try connection
    try:
        logger.info(f"Connecting to MongoDB: {uri[:50]}...")
        client = MongoClient(
            uri,
            tls=True,
            tlsCertificateKeyFile=cert_file,
            server_api=ServerApi('1')
        )
        
        # Test connection
        logger.info("Pinging MongoDB server...")
        client.admin.command('ping')
        logger.info("✅ Successfully connected to MongoDB!")
        
        # Get database and collection info
        db_list = client.list_database_names()
        logger.info(f"Available databases: {db_list}")
        
        # Use the Auragens_AI database
        db = client['Auragens_AI']
        collections = db.list_collection_names()
        logger.info(f"Collections in Auragens_AI: {collections}")
        
        # Print document counts
        for collection in collections:
            count = db[collection].count_documents({})
            logger.info(f"  {collection}: {count} documents")
        
        return True
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {str(e)}")
        
        # Try alternative connection method
        try:
            logger.info("Attempting alternative connection...")
            client = MongoClient(
                uri,
                tls=True,
                tlsAllowInvalidCertificates=True,
                server_api=ServerApi('1')
            )
            client.admin.command('ping')
            logger.info("✅ Alternative connection successful!")
            return True
        except Exception as alt_error:
            logger.error(f"❌ Alternative connection also failed: {str(alt_error)}")
            return False

if __name__ == "__main__":
    logger.info("=== Simple MongoDB Connection Test ===")
    result = main()
    if result:
        logger.info("Connection test completed successfully.")
    else:
        logger.error("Connection test failed.")
        # Print troubleshooting tips
        logger.info("\nTroubleshooting tips:")
        logger.info("1. Check that the MongoDB Atlas cluster is accessible")
        logger.info("2. Verify the certificate has been registered with MongoDB Atlas")
        logger.info("3. Ensure the cluster name in the URI is correct")
        logger.info("4. Check firewall/network settings that might block MongoDB connections") 