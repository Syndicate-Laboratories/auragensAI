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
cert_path = os.getenv("MONGO_X509_CERT_PATH", "certs/mongodb.pem")
cert_base64 = os.getenv("MONGO_X509_CERT_BASE64")
print(f"Loaded MongoDB URI: {uri[:30]}..." if uri else "MONGO_URI not found in environment variables")

if not uri:
    raise Exception("MONGO_URI environment variable not found - Please ensure it's set in .env or Heroku config vars")

# Initialize certificate path
temp_cert_file = None
cert_exists = False

# Check if we have a base64 encoded certificate (Heroku environment)
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
        print(f"Using certificate from base64 environment variable, saved to temporary file: {cert_path}")
    except Exception as cert_error:
        logger.error(f"Error decoding base64 certificate: {str(cert_error)}")
        cert_exists = False
else:
    # Check if the certificate file exists
    cert_exists = os.path.isfile(cert_path)
    print(f"X.509 Certificate {'found' if cert_exists else 'not found'} at: {cert_path}")

# Initialize MongoDB client with options and better error handling
db = None
chats = None
vector_embeddings = None
client = None

try:
    # Setup SSL context for X.509 authentication
    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    
    if cert_exists:
        # Configure SSL context with the certificate
        ssl_context.load_cert_chain(cert_path)
        logger.info(f"X.509 certificate loaded from {cert_path}")
    else:
        logger.warning(f"X.509 certificate not found at {cert_path}, falling back to default authentication")
    
    # Connect with proper error handling and timeout
    client = MongoClient(
        uri, 
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=30000,
        socketTimeoutMS=45000,
        maxPoolSize=50,
        maxIdleTimeMS=60000,
        tls=True,
        tlsAllowInvalidCertificates=False,
        ssl_cert_reqs=ssl.CERT_REQUIRED if cert_exists else ssl.CERT_NONE,
        ssl_ca_certs=cert_path if cert_exists else None,
        server_api=ServerApi('1')
    )
    
    # Test connection with timeout
    client.admin.command('ping')
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
    
    # Provide fallback connection method if X.509 auth fails
    try:
        logger.info("Attempting alternative connection method...")
        # Try without SSL context but with TLS
        client = MongoClient(
            uri, 
            serverSelectionTimeoutMS=10000,
            tls=True,
            tlsAllowInvalidCertificates=True,
            server_api=ServerApi('1')
        )
        client.admin.command('ping')
        logger.info("✅ Connected with alternative method!")
        
        # Initialize database and collections
        db = client['Auragens_AI']
        chats = db['chats']
        vector_embeddings = db['vector_embeddings']
    except Exception as alt_error:
        logger.error(f"❌ Alternative connection also failed: {str(alt_error)}")
        logger.error("Using dummy database functions that will log errors but not crash")
        
        # Create a dummy client class for graceful failure
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
        
        class DummyDB:
            def __getitem__(self, name):
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
    try:
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
    except Exception as e:
        logger.error(f"❌ Error creating vector search index: {str(e)}")

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
    try:
        logger.info(f"📝 Processing document: '{title}'")
        embedding = generate_embedding(content)
        
        document = {
            "title": title,
            "content": content,
            "category": category,
            "embedding": embedding,
            "timestamp": datetime.utcnow()
        }
        
        result = vector_embeddings.insert_one(document)
        duration = time() - start_time
        
        logger.info(f"""
✅ Document inserted successfully:
   - ID: {result.inserted_id}
   - Title: {title}
   - Category: {category}
   - Processing time: {duration:.3f}s
   - Embedding size: {len(embedding)}
""")
        return True
        
    except Exception as e:
        logger.error(f"""
❌ Document insertion failed:
   - Title: {title}
   - Error: {str(e)}
   - Duration: {time() - start_time:.3f}s
""")
        return False 