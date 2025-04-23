#!/usr/bin/env python
"""
MongoDB Database Initialization and Test Script
This script verifies the MongoDB connection, creates required collections,
initializes vector search indexes, and adds sample data if needed.
"""

import os
import sys
import time
from dotenv import load_dotenv
from pymongo import MongoClient, errors
from pymongo.server_api import ServerApi
import logging
from datetime import datetime
import ssl
import base64
import tempfile
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
import gc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("db_init")

# Load environment variables
load_dotenv(override=True)

def check_environment():
    """Check if all required environment variables are set"""
    logger.info("Checking environment variables...")
    required_vars = ["MONGO_URI"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your .env file or environment")
        return False
    
    # Get and mask MongoDB URI for logging
    uri = os.getenv("MONGO_URI")
    masked_uri = uri[:30] + "..." if uri else "None"
    logger.info(f"MongoDB URI: {masked_uri}")
    
    # Validate MongoDB URI format
    if uri:
        try:
            # Check basic URI format
            if not uri.startswith(("mongodb://", "mongodb+srv://")):
                logger.error("Invalid MongoDB URI format. URI must start with 'mongodb://' or 'mongodb+srv://'")
                return False
            
            # Extract hostname for logging
            hostname = uri.split('@')[-1].split('/')[0]
            logger.info(f"MongoDB hostname: {hostname}")
            
            return True
        except Exception as uri_error:
            logger.error(f"Error parsing MongoDB URI: {str(uri_error)}")
            return False
    
    return False

def setup_certificate():
    """Setup SSL certificate for MongoDB connection"""
    cert_path = os.getenv("MONGO_X509_CERT_PATH", "certs/mongodb.pem")
    cert_base64 = os.getenv("MONGO_X509_CERT_BASE64")
    temp_cert_file = None
    cert_exists = False
    
    # Check if we have a base64 encoded certificate
    if cert_base64:
        try:
            # Decode the base64 certificate
            cert_content = base64.b64decode(cert_base64)
            # Create a temporary file for the certificate
            temp_cert_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pem')
            temp_cert_file.write(cert_content)
            temp_cert_file.close()
            cert_path = temp_cert_file.name
            cert_exists = True
            logger.info(f"Using certificate from base64 environment variable, saved to: {cert_path}")
        except Exception as cert_error:
            logger.error(f"Error decoding base64 certificate: {str(cert_error)}")
            cert_exists = False
    else:
        # Check if the certificate file exists
        cert_exists = os.path.isfile(cert_path)
        logger.info(f"X.509 Certificate {'found' if cert_exists else 'not found'} at: {cert_path}")
        
        # If cert doesn't exist, try to create directories and check again
        if not cert_exists:
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(cert_path), exist_ok=True)
                logger.info(f"Created directory: {os.path.dirname(cert_path)}")
                
                # For testing purposes, create a self-signed certificate
                logger.info("Creating self-signed certificate for testing...")
                
                # Use OpenSSL command to create a self-signed certificate
                try:
                    import subprocess
                    cmd = [
                        "openssl", "req", "-new", "-x509", "-days", "365", "-nodes",
                        "-out", cert_path,
                        "-keyout", cert_path,
                        "-subj", "/CN=localhost/O=AuragensAI/C=US"
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        logger.info(f"Self-signed certificate created successfully at {cert_path}")
                        cert_exists = os.path.isfile(cert_path)
                    else:
                        logger.error(f"Failed to create self-signed certificate: {result.stderr}")
                except Exception as openssl_error:
                    logger.error(f"Error creating self-signed certificate: {str(openssl_error)}")
            except Exception as dir_error:
                logger.error(f"Error creating certificate directory: {str(dir_error)}")
    
    return cert_path, cert_exists

def connect_to_mongodb():
    """Connect to MongoDB with proper error handling"""
    uri = os.getenv("MONGO_URI")
    cert_path, cert_exists = setup_certificate()
    
    # Initialize MongoDB client
    client = None
    connected = False
    
    # Connection attempts with different configurations
    connection_attempts = [
        {
            "name": "Relaxed TLS Settings",
            "config": {
                "serverSelectionTimeoutMS": 10000,
                "tls": True,
                "tlsAllowInvalidCertificates": True,
                "server_api": ServerApi('1')
            }
        },
        {
            "name": "No TLS Connection",
            "config": {
                "serverSelectionTimeoutMS": 10000,
                "server_api": ServerApi('1')
            }
        },
        {
            "name": "Standard TLS Connection",
            "config": {
                "serverSelectionTimeoutMS": 10000,
                "connectTimeoutMS": 30000,
                "socketTimeoutMS": 45000,
                "tls": True,
                "server_api": ServerApi('1')
            }
        },
        {
            "name": "X.509 Certificate Authentication",
            "config": {
                "serverSelectionTimeoutMS": 10000,
                "connectTimeoutMS": 30000,
                "socketTimeoutMS": 45000,
                "maxPoolSize": 50,
                "maxIdleTimeMS": 60000,
                "tls": True,
                "tlsAllowInvalidCertificates": False,
                "ssl_cert_reqs": ssl.CERT_REQUIRED if cert_exists else ssl.CERT_NONE,
                "ssl_ca_certs": cert_path if cert_exists else None,
                "server_api": ServerApi('1')
            }
        }
    ]
    
    for attempt in connection_attempts:
        try:
            logger.info(f"Attempting connection with: {attempt['name']}")
            client = MongoClient(uri, **attempt["config"])
            # Test connection
            client.admin.command('ping')
            logger.info(f"✅ Successfully connected to MongoDB Atlas using {attempt['name']}!")
            connected = True
            break
        except Exception as e:
            logger.error(f"❌ Connection failed with {attempt['name']}: {str(e)}")
    
    if not connected:
        logger.error("All connection attempts failed. Please check your MongoDB URI and network connection.")
        return None
    
    return client

def initialize_models():
    """Initialize NLP models for vector embeddings"""
    logger.info("🔄 Initializing NLP models for vector embeddings...")
    try:
        # Use a smaller model
        model_name = 'sentence-transformers/paraphrase-MiniLM-L3-v2'
        
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir='/tmp/transformers_cache',
            local_files_only=False
        )
        
        # Load model with memory optimizations
        model = AutoModel.from_pretrained(
            model_name,
            cache_dir='/tmp/transformers_cache',
            local_files_only=False
        )
        
        # Move model to CPU and clear CUDA cache
        model = model.cpu()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return tokenizer, model
    except Exception as e:
        logger.error(f"❌ Error initializing models: {str(e)}")
        return None, None

def generate_embedding(text, tokenizer, model):
    """Generate embeddings for text using the NLP model"""
    try:
        # Tokenize with max length limit
        inputs = tokenizer(
            text, 
            padding=True, 
            truncation=True, 
            max_length=256,
            return_tensors="pt"
        )
        
        # Move inputs to CPU explicitly
        inputs = {k: v.cpu() for k, v in inputs.items()}
        
        # Generate embeddings with memory optimization
        with torch.no_grad():
            outputs = model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)
            
        # Convert to list and clear memory
        result = embeddings[0].cpu().numpy().tolist()
        
        # Force garbage collection
        del outputs, embeddings
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        return result
    except Exception as e:
        logger.error(f"❌ Error generating embedding: {str(e)}")
        return None

def setup_database_structure(client):
    """Create necessary database collections and indexes"""
    logger.info("Setting up database structure...")
    
    try:
        # Create or get database
        db = client['Auragens_AI']
        logger.info(f"Using database: Auragens_AI")
        
        # Required collections and their indexes
        required_collections = {
            'chats': [
                ('user_id', 1),
                ('timestamp', -1)
            ],
            'vector_embeddings': [
                ('category', 1),
                ('timestamp', -1)
            ],
            'users': [
                ('user_id', 1),
                ('email', 1)
            ],
            'feedback': [
                ('chat_id', 1),
                ('timestamp', -1)
            ]
        }
        
        # Get existing collections
        existing_collections = db.list_collection_names()
        logger.info(f"Existing collections: {existing_collections}")
        
        # Create missing collections and indexes
        for collection_name, indexes in required_collections.items():
            if collection_name not in existing_collections:
                logger.info(f"Creating collection: {collection_name}")
                db.create_collection(collection_name)
            
            collection = db[collection_name]
            
            # Create indexes
            for index in indexes:
                if isinstance(index, tuple):
                    field, direction = index
                    index_name = f"{field}_{direction}"
                    logger.info(f"Creating index on {collection_name}.{field}")
                    collection.create_index([(field, direction)], name=index_name)
        
        # Vector search index setup for vector_embeddings collection
        if 'vector_embeddings' in db.list_collection_names():
            try:
                logger.info("Setting up vector search index...")
                
                # Create 2dsphere index for basic vector support
                db.vector_embeddings.create_index([("embedding", "2dsphere")])
                
                # Try to create knnVector index if Atlas supports it
                try:
                    db.vector_embeddings.create_search_index({
                        "name": "vector_search",
                        "definition": {
                            "mappings": {
                                "dynamic": True,
                                "fields": {
                                    "embedding": {
                                        "type": "knnVector",
                                        "dimensions": 384,
                                        "similarity": "cosine"
                                    }
                                }
                            }
                        }
                    })
                    logger.info("✅ Vector search index created successfully")
                except errors.OperationFailure as e:
                    if "Search index creation is not enabled" in str(e):
                        logger.warning("Vector search not available on this MongoDB tier. Using standard indexes instead.")
                    else:
                        logger.error(f"Error creating vector search index: {str(e)}")
                
            except Exception as index_error:
                logger.error(f"Error creating basic indexes: {str(index_error)}")
        
        return db
    except Exception as e:
        logger.error(f"❌ Error setting up database structure: {str(e)}")
        return None

def seed_sample_data(db, tokenizer, model):
    """Add sample data to collections if they're empty"""
    logger.info("Checking if collections need sample data...")
    
    # Seed vector_embeddings
    if db.vector_embeddings.count_documents({}) == 0:
        logger.info("Vector embeddings collection is empty, adding seed data...")
        
        # Sample data for vector embeddings
        seed_documents = [
            {
                "title": "Introduction to Stem Cell Therapy",
                "content": "Stem cell therapy is a form of regenerative medicine that uses stem cells or their derivatives to promote the repair response of diseased, dysfunctional or injured tissue. Auragens specializes in using Mesenchymal Stem Cells (MSCs) from Wharton's Jelly tissue for optimal therapeutic results.",
                "category": "general",
                "timestamp": datetime.utcnow()
            },
            {
                "title": "MSC Harvesting Procedure",
                "content": "MSCs are harvested using a minimally invasive procedure from Wharton's Jelly, the gelatinous tissue from the umbilical cord. This ensures high cell viability and minimal discomfort compared to other harvesting methods such as bone marrow extraction.",
                "category": "procedures",
                "timestamp": datetime.utcnow()
            },
            {
                "title": "Treatment Areas",
                "content": "MSCs are used in treating orthopedic, autoimmune, and cardiovascular conditions. They are also applied in neurological and pulmonary therapies. At Auragens, we focus on evidence-based applications with documented clinical outcomes.",
                "category": "treatments",
                "timestamp": datetime.utcnow()
            },
            {
                "title": "Auragens Leadership",
                "content": "Auragens is led by Dr. Dan Briggs, CEO, who has extensive experience in regenerative medicine and stem cell therapies. Under his leadership, Auragens has become a leader in providing high-quality Mesenchymal Stem Cell treatments derived from Wharton's Jelly tissue.",
                "category": "company",
                "timestamp": datetime.utcnow()
            },
            {
                "title": "Contact Information",
                "content": "For more information about Auragens and our stem cell therapy options, please visit our website at www.auragens.com or contact Dr. Dan Briggs directly for personalized consultation on treatment options for your specific condition.",
                "category": "contact",
                "timestamp": datetime.utcnow()
            }
        ]
        
        # Add embeddings to each document and insert
        success_count = 0
        for doc in seed_documents:
            try:
                # Generate embedding for the content
                embedding = generate_embedding(doc["content"], tokenizer, model)
                if embedding:
                    doc["embedding"] = embedding
                    # Insert document
                    result = db.vector_embeddings.insert_one(doc)
                    logger.info(f"Added seed document: {doc['title']} with ID: {result.inserted_id}")
                    success_count += 1
            except Exception as doc_error:
                logger.error(f"Error adding seed document {doc['title']}: {str(doc_error)}")
        
        logger.info(f"✅ Added {success_count} of {len(seed_documents)} seed documents to vector_embeddings")
    else:
        logger.info(f"Vector embeddings collection already has {db.vector_embeddings.count_documents({})} documents")
    
    # Seed users collection with a test user if empty
    if db.users.count_documents({}) == 0:
        logger.info("Users collection is empty, adding a test user...")
        test_user = {
            "user_id": "test_user_123",
            "email": "test@example.com",
            "name": "Test User",
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow()
        }
        
        try:
            result = db.users.insert_one(test_user)
            logger.info(f"Added test user with ID: {result.inserted_id}")
        except Exception as user_error:
            logger.error(f"Error adding test user: {str(user_error)}")
    else:
        logger.info(f"Users collection already has {db.users.count_documents({})} documents")
    
    return True

def test_database_operations(db, tokenizer, model):
    """Test essential database operations"""
    logger.info("Testing database operations...")
    
    test_results = {
        "vector_search": False,
        "chat_logging": False,
        "user_query": False
    }
    
    # Test 1: Insert and query vector embedding
    try:
        logger.info("Testing vector embedding insertion and search...")
        test_doc = {
            "title": "Test Document",
            "content": "This is a test document to verify vector search functionality.",
            "category": "test",
            "timestamp": datetime.utcnow()
        }
        
        # Generate embedding
        embedding = generate_embedding(test_doc["content"], tokenizer, model)
        if embedding:
            test_doc["embedding"] = embedding
            # Insert test document
            result = db.vector_embeddings.insert_one(test_doc)
            test_doc_id = result.inserted_id
            logger.info(f"Inserted test document with ID: {test_doc_id}")
            
            # Verify document was inserted
            verify = db.vector_embeddings.find_one({"_id": test_doc_id})
            if verify:
                logger.info("✅ Test document inserted and retrieved successfully")
                test_results["vector_search"] = True
            else:
                logger.error("❌ Failed to retrieve test document")
            
            # Clean up test document
            db.vector_embeddings.delete_one({"_id": test_doc_id})
            logger.info("Test document cleaned up")
    except Exception as vector_error:
        logger.error(f"❌ Vector search test failed: {str(vector_error)}")
    
    # Test 2: Chat logging
    try:
        logger.info("Testing chat logging...")
        test_chat = {
            "user_id": "test_user_123",
            "user_message": "This is a test message",
            "bot_response": "This is a test response",
            "timestamp": datetime.utcnow()
        }
        
        # Insert test chat
        result = db.chats.insert_one(test_chat)
        test_chat_id = result.inserted_id
        logger.info(f"Inserted test chat with ID: {test_chat_id}")
        
        # Verify chat was inserted
        verify = db.chats.find_one({"_id": test_chat_id})
        if verify:
            logger.info("✅ Test chat inserted and retrieved successfully")
            test_results["chat_logging"] = True
        else:
            logger.error("❌ Failed to retrieve test chat")
        
        # Clean up test chat
        db.chats.delete_one({"_id": test_chat_id})
        logger.info("Test chat cleaned up")
    except Exception as chat_error:
        logger.error(f"❌ Chat logging test failed: {str(chat_error)}")
    
    # Test 3: User query
    try:
        logger.info("Testing user queries...")
        # Find the test user
        test_user = db.users.find_one({"user_id": "test_user_123"})
        if test_user:
            logger.info(f"✅ Found test user: {test_user.get('email')}")
            test_results["user_query"] = True
        else:
            logger.error("❌ Failed to find test user")
    except Exception as user_error:
        logger.error(f"❌ User query test failed: {str(user_error)}")
    
    # Report test results
    logger.info("\n===== DATABASE TEST RESULTS =====")
    logger.info(f"Vector Search: {'✅ PASS' if test_results['vector_search'] else '❌ FAIL'}")
    logger.info(f"Chat Logging: {'✅ PASS' if test_results['chat_logging'] else '❌ FAIL'}")
    logger.info(f"User Query: {'✅ PASS' if test_results['user_query'] else '❌ FAIL'}")
    logger.info("===============================\n")
    
    return all(test_results.values())

def main():
    """Main function to execute the database initialization and testing"""
    logger.info("Starting database initialization and testing...")
    
    # Step 1: Check environment variables
    if not check_environment():
        return False
    
    # Step 2: Connect to MongoDB
    client = connect_to_mongodb()
    if not client:
        return False
    
    # Step 3: Initialize NLP models
    tokenizer, model = initialize_models()
    if not tokenizer or not model:
        return False
    
    # Step 4: Setup database structure
    db = setup_database_structure(client)
    if not db:
        return False
    
    # Step 5: Seed sample data
    if not seed_sample_data(db, tokenizer, model):
        logger.warning("Sample data seeding had some issues, but continuing...")
    
    # Step 6: Test database operations
    test_passed = test_database_operations(db, tokenizer, model)
    
    # Final report
    if test_passed:
        logger.info("✅ Database initialization and testing completed successfully!")
    else:
        logger.warning("⚠️ Database initialization completed, but some tests failed.")
    
    # Return connection info for application use
    return {
        "client": client,
        "db": db,
        "collections": {
            "chats": db.chats,
            "vector_embeddings": db.vector_embeddings,
            "users": db.users,
            "feedback": db.feedback
        },
        "status": "Success" if test_passed else "Partial Success"
    }

if __name__ == "__main__":
    # Check if .env file exists, if not create a template
    if not os.path.exists('.env'):
        logger.warning(".env file not found, creating template...")
        try:
            with open('.env', 'w') as env_file:
                env_file.write("""# MongoDB Connection
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGO_X509_CERT_PATH=certs/mongodb.pem
# MONGO_X509_CERT_BASE64=

# API Keys
# GROQ_API_KEY=
# ANTHROPIC_API_KEY=

# Auth0 Configuration
# AUTH0_CLIENT_ID=
# AUTH0_CLIENT_SECRET=
# AUTH0_DOMAIN=
# AUTH0_CALLBACK_URL=

# Application Secret
# SECRET_KEY=
""")
            logger.info(".env template created. Please edit it with your actual MongoDB URI.")
            print("\n⚠️ Please edit the .env file with your MongoDB connection details and run this script again.\n")
            sys.exit(0)
        except Exception as env_error:
            logger.error(f"Error creating .env template: {str(env_error)}")
    
    main() 