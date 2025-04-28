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
import psutil
import sys
import traceback
import platform
import pymongo

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

# Process certificate from base64 if provided
if os.environ.get("MONGO_X509_CERT_BASE64"):
    try:
        encoded_cert = os.environ.get("MONGO_X509_CERT_BASE64")
        # Print first and last few characters for debugging
        logger.info(f"Certificate B64 found in env. First 10 chars: {encoded_cert[:10]}..., Last 10: ...{encoded_cert[-10:] if len(encoded_cert) > 10 else encoded_cert}")
        
        # Try to decode the base64 string
        try:
            # Check if certificate appears to be base64 encoded
            if not all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in encoded_cert):
                logger.warning("⚠️ Certificate contains characters not in base64 alphabet - may need cleaning")
            
            # Try to decode, handling potential padding issues
            try:
                decoded_cert = base64.b64decode(encoded_cert)
            except Exception as padding_error:
                logger.warning(f"⚠️ Base64 decoding failed: {str(padding_error)}, trying to add padding...")
                # Try adding padding if missing
                padding = '=' * (4 - len(encoded_cert) % 4) if len(encoded_cert) % 4 != 0 else ''
                encoded_cert_padded = encoded_cert + padding
                decoded_cert = base64.b64decode(encoded_cert_padded)
                logger.info("✅ Successfully decoded certificate with added padding")
            
            # Check if it seems to be a valid certificate
            decoded_text = decoded_cert.decode('utf-8', errors='replace')
            if "BEGIN CERTIFICATE" not in decoded_text:
                logger.warning("⚠️ Decoded certificate doesn't contain BEGIN CERTIFICATE marker")
                # Log a sample of the decoded content to help diagnose
                logger.info(f"Decoded content sample: {decoded_text[:100]}...")
            else:
                logger.info("✅ Certificate appears to be in correct PEM format")
        except Exception as decode_error:
            logger.error(f"❌ Error decoding certificate: {str(decode_error)}")
            raise
        
        # Ensure certificate has proper line breaks
        if "-----BEGIN CERTIFICATE-----" in decoded_text and "\n" not in decoded_text:
            logger.info("⚠️ Certificate lacks proper line breaks, adding them...")
            # Add line breaks to properly format PEM certificate
            formatted_cert = decoded_text.replace("-----BEGIN CERTIFICATE-----", "-----BEGIN CERTIFICATE-----\n")
            formatted_cert = formatted_cert.replace("-----END CERTIFICATE-----", "\n-----END CERTIFICATE-----")
            # Insert a line break every 64 characters between the BEGIN and END markers
            middle_content = formatted_cert.split("-----BEGIN CERTIFICATE-----\n")[1].split("\n-----END CERTIFICATE-----")[0]
            formatted_middle = '\n'.join([middle_content[i:i+64] for i in range(0, len(middle_content), 64)])
            formatted_cert = "-----BEGIN CERTIFICATE-----\n" + formatted_middle + "\n-----END CERTIFICATE-----"
            decoded_text = formatted_cert
            logger.info("✅ Added proper line breaks to certificate")
        
        # Create cert directory if needed
        os.makedirs(os.path.dirname(cert_path), exist_ok=True)
        
        # Save to multiple locations for maximum compatibility
        cert_locations = [
            cert_path,
            "/tmp/mongodb-cert.pem",
            "mongodb-cert.pem",
            "./mongodb-cert.pem"
        ]
        
        for location in cert_locations:
            with open(location, 'w') as cert_file:
                cert_file.write(decoded_text)
            os.chmod(location, 0o600)
            logger.info(f"✅ Certificate saved to {location} with 0o600 permissions")
            
        # Verify content
        with open(cert_path, 'r') as verify_file:
            cert_content = verify_file.read()
            if "BEGIN CERTIFICATE" in cert_content and "END CERTIFICATE" in cert_content:
                logger.info(f"✅ Verified certificate at {cert_path} (length: {len(cert_content)} chars)")
                # Advanced OpenSSL validation if available
                try:
                    import subprocess
                    result = subprocess.run(['openssl', 'x509', '-in', cert_path, '-text', '-noout'], 
                                           capture_output=True, text=True)
                    if result.returncode == 0:
                        # Log certificate details without sensitive info
                        subject_line = [line for line in result.stdout.split('\n') if 'Subject:' in line]
                        issuer_line = [line for line in result.stdout.split('\n') if 'Issuer:' in line]
                        valid_dates = [line for line in result.stdout.split('\n') if 'Not Before:' in line or 'Not After :' in line]
                        
                        logger.info(f"Certificate validation successful! Details:")
                        for line in subject_line + issuer_line + valid_dates:
                            logger.info(f"   {line.strip()}")
                    else:
                        logger.warning(f"⚠️ OpenSSL validation failed: {result.stderr}")
                except Exception as openssl_error:
                    logger.warning(f"⚠️ Could not perform OpenSSL validation: {str(openssl_error)}")
            else:
                logger.error(f"❌ Certificate at {cert_path} appears corrupted or incomplete")
            
            # Log the beginning and end of the certificate (without revealing full content)
            lines = cert_content.split('\n')
            if len(lines) > 6:
                logger.info(f"Certificate beginning:\n{lines[0]}\n{lines[1]}\n{lines[2]}")
                logger.info(f"Certificate ending:\n{lines[-3]}\n{lines[-2]}\n{lines[-1]}")
            
        # Certificate exists
        cert_exists = True
    except Exception as cert_error:
        logger.error(f"❌ Error processing certificate: {str(cert_error)}")
        logger.error(traceback.format_exc())
        # Continue and try connecting without certificate
        cert_exists = False
else:
    logger.warning("⚠️ MONGO_X509_CERT_BASE64 environment variable not found")
    # Check if cert file exists already
    cert_exists = os.path.exists(cert_path)
    if cert_exists:
        logger.info(f"✅ Found existing certificate at {cert_path}")
    else:
        logger.warning(f"⚠️ No certificate found at {cert_path}")

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
    
    # Check if the URI has the correct format for X.509
    if "authMechanism=MONGODB-X509" not in uri:
        logger.warning("⚠️ URI does not contain X.509 authentication. Adding it...")
        if "?" in uri:
            uri += "&authMechanism=MONGODB-X509"
        else:
            uri += "?authMechanism=MONGODB-X509"
        logger.info(f"Updated URI: {uri[:30]}...")
    
    # Check if the certificate is correctly set up
    if cert_exists:
        # Validate certificate file content
        try:
            with open(cert_path, "r") as cert_file:
                cert_content = cert_file.read()
                if "BEGIN CERTIFICATE" not in cert_content or "END CERTIFICATE" not in cert_content:
                    logger.error("❌ Certificate file does not contain a valid certificate!")
                    cert_exists = False
                else:
                    logger.info("✅ Certificate file validated successfully")
        except Exception as cert_read_error:
            logger.error(f"❌ Error reading certificate file: {str(cert_read_error)}")
            cert_exists = False
    
    # First attempt connection using X.509 certificate directly
    try:
        logger.info("Attempting connection with X.509 certificate...")
        # Log detailed connection parameters for debugging
        logger.info(f"Connection parameters: TLS: {True}, Certificate exists: {cert_exists}, Cert path: {cert_path}")
        
        if not cert_exists:
            logger.error("❌ Certificate not found or invalid! Attempting connection without certificate.")
            raise Exception("Certificate not found")
        
        # Try with explicit authSource and authMechanism parameters
        client = MongoClient(
            uri,
            tls=True,
            tlsCertificateKeyFile=cert_path,
            serverSelectionTimeoutMS=5000,
            server_api=ServerApi('1')
        )
        # Test connection with timeout
        client.admin.command('ping')
        logger.info("✅ Successfully connected to MongoDB with X.509 certificate!")
    except Exception as x509_error:
        logger.error(f"❌ MongoDB connection error with X.509 certificate: {str(x509_error)}")
        
        # Try with client certificate auth (no authMechanism in URI)
        try:
            logger.info("Attempting connection with client certificate auth...")
            # Remove authMechanism from URI to try simple TLS client auth
            uri_no_auth_mechanism = uri.replace('&authMechanism=MONGODB-X509', '').replace('?authMechanism=MONGODB-X509', '?')
            logger.info(f"Modified URI without authMechanism: {uri_no_auth_mechanism[:30]}...")
            
            client = MongoClient(
                uri_no_auth_mechanism, 
                tls=True,
                tlsCertificateKeyFile=cert_path,
                serverSelectionTimeoutMS=5000,
                server_api=ServerApi('1')
            )
            client.admin.command('ping')
            logger.info("✅ Connected with client certificate auth!")
        except Exception as client_cert_error:
            logger.error(f"❌ Client certificate auth failed: {str(client_cert_error)}")
            
            # Try with relaxed TLS settings
            try:
                logger.info("Attempting connection with relaxed TLS settings...")
                client = MongoClient(
                    uri, 
                    serverSelectionTimeoutMS=5000,
                    tls=True,
                    tlsAllowInvalidCertificates=True,
                    server_api=ServerApi('1')
                )
                client.admin.command('ping')
                logger.info("✅ Connected with relaxed TLS settings!")
            except Exception as relaxed_error:
                logger.error(f"❌ Relaxed TLS connection failed: {str(relaxed_error)}")
                
                # Final fallback: try with username/password from environment
                try:
                    logger.info("Attempting connection with username/password auth...")
                    username = os.getenv("MONGO_USERNAME")
                    password = os.getenv("MONGO_PASSWORD")
                    
                    if username and password:
                        # Create a URI with username/password
                        base_uri = uri.split("@")[1] if "@" in uri else uri
                        user_pass_uri = f"mongodb+srv://{username}:{password}@{base_uri}"
                        logger.info(f"Created username/password URI: {user_pass_uri[:30]}...")
                        
                        client = MongoClient(
                            user_pass_uri,
                            serverSelectionTimeoutMS=5000,
                            tls=True,
                            server_api=ServerApi('1')
                        )
                        client.admin.command('ping')
                        logger.info("✅ Connected with username/password auth!")
                    else:
                        logger.error("❌ No username/password credentials found in environment")
                        raise Exception("No fallback credentials available")
                except Exception as user_pass_error:
                    logger.error(f"❌ Username/password auth failed: {str(user_pass_error)}")
                    
                    # Last resort: try without TLS
                    try:
                        logger.info("Attempting final fallback connection without TLS...")
                        # Try without TLS as last resort
                        uri_without_tls = uri.replace('&authMechanism=MONGODB-X509', '')
                        logger.info(f"Modified URI: {uri_without_tls[:30]}...")
                        
                        client = MongoClient(
                            uri_without_tls, 
                            serverSelectionTimeoutMS=5000,
                            tls=False,
                            server_api=ServerApi('1')
                        )
                        client.admin.command('ping')
                        logger.info("✅ Connected with non-TLS fallback method!")
                    except Exception as final_error:
                        logger.error(f"❌ All connection attempts failed: {str(final_error)}")
                        raise
    
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
        # Use the smallest possible model to save memory
        model_name = 'sentence-transformers/paraphrase-MiniLM-L3-v2'  # Very small model
        
        # Add memory optimization settings
        os.environ['PYTORCH_NO_CUDA_MEMORY_CACHING'] = '1'  # Disable CUDA caching
        
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir='/tmp/transformers_cache',
            local_files_only=False
        )
        
        # Load model with maximum memory optimizations
        model = AutoModel.from_pretrained(
            model_name,
            cache_dir='/tmp/transformers_cache',
            local_files_only=False,
            low_cpu_mem_usage=True  # Reduce memory usage
        )
        
        # Move model to CPU and aggressively clear memory
        model = model.cpu()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # Force garbage collection
        gc.collect()
        
        logger.info(f"Model loaded: {model_name} (lightweight version)")
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

# Function to generate embeddings with memory optimization
def generate_embedding(text):
    try:
        # Limit input text length to conserve memory
        max_length = 512
        if len(text) > max_length:
            logger.info(f"Truncating input text from {len(text)} to {max_length} chars to save memory")
            text = text[:max_length]
        
        # Tokenize with max length limit
        inputs = tokenizer(
            text, 
            padding=True, 
            truncation=True, 
            max_length=128,  # Reduced from 256 to save memory
            return_tensors="pt"
        )
        
        # Move inputs to CPU explicitly
        inputs = {k: v.cpu() for k, v in inputs.items()}
        
        # Generate embeddings with memory optimization
        with torch.no_grad():
            outputs = model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)
            
        # Convert to list and clear memory immediately
        result = embeddings[0].cpu().numpy().tolist()
        
        # Force aggressive garbage collection
        del inputs, outputs, embeddings
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        gc.collect()
            
        return result
    except Exception as e:
        logger.error(f"❌ Error generating embedding: {str(e)}")
        # Try to free memory even if there's an error
        gc.collect()
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
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
    
    # Memory optimization: Limit content size for very large documents
    if len(content) > 10000:
        logger.warning(f"Content is very large ({len(content)} chars). Truncating to 10000 chars to save memory.")
        content = content[:10000]
    
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
        
        # Generate embedding with timing and memory tracking
        embed_start = time()
        start_mem = psutil.Process().memory_info().rss / 1024 / 1024 if 'psutil' in sys.modules else 0
        
        try:
            embedding = generate_embedding(content)
            embed_time = time() - embed_start
            
            if not embedding:
                logger.error("❌ Failed to generate embedding for document")
                return False
                
            end_mem = psutil.Process().memory_info().rss / 1024 / 1024 if 'psutil' in sys.modules else 0
            mem_diff = end_mem - start_mem
            
            logger.info(f"✅ Generated embedding in {embed_time:.3f}s | Size: {len(embedding)} | Memory use: {mem_diff:.1f}MB")
        except Exception as embed_error:
            logger.error(f"❌ Embedding generation failed: {str(embed_error)}")
            # Free memory and attempt to continue
            gc.collect()
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            return False
        
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
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False

# Initialize database and collections after successful connection
def initialize_database_structure():
    """Initialize the database collections and indexes"""
    if not db:
        logger.error("Database not initialized")
        return False
    
    success = True
    collections = db.list_collection_names()
    logger.info(f"Existing collections: {collections}")
    
    # Create chats collection if it doesn't exist
    if 'chats' not in collections:
        try:
            db.create_collection('chats')
            db.chats.create_index([('user_id', 1)])
            db.chats.create_index([('timestamp', -1)])
            logger.info("Created chats collection with indexes")
        except Exception as e:
            logger.error(f"Error creating chats collection: {str(e)}")
            success = False
    
    # Create users collection if it doesn't exist
    if 'users' not in collections:
        try:
            db.create_collection('users')
            db.users.create_index([('user_id', 1)], unique=True)
            logger.info("Created users collection with user_id index")
        except Exception as e:
            logger.error(f"Error creating users collection: {str(e)}")
            success = False
    
    # Create vector_embeddings collection if it doesn't exist
    if 'vector_embeddings' not in collections:
        try:
            db.create_collection('vector_embeddings')
            db.vector_embeddings.create_index([('title', 1)])
            db.vector_embeddings.create_index([('category', 1)])
            logger.info("Created vector_embeddings collection with indexes")
            
            # Now let's create a vector search index
            setup_vector_search()
        except Exception as e:
            logger.error(f"Error creating vector_embeddings collection: {str(e)}")
            success = False
    
    # Create temperature_records collection if it doesn't exist
    if 'temperature_records' not in collections:
        try:
            db.create_collection('temperature_records')
            db.temperature_records.create_index([('date', 1)], unique=True)
            logger.info("Created temperature_records collection with date index")
        except Exception as e:
            logger.error(f"Error creating temperature_records collection: {str(e)}")
            success = False
    
    return success

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

def connect_to_mongodb():
    """Connect to MongoDB using environment variables."""
    global mongo_client, db
    
    # Track connection attempts for diagnostics
    connection_attempts = []
    
    # Get MongoDB URI from environment
    mongo_uri = os.getenv("MONGODB_URI")
    
    if not mongo_uri:
        logger.error("❌ MONGODB_URI environment variable not set")
        return False
        
    logger.info(f"Connecting to MongoDB... URI starts with: {mongo_uri[:20]}... (URI length: {len(mongo_uri)})")
    
    # Check if URI appears to contain X.509 configurations
    contains_x509 = "authMechanism=MONGODB-X509" in mongo_uri
    contains_tls = "tls=true" in mongo_uri or "ssl=true" in mongo_uri
    
    if cert_exists:
        logger.info(f"✅ Using certificate at {cert_path}")
        # Ensure URI has authMechanism=MONGODB-X509 if using cert
        if not contains_x509 and "authMechanism=" not in mongo_uri:
            if "?" in mongo_uri:
                mongo_uri += "&authMechanism=MONGODB-X509"
                logger.info("✅ Added authMechanism=MONGODB-X509 to URI")
            else:
                mongo_uri += "?authMechanism=MONGODB-X509"
                logger.info("✅ Added authMechanism=MONGODB-X509 to URI")
        
        # Ensure TLS is enabled
        if not contains_tls:
            if "?" in mongo_uri:
                mongo_uri += "&tls=true"
                logger.info("✅ Added tls=true to URI")
            else:
                mongo_uri += "?tls=true"
                logger.info("✅ Added tls=true to URI")
    
    # Check if certificate path exists and has content
    if cert_exists:
        try:
            cert_stat = os.stat(cert_path)
            logger.info(f"Certificate file size: {cert_stat.st_size} bytes")
            
            if cert_stat.st_size == 0:
                logger.error("❌ Certificate file exists but is empty!")
                cert_exists = False
        except Exception as stat_error:
            logger.error(f"❌ Error checking certificate: {str(stat_error)}")
            cert_exists = False
    
    # Log system environment information
    logger.info(f"System: {platform.system()} {platform.release()}, Python: {sys.version}")
    logger.info(f"Memory: {psutil.virtual_memory().available / 1024 / 1024:.1f}MB available")
    
    # Connection attempt function with logging
    def attempt_connection(method, uri, **kwargs):
        start_time = time.time()
        logger.info(f"🔄 Attempting connection with method: {method}")
        
        try:
            # Create connection
            client = pymongo.MongoClient(uri, **kwargs)
            
            # Force a connection to verify
            client.admin.command('ping')
            
            # Success
            elapsed = time.time() - start_time
            logger.info(f"✅ Connection successful using {method} ({elapsed:.2f}s)")
            connection_attempts.append({"method": method, "status": "success", "time": elapsed})
            return client
        except Exception as e:
            elapsed = time.time() - start_time
            error_str = str(e)
            
            # Log the error (trim if very long)
            if len(error_str) > 500:
                error_str = error_str[:500] + "... [truncated]"
            logger.error(f"❌ Connection failed with {method}: {error_str} ({elapsed:.2f}s)")
            
            # Add detailed authentication error info
            if "Authentication failed" in error_str:
                logger.error("   ↳ This is an authentication error - check credentials and certificate")
            if "SSL handshake failed" in error_str:
                logger.error("   ↳ This is an SSL/TLS error - check your certificate and TLS settings")
            if "Server Selection Timeout" in error_str:
                logger.error("   ↳ This is a timeout error - check network and firewall settings")
            
            connection_attempts.append({"method": method, "status": "failed", "error": error_str, "time": elapsed})
            return None
    
    # ATTEMPT 1: Try connecting with X.509 certificate if it exists
    if cert_exists:
        logger.info(f"Attempting X.509 certificate connection with cert: {cert_path}")
        
        client = attempt_connection(
            "X.509 Certificate", 
            mongo_uri,
            tlsCAFile=cert_path,
            tlsCertificateKeyFile=cert_path
        )
        
        if client:
            mongo_client = client
            db = mongo_client.get_default_database()
            logger.info("✅ Successfully connected to MongoDB using X.509 certificate")
            return True
    
    # ATTEMPT 2: Try client certificate auth (without explicit authMechanism)
    if cert_exists:
        logger.info("Trying client certificate authentication (without explicit X.509 mechanism)")
        
        # Modify URI to remove authMechanism=MONGODB-X509 if present
        alt_uri = mongo_uri
        if "authMechanism=MONGODB-X509" in alt_uri:
            alt_uri = alt_uri.replace("authMechanism=MONGODB-X509", "")
            # Clean up URI: remove empty parameters and fix consecutive delimiters
            alt_uri = alt_uri.replace("&&", "&").replace("?&", "?").rstrip("&?")
            if alt_uri.endswith("?"):
                alt_uri = alt_uri[:-1]
        
        client = attempt_connection(
            "Client Certificate Auth",
            alt_uri,
            tlsCAFile=cert_path,
            tlsCertificateKeyFile=cert_path
        )
        
        if client:
            mongo_client = client
            db = mongo_client.get_default_database()
            logger.info("✅ Successfully connected to MongoDB using client certificate")
            return True
    
    # ATTEMPT 3: Try with relaxed TLS settings
    if cert_exists:
        logger.info("Trying connection with relaxed TLS settings")
        
        client = attempt_connection(
            "Relaxed TLS",
            mongo_uri,
            tlsCAFile=cert_path,
            tlsCertificateKeyFile=cert_path,
            tlsAllowInvalidCertificates=True
        )
        
        if client:
            mongo_client = client
            db = mongo_client.get_default_database()
            logger.warning("⚠️ Connected to MongoDB with relaxed TLS security (allowing invalid certificates)")
            return True
    
    # ATTEMPT 4: Try username/password authentication if provided
    username = os.getenv("MONGO_USERNAME")
    password = os.getenv("MONGO_PASSWORD")
    
    if username and password:
        logger.info("Trying username/password authentication")
        
        # Create new URI with username/password
        parts = mongo_uri.split("://")
        if len(parts) == 2:
            protocol, rest = parts
            auth_uri = f"{protocol}://{username}:{password}@{rest}"
            
            client = attempt_connection(
                "Username/Password",
                auth_uri
            )
            
            if client:
                mongo_client = client
                db = mongo_client.get_default_database()
                logger.info("✅ Successfully connected to MongoDB using username/password")
                return True
    
    # ATTEMPT 5: Last resort - try without TLS
    logger.warning("⚠️ Attempting connection without TLS as last resort")
    
    # Modify URI to remove TLS/SSL and X.509 authentication
    no_tls_uri = mongo_uri
    for param in ["tls=true", "ssl=true", "authMechanism=MONGODB-X509"]:
        if param in no_tls_uri:
            no_tls_uri = no_tls_uri.replace(param, "")
    
    # Clean up URI: remove empty parameters and fix consecutive delimiters
    no_tls_uri = no_tls_uri.replace("&&", "&").replace("?&", "?").rstrip("&?")
    if no_tls_uri.endswith("?"):
        no_tls_uri = no_tls_uri[:-1]
    
    client = attempt_connection(
        "No TLS",
        no_tls_uri
    )
    
    if client:
        mongo_client = client
        db = mongo_client.get_default_database()
        logger.warning("⚠️ Connected to MongoDB without TLS security - not recommended for production")
        return True
    
    # Final fallback - try direct connection with URI as-is
    logger.warning("⚠️ Attempting direct connection with URI as-is as final attempt")
    
    try:
        mongo_client = pymongo.MongoClient(mongo_uri)
        db = mongo_client.get_default_database()
        logger.info("✅ Successfully connected to MongoDB with direct URI")
        return True
    except Exception as e:
        logger.error(f"❌ All connection attempts failed. Final error: {str(e)}")
        
        # Summarize all connection attempts
        logger.error(f"Connection attempts summary:")
        for i, attempt in enumerate(connection_attempts):
            status = "✅" if attempt["status"] == "success" else "❌"
            error_info = f" - Error: {attempt['error']}" if attempt["status"] == "failed" else ""
            logger.error(f"  {i+1}. {status} {attempt['method']} ({attempt['time']:.2f}s){error_info}")
        
        # Log troubleshooting advice
        logger.error("""
❌ CONNECTION TROUBLESHOOTING:
1. Check that your MONGODB_URI is correctly formatted
2. Verify the X.509 certificate is valid and properly formatted
3. Ensure the certificate is accessible and has proper permissions
4. Check if firewall or network settings are blocking the connection
5. Try connecting with MongoDB Compass using the same credentials
        """)
        
        return False 