#!/usr/bin/env python
"""
MongoDB Database Initialization Script
This script initializes the MongoDB database with required collections and indexes.
It also seeds some initial data for the vector database.
"""

import os
import sys
import logging
from pymongo import MongoClient, errors
from pymongo.server_api import ServerApi
from datetime import datetime
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModel
import torch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("init_database")

# Load environment variables
load_dotenv(override=True)

def get_mongodb_connection():
    """Establish connection to MongoDB using X.509 certificate"""
    # Get MongoDB URI from environment
    uri = os.getenv("MONGO_URI")
    if not uri:
        uri = "mongodb+srv://auragensai.6zehw.mongodb.net/?authSource=%24external&authMechanism=MONGODB-X509&retryWrites=true&w=majority&appName=AuragensAI"
        logger.info("Using default MongoDB URI")
    
    # Look for specific X.509 certificate
    x509_cert_path = "certs/X509-cert-4832015629630048359.pem"
    if os.path.isfile(x509_cert_path):
        cert_path = x509_cert_path
        logger.info(f"Using specific X.509 certificate: {cert_path}")
    else:
        cert_path = os.getenv("MONGO_X509_CERT_PATH", "certs/mongodb.pem")
        logger.info(f"Using certificate path from environment: {cert_path}")
    
    cert_exists = os.path.isfile(cert_path)
    logger.info(f"X.509 Certificate {'found' if cert_exists else 'not found'} at: {cert_path}")
    
    if not cert_exists:
        logger.error("No valid certificate found. Cannot connect to MongoDB.")
        return None
    
    try:
        # Connect with X.509 certificate
        logger.info(f"Connecting to MongoDB: {uri[:50]}...")
        client = MongoClient(
            uri,
            tls=True,
            tlsCertificateKeyFile=cert_path,
            server_api=ServerApi('1')
        )
        
        # Test connection
        client.admin.command('ping')
        logger.info("✅ Successfully connected to MongoDB!")
        return client
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {str(e)}")
        return None

def initialize_models():
    """Initialize NLP models for embeddings"""
    logger.info("Loading NLP models for embeddings...")
    try:
        # Load models
        model_name = 'sentence-transformers/paraphrase-MiniLM-L3-v2'
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        logger.info(f"✅ Successfully loaded models: {model_name}")
        return tokenizer, model
    except Exception as e:
        logger.error(f"❌ Failed to load NLP models: {str(e)}")
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
        
        # Generate embeddings
        with torch.no_grad():
            outputs = model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)
            
        # Convert to list
        result = embeddings[0].numpy().tolist()
        return result
    except Exception as e:
        logger.error(f"❌ Error generating embedding: {str(e)}")
        return None

def setup_database_structure(client):
    """Create necessary collections and indexes"""
    if not client:
        return False
    
    logger.info("Setting up database structure...")
    try:
        # Get or create database
        db = client['Auragens_AI']
        
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
                ('user_id', 1, True),  # Unique index
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
                if len(index) == 2:
                    field, direction = index
                    unique = False
                else:
                    field, direction, unique = index
                
                logger.info(f"Creating index on {collection_name}.{field} (unique={unique})")
                collection.create_index([(field, direction)], unique=unique)
        
        # Try to create vector search index for vector_embeddings
        try:
            logger.info("Setting up vector search index...")
            db.vector_embeddings.create_index([("embedding", "2dsphere")])
            
            # Try creating a MongoDB Atlas Search index if available
            try:
                # Check if index already exists
                existing_indexes = list(db.vector_embeddings.list_indexes())
                has_search_index = any("vector_search" in idx.get('name', '') for idx in existing_indexes)
                
                if not has_search_index:
                    db.vector_embeddings.create_search_index(
                        {
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
                        }
                    )
                    logger.info("✅ Vector search index created successfully")
            except errors.OperationFailure as e:
                if "Search index creation is not enabled" in str(e):
                    logger.warning("Vector search not available on this MongoDB tier. Using standard indexes.")
                else:
                    logger.error(f"Error creating vector search index: {str(e)}")
            
        except Exception as index_error:
            logger.error(f"Error creating basic indexes: {str(index_error)}")
        
        return db
    except Exception as e:
        logger.error(f"❌ Error setting up database structure: {str(e)}")
        return None

def seed_initial_data(db, tokenizer, model):
    """Add initial data to collections if they're empty"""
    if not db or not tokenizer or not model:
        return False
    
    logger.info("Checking if collections need initial data...")
    
    # Check if vector_embeddings is empty
    if db.vector_embeddings.count_documents({}) == 0:
        logger.info("Vector embeddings collection is empty, adding initial data...")
        
        # Sample data for vector embeddings
        sample_data = [
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
        
        # Add embeddings and insert documents
        success_count = 0
        for doc in sample_data:
            try:
                # Generate embedding
                embedding = generate_embedding(doc["content"], tokenizer, model)
                if embedding:
                    doc["embedding"] = embedding
                    # Insert document
                    result = db.vector_embeddings.insert_one(doc)
                    logger.info(f"Added document: {doc['title']} with ID: {result.inserted_id}")
                    success_count += 1
            except Exception as e:
                logger.error(f"Error adding document {doc['title']}: {str(e)}")
        
        logger.info(f"✅ Added {success_count} of {len(sample_data)} documents to vector_embeddings")
    else:
        logger.info(f"Vector embeddings collection already has {db.vector_embeddings.count_documents({})} documents")
    
    # Check if users collection is empty
    if db.users.count_documents({}) == 0:
        logger.info("Users collection is empty, adding a test user...")
        
        # Add test user
        test_user = {
            "user_id": "test_user_123",
            "email": "test@example.com",
            "name": "Test User",
            "created_at": datetime.utcnow()
        }
        
        try:
            result = db.users.insert_one(test_user)
            logger.info(f"Added test user with ID: {result.inserted_id}")
        except Exception as e:
            logger.error(f"Error adding test user: {str(e)}")
    else:
        logger.info(f"Users collection already has {db.users.count_documents({})} users")
    
    return True

def main():
    logger.info("=== MongoDB Database Initialization Script ===")
    
    # Connect to MongoDB
    client = get_mongodb_connection()
    if not client:
        logger.error("Failed to connect to MongoDB. Database initialization aborted.")
        return False
    
    # Initialize NLP models for embeddings
    tokenizer, model = initialize_models()
    if not tokenizer or not model:
        logger.warning("Failed to initialize NLP models. Continuing without embeddings.")
    
    # Set up database structure
    db = setup_database_structure(client)
    if not db:
        logger.error("Failed to set up database structure.")
        return False
    
    # Seed initial data
    if tokenizer and model:
        if not seed_initial_data(db, tokenizer, model):
            logger.warning("Failed to seed initial data.")
    
    # Print database status
    logger.info("\n=== Database Status ===")
    collections = db.list_collection_names()
    logger.info(f"Collections: {collections}")
    
    for collection_name in collections:
        count = db[collection_name].count_documents({})
        logger.info(f"Collection '{collection_name}' has {count} documents")
    
    logger.info("✅ Database initialization completed!")
    return True

if __name__ == "__main__":
    if main():
        logger.info("MongoDB database initialization successful. Application is ready to use.")
    else:
        logger.error("MongoDB database initialization failed. Please check the logs for details.") 