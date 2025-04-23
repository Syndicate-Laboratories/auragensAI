#!/usr/bin/env python
"""
MongoDB Database Fix Script
This script will update the MongoDB connection using the correct X.509 certificate
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
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("fix_database")

# Load environment variables
load_dotenv(override=True)

def find_and_copy_certificate():
    """Find and copy the X.509 certificate to the right location"""
    certificate_found = False
    dest_path = "certs/mongodb.pem"
    
    # Create certs directory if it doesn't exist
    os.makedirs("certs", exist_ok=True)
    
    # Check if the specific certificate exists
    x509_cert = "certs/X509-cert-4832015629630048359.pem"
    if os.path.exists(x509_cert):
        logger.info(f"Found existing X.509 certificate: {x509_cert}")
        # Copy the certificate to the standard location
        shutil.copy2(x509_cert, dest_path)
        logger.info(f"Copied certificate to standard location: {dest_path}")
        certificate_found = True
    else:
        logger.warning(f"Specified X.509 certificate not found: {x509_cert}")
        
        # Search for any other .pem files
        try:
            result = subprocess.run(["find", ".", "-name", "*.pem", "-type", "f"], 
                                  capture_output=True, text=True, check=True)
            pem_files = result.stdout.strip().split('\n')
            
            if pem_files:
                logger.info(f"Found {len(pem_files)} PEM files:")
                for i, pem_file in enumerate(pem_files):
                    logger.info(f"{i+1}. {pem_file}")
                
                # Use the first non-standard library PEM file
                for pem_file in pem_files:
                    if not ('venv' in pem_file or 'site-packages' in pem_file):
                        shutil.copy2(pem_file, dest_path)
                        logger.info(f"Copied certificate from {pem_file} to {dest_path}")
                        certificate_found = True
                        break
            
            if not certificate_found:
                logger.warning("No suitable PEM files found to use as certificate")
        except Exception as e:
            logger.error(f"Error searching for PEM files: {str(e)}")
    
    return certificate_found, dest_path

def update_env_file():
    """Update the .env file with the correct MongoDB URI"""
    try:
        # Read the existing .env file
        env_file_path = ".env"
        env_content = ""
        
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as env_file:
                env_content = env_file.read()
        
        # Update or add the MongoDB URI
        uri_line = 'MONGO_URI=mongodb+srv://auragensai.6zehw.mongodb.net/?authSource=%24external&authMechanism=MONGODB-X509&retryWrites=true&w=majority&appName=AuragensAI'
        cert_line = 'MONGO_X509_CERT_PATH=certs/mongodb.pem'
        
        # Check if MONGO_URI already exists in the file
        if 'MONGO_URI=' in env_content:
            # Replace the existing URI
            lines = env_content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('MONGO_URI='):
                    lines[i] = uri_line
            env_content = '\n'.join(lines)
        else:
            # Add the URI if it doesn't exist
            env_content += f'\n{uri_line}'
        
        # Check if MONGO_X509_CERT_PATH already exists in the file
        if 'MONGO_X509_CERT_PATH=' in env_content:
            # Replace the existing path
            lines = env_content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('MONGO_X509_CERT_PATH='):
                    lines[i] = cert_line
            env_content = '\n'.join(lines)
        else:
            # Add the path if it doesn't exist
            env_content += f'\n{cert_line}'
        
        # Write the updated content back to the file
        with open(env_file_path, 'w') as env_file:
            env_file.write(env_content)
        
        logger.info(f"Updated .env file with MongoDB URI and certificate path")
        return True
    except Exception as e:
        logger.error(f"Error updating .env file: {str(e)}")
        return False

def test_mongodb_connection():
    """Test the MongoDB connection with the X.509 certificate"""
    try:
        # Get MongoDB URI from environment
        uri = os.getenv("MONGO_URI")
        if not uri:
            uri = "mongodb+srv://auragensai.6zehw.mongodb.net/?authSource=%24external&authMechanism=MONGODB-X509&retryWrites=true&w=majority&appName=AuragensAI"
        
        cert_path = os.getenv("MONGO_X509_CERT_PATH", "certs/mongodb.pem")
        
        logger.info(f"Testing connection to MongoDB with URI: {uri[:50]}...")
        logger.info(f"Using certificate at: {cert_path}")
        
        # Try connection with certificate
        client = MongoClient(
            uri,
            tls=True,
            tlsCertificateKeyFile=cert_path,
            server_api=ServerApi('1')
        )
        
        # Test connection
        client.admin.command('ping')
        logger.info("✅ Successfully connected to MongoDB!")
        
        # Initialize database and collections
        db = client['Auragens_AI']
        
        # Print available collections
        collections = db.list_collection_names()
        logger.info(f"Available collections: {collections}")
        
        if len(collections) == 0:
            logger.warning("No collections found. Creating initial collections...")
            
            # Create required collections
            db.create_collection('chats')
            db.create_collection('vector_embeddings')
            db.create_collection('users')
            db.create_collection('feedback')
            
            # Create indexes
            db.chats.create_index([('user_id', 1)])
            db.chats.create_index([('timestamp', -1)])
            db.vector_embeddings.create_index([('category', 1)])
            db.vector_embeddings.create_index([('timestamp', -1)])
            db.users.create_index([('user_id', 1)], unique=True)
            db.users.create_index([('email', 1)])
            db.feedback.create_index([('chat_id', 1)])
            db.feedback.create_index([('timestamp', -1)])
            
            logger.info("Created collections and indexes successfully")
            
            # Add test document to vector_embeddings
            test_doc = {
                'title': 'Test Document',
                'content': 'This is a test document for Auragens AI vector database.',
                'category': 'test',
                'timestamp': datetime.now()
            }
            
            db.vector_embeddings.insert_one(test_doc)
            logger.info("Added test document to vector_embeddings collection")
            
            # Add test user
            test_user = {
                'user_id': 'test_user',
                'email': 'test@example.com',
                'name': 'Test User',
                'created_at': datetime.now()
            }
            
            db.users.insert_one(test_user)
            logger.info("Added test user to users collection")
        
        # Count documents in each collection
        for collection_name in db.list_collection_names():
            count = db[collection_name].count_documents({})
            logger.info(f"Collection '{collection_name}' has {count} documents")
        
        return True
    except Exception as e:
        logger.error(f"❌ MongoDB connection test failed: {str(e)}")
        return False

def main():
    logger.info("=== MongoDB Database Fix Script ===")
    
    # Step 1: Find and copy the certificate
    cert_found, cert_path = find_and_copy_certificate()
    if not cert_found:
        logger.error("Could not find or set up the X.509 certificate")
        return False
    
    # Step 2: Update the .env file
    if not update_env_file():
        logger.warning("Failed to update .env file, but continuing...")
    
    # Step 3: Test the MongoDB connection
    if test_mongodb_connection():
        logger.info("✅ MongoDB connection and setup completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Update your database.py with the correct certificate path")
        logger.info("2. Restart your application to apply the changes")
        return True
    else:
        logger.error("❌ MongoDB connection failed")
        logger.info("\nTroubleshooting:")
        logger.info("1. Check your MongoDB Atlas settings to ensure X.509 authentication is enabled")
        logger.info("2. Verify that the certificate has been added to your MongoDB Atlas cluster")
        logger.info("3. Check your network connectivity")
        return False

if __name__ == "__main__":
    # Import datetime for document timestamps 
    from datetime import datetime
    main() 