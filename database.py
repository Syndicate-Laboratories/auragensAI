from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv
from datetime import datetime
from bson import ObjectId
from transformers import AutoTokenizer, AutoModel
import torch
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging
import gc  # For garbage collection
from time import time
from typing import List, Dict, Any
import ssl
import base64
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv(override=True)

# Debug: Print current working directory and env vars
print(f"Current working directory: {os.getcwd()}")
print(f"Environment variables available: {', '.join([k for k in os.environ.keys() if not k.startswith('_')])}")

# Get MongoDB URI and X.509 certificate from environment variables
uri = os.getenv("MONGO_URI")
if not uri:
    uri = "mongodb+srv://auragensai.6zehw.mongodb.net/?authSource=%24external&authMechanism=MONGODB-X509&retryWrites=true&w=majority&appName=AuragensAI"
    print("Using default MongoDB URI")

# Handle X.509 certificates with better error handling for Heroku environment
cert_path = None
cert_exists = False
temp_cert_file = None

# First check for base64 encoded certificate (Heroku environment)
cert_base64 = os.getenv("MONGO_X509_CERT_BASE64")
if cert_base64:
    try:
        # Decode the base64 certificate
        logger.info("Found MONGO_X509_CERT_BASE64 environment variable, creating temporary certificate file")
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

# If no base64 cert, try specific file cert
if not cert_exists:
    # Check for the specific X.509 certificate
    x509_cert_path = "certs/X509-cert-4832015629630048359.pem"
    if os.path.isfile(x509_cert_path):
        cert_path = x509_cert_path
        print(f"Using specific X.509 certificate: {cert_path}")
        cert_exists = True
    else:
        # Fall back to generic certificate path
        cert_path = os.getenv("MONGO_X509_CERT_PATH", "certs/mongodb.pem")
        print(f"Using certificate path from environment: {cert_path}")
        cert_exists = os.path.isfile(cert_path)

# Log connection parameters for debugging
print(f"X.509 Certificate {'found' if cert_exists else 'not found'} at: {cert_path}")
print(f"Loaded MongoDB URI: {uri[:30]}..." if uri else "MONGO_URI not found in environment variables")

if not uri:
    raise Exception("MONGO_URI environment variable not found - Please ensure it's set in .env or Heroku config vars")

# Initialize MongoDB client with options and better error handling
db = None
chats = None
vector_embeddings = None
client = None

try:
    # Log connection attempt details
    logger.info(f"MongoDB connection attempt - URI: {uri[:30]}... Certificate exists: {cert_exists}, Path: {cert_path}")
    
    # First attempt connection using X.509 certificate directly
    try:
        logger.info("Attempting connection with X.509 certificate...")
        client = MongoClient(
            uri,
            tls=True,
            tlsCertificateKeyFile=cert_path if cert_exists else None,
            server_api=ServerApi('1')
        )
        # Test connection with timeout
        client.admin.command('ping')
        logger.info("✅ Successfully connected to MongoDB with X.509 certificate!")
    except Exception as x509_error:
        logger.error(f"❌ MongoDB connection error with X.509 certificate: {str(x509_error)}")
        
        # Try with relaxed TLS settings
        try:
            logger.info("Attempting connection with relaxed TLS settings...")
            client = MongoClient(
                uri, 
                serverSelectionTimeoutMS=10000,
                tls=True,
                tlsAllowInvalidCertificates=True,
                server_api=ServerApi('1')
            )
            client.admin.command('ping')
            logger.info("✅ Connected with relaxed TLS settings!")
        except Exception as relaxed_error:
            logger.error(f"❌ Relaxed TLS connection failed: {str(relaxed_error)}")
            
            # Final fallback attempt with minimal settings
            logger.info("Attempting final fallback connection...")
            client = MongoClient(
                uri, 
                serverSelectionTimeoutMS=10000,
                tls=True,
                server_api=ServerApi('1')
            )
            client.admin.command('ping')
            logger.info("✅ Connected with fallback method!")
    
    print("✅ Successfully connected to MongoDB Atlas!")
    
    # Initialize database and collections
    db = client['Auragens_AI']
    chats = db['chats']
    vector_embeddings = db['vector_embeddings']
    
    # Create index for semantic search with error handling
    try:
        logger.info("Setting up vector search index...")
        vector_embeddings.create_index([("embedding", "2dsphere")])
        logger.info("✅ Vector search index created successfully")
    except Exception as index_error:
        logger.error(f"Error creating search index: {str(index_error)}")
        
except Exception as e:
    logger.error(f"❌ MongoDB connection error: {str(e)}")
    logger.error("Using dummy database functions that will log errors but not crash")
    
    # Create dummy classes for graceful failure
    class DummyCollection:
        def __init__(self, name):
            self.name = name
        
        def insert_one(self, *args, **kwargs):
            logger.error(f"Attempted insert to {self.name} but database is unavailable")
            return type('obj', (object,), {'inserted_id': None})
        
        def find(self, *args, **kwargs):
            logger.error(f"Attempted find on {self.name} but database is unavailable")
            return []
        
        def find_one(self, *args, **kwargs):
            logger.error(f"Attempted find_one on {self.name} but database is unavailable")
            return None
        
        def create_index(self, *args, **kwargs):
            logger.error(f"Attempted create_index on {self.name} but database is unavailable")
        
        def create_search_index(self, *args, **kwargs):
            logger.error(f"Attempted create_search_index on {self.name} but database is unavailable")
        
        def aggregate(self, *args, **kwargs):
            logger.error(f"Attempted aggregate on {self.name} but database is unavailable")
            return []
        
        def count_documents(self, *args, **kwargs):
            logger.error(f"Attempted count_documents on {self.name} but database is unavailable")
            return 0
    
    class DummyDB:
        def __init__(self):
            self.name = "dummy_db"
        
        def __getitem__(self, name):
            return DummyCollection(name)
        
        def list_collection_names(self):
            logger.error("Attempted to list collections but database is unavailable")
            return []
        
        def create_collection(self, name):
            logger.error(f"Attempted to create collection {name} but database is unavailable")
            return DummyCollection(name)
    
    class DummyClient:
        def __init__(self):
            self.admin = self
        
        def command(self, *args, **kwargs):
            logger.error("Attempted database command but database is unavailable")
        
        def __getitem__(self, name):
            return DummyDB()
    
    client = DummyClient()
    db = DummyDB()
    chats = DummyCollection('chats')
    vector_embeddings = DummyCollection('vector_embeddings')

# Set environment variables for better memory management
os.environ['TRANSFORMERS_CACHE'] = '/tmp/transformers_cache'
os.environ['TORCH_CUDA_ARCH_LIST'] = '3.5;5.0;6.0;7.0;7.5'  # Optimize CUDA architectures
os.environ['HF_HOME'] = '/tmp/huggingface'

# Initialize model with better memory handling
def initialize_models():
    logger.info("🔄 Initializing NLP models...")
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
        raise

# Initialize at startup with error handling
try:
    tokenizer, model = initialize_models()
    logger.info("✅ NLP models initialized successfully")
except Exception as model_error:
    logger.error(f"Failed to initialize NLP models: {str(model_error)}")
    # Create dummy tokenizer and model for graceful degradation
    tokenizer = None
    model = None

def save_chat(user_id, user_message, bot_response):
    try:
        # Verify connection before saving
        logger.info(f"Attempting to save chat for user: {user_id[:5]}...")
        client.admin.command('ping')
        
        chat = {
            'user_id': user_id,
            'user_message': user_message,
            'bot_response': bot_response[:100] + "..." if len(bot_response) > 100 else bot_response,  # Truncate for logging
            'timestamp': datetime.utcnow()
        }
        
        logger.info(f"Inserting chat document into MongoDB: {chat['user_message'][:50]}...")
        result = chats.insert_one(chat)
        
        if result and result.inserted_id:
            logger.info(f"✅ Chat saved successfully with ID: {result.inserted_id}")
            return result.inserted_id
        else:
            logger.warning("⚠️ No insert_id returned, but no error thrown")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error saving chat: {str(e)}")
        logger.info("Attempting to reconnect and retry...")
        try:
            # Try to reconnect
            if isinstance(client, MongoClient):
                client.admin.command('ping')
                logger.info("Reconnected to MongoDB successfully")
                result = chats.insert_one(chat)
                logger.info(f"✅ Chat saved successfully after retry with ID: {result.inserted_id}")
                return result.inserted_id
        except Exception as retry_error:
            logger.error(f"❌ Retry failed: {str(retry_error)}")
        return None

def get_user_chats(user_id):
    try:
        return list(chats.find({'user_id': user_id}).sort('timestamp', -1))
    except Exception as e:
        print(f"Error retrieving chats: {str(e)}")
        return []

def get_chat_by_id(chat_id):
    try:
        return chats.find_one({'_id': ObjectId(chat_id)})
    except Exception as e:
        print(f"Error retrieving chat: {str(e)}")
        return None

# Function to generate embeddings
def generate_embedding(text):
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
        raise

# Add monitoring class
class SearchMetrics:
    def __init__(self):
        self.total_searches = 0
        self.total_time = 0
        self.successful_searches = 0
        self.failed_searches = 0
        
    def log_search(self, duration: float, success: bool, results_count: int):
        self.total_searches += 1
        self.total_time += duration
        if success:
            self.successful_searches += 1
        else:
            self.failed_searches += 1
        
        logger.info(f"""
🔍 Search Metrics:
   - Duration: {duration:.3f}s
   - Results found: {results_count}
   - Success rate: {(self.successful_searches/self.total_searches)*100:.1f}%
   - Avg response time: {(self.total_time/self.total_searches)*1000:.2f}ms
""")

# Initialize metrics
search_metrics = SearchMetrics()

def setup_vector_search():
    """Set up or update the vector search index"""
    try:
        if not vector_embeddings:
            logger.error("Vector embeddings collection not available")
            return False
            
        logger.info("Setting up vector search index...")
        vector_embeddings.create_search_index({
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
        })
        logger.info("✅ Vector search index created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error creating vector search index: {str(e)}")
        return False

def semantic_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    start_time = time()
    try:
        logger.info(f"🔄 Processing search query: '{query[:50]}...'")
        query_embedding = generate_embedding(query)
        
        results = vector_embeddings.aggregate([
            {
                "$search": {
                    "index": "default",
                    "knnBeta": {
                        "vector": query_embedding,
                        "path": "embedding",
                        "k": limit
                    }
                }
            },
            {
                "$project": {
                    "title": 1,
                    "content": 1,
                    "category": 1,
                    "score": { "$meta": "searchScore" }
                }
            }
        ])
        
        results_list = list(results)
        duration = time() - start_time
        
        # Log detailed results
        if results_list:
            scores = [doc.get('score', 0) for doc in results_list]
            logger.info(f"""
📊 Search Results:
   - Query: '{query[:50]}...'
   - Found: {len(results_list)} documents
   - Top score: {max(scores):.3f}
   - Avg score: {sum(scores)/len(scores):.3f}
   - Categories: {set(doc.get('category') for doc in results_list)}
""")
        
        search_metrics.log_search(duration, True, len(results_list))
        return results_list
        
    except Exception as e:
        duration = time() - start_time
        logger.error(f"❌ Search failed: {str(e)}")
        search_metrics.log_search(duration, False, 0)
        return []

def insert_document_with_embedding(title: str, content: str, category: str) -> bool:
    start_time = time()
    
    if not isinstance(title, str) or not title.strip():
        logger.error("❌ Document insertion failed: Title is required")
        return False
    
    if not isinstance(content, str) or len(content) < 50:
        logger.error("❌ Document insertion failed: Content must be at least 50 characters")
        return False
    
    if not isinstance(category, str) or not category.strip():
        logger.error("❌ Document insertion failed: Category is required")
        return False
    
    # Verify database connection before continuing
    try:
        if isinstance(vector_embeddings, type(None)) or not client:
            logger.error("❌ Document insertion failed: Database connection not available")
            return False
            
        # Verify we can reach the database
        client.admin.command('ping')
        logger.info("✅ Database connection verified before document insertion")
    except Exception as conn_error:
        logger.error(f"❌ Database connection failed before document insertion: {str(conn_error)}")
        return False
    
    try:
        logger.info(f"📝 Processing document for vector database: '{title}'")
        
        # Generate embedding with timing
        embed_start = time()
        embedding = generate_embedding(content)
        embed_time = time() - embed_start
        
        if not embedding:
            logger.error("❌ Failed to generate embedding for document")
            return False
            
        logger.info(f"✅ Generated embedding in {embed_time:.3f}s | Size: {len(embedding)}")
        
        document = {
            "title": title,
            "content": content,
            "category": category,
            "embedding": embedding,
            "timestamp": datetime.utcnow()
        }
        
        # Insert document with timing
        insert_start = time()
        result = vector_embeddings.insert_one(document)
        insert_time = time() - insert_start
        total_time = time() - start_time
        
        if result and result.inserted_id:
            logger.info(f"""
✅ Document inserted successfully:
   - ID: {result.inserted_id}
   - Title: {title}
   - Category: {category}
   - Total processing time: {total_time:.3f}s
   - Embedding generation: {embed_time:.3f}s
   - Database insertion: {insert_time:.3f}s
   - Embedding size: {len(embedding)}
""")
            return True
        else:
            logger.error(f"❌ Document insertion failed: No insert ID returned")
            return False
        
    except Exception as e:
        logger.error(f"""
❌ Document insertion failed:
   - Title: {title}
   - Error: {str(e)}
   - Error type: {type(e).__name__}
   - Duration: {time() - start_time:.3f}s
""")
        # Log stack trace for debugging
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False

# Initialize database and collections after successful connection
def initialize_database_structure():
    """Create necessary database collections and indexes if they don't exist"""
    if not isinstance(client, MongoClient):
        logger.error("Cannot initialize database structure: Invalid MongoDB client")
        return False
    
    try:
        logger.info("Checking and initializing MongoDB database structure...")
        
        # Get or create database
        db = client['Auragens_AI']
        
        # List of required collections with their indexes
        required_collections = {
            'chats': [
                ('user_id', 1),  # Index for user_id for faster lookups
                ('timestamp', -1)  # Index for timestamp, descending for recent first
            ],
            'vector_embeddings': [
                ('category', 1),  # Index for category field
                ('timestamp', -1),  # Index for timestamp
                [('embedding', '2dsphere')]  # Special index for vector search
            ],
            'users': [
                ('user_id', 1),  # Unique index for user_id
                ('email', 1)  # Index for email lookups
            ],
            'feedback': [
                ('chat_id', 1),  # Index for chat_id
                ('timestamp', -1)  # Index for timestamp
            ]
        }
        
        # Get existing collections
        existing_collections = db.list_collection_names()
        logger.info(f"Existing collections: {existing_collections}")
        
        # Create missing collections and indexes
        for collection_name, indexes in required_collections.items():
            # Create collection if it doesn't exist
            if collection_name not in existing_collections:
                logger.info(f"Creating collection: {collection_name}")
                db.create_collection(collection_name)
            
            collection = db[collection_name]
            
            # Create indexes
            for index in indexes:
                if isinstance(index, tuple):
                    field, direction = index
                    logger.info(f"Creating index on {collection_name}.{field}")
                    collection.create_index([(field, direction)])
                elif isinstance(index, list):
                    logger.info(f"Creating special index on {collection_name}: {index}")
                    collection.create_index(index)
        
        # Initialize vector search index if needed
        if 'vector_embeddings' in existing_collections:
            try:
                logger.info("Setting up vector search index...")
                db.vector_embeddings.create_search_index({
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
                })
                logger.info("✅ Vector search index created/updated successfully")
            except Exception as index_error:
                logger.error(f"Error setting up vector search index: {str(index_error)}")
        
        logger.info("✅ Database initialization completed successfully")
        return db
    except Exception as e:
        logger.error(f"❌ Error initializing database structure: {str(e)}")
        return None

# Call initialization after connection succeeds
if client:
    try:
        db = initialize_database_structure()
        if db:
            # Set up global references to collections
            chats = db['chats']
            vector_embeddings = db['vector_embeddings']
            logger.info("Database collections initialized and ready")
        else:
            logger.warning("Database initialization returned None, using dummy collections")
    except Exception as init_error:
        logger.error(f"Error during database initialization: {str(init_error)}")

# Function to seed database with initial data if empty
def seed_database_if_empty():
    """Add initial data to the database if collections are empty"""
    try:
        if not isinstance(db, type(None)):
            # Check if the vector_embeddings collection is empty
            if vector_embeddings.count_documents({}) == 0:
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
                for doc in seed_documents:
                    try:
                        # Generate embedding for the content
                        doc["embedding"] = generate_embedding(doc["content"])
                        # Insert document
                        result = vector_embeddings.insert_one(doc)
                        logger.info(f"Added seed document: {doc['title']} with ID: {result.inserted_id}")
                    except Exception as doc_error:
                        logger.error(f"Error adding seed document {doc['title']}: {str(doc_error)}")
                
                logger.info("✅ Seed data added successfully")
            else:
                logger.info("Vector embeddings collection already contains data, skipping seeding")
            
            return True
    except Exception as e:
        logger.error(f"❌ Error seeding database: {str(e)}")
        return False

# Call seeding function after initialization
if db and vector_embeddings:
    seed_database_if_empty() 