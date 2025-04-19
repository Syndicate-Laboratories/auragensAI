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

load_dotenv(override=True)

# Debug: Print current working directory and env vars
print(f"Current working directory: {os.getcwd()}")
print(f"All environment variables: {os.environ.keys()}")

# Get MongoDB URI from environment variables
uri = os.getenv("MONGO_URI")
print(f"Loaded URI: {uri[:30]}..." if uri else "URI not loaded")

if not uri:
    raise Exception("MONGO_URI environment variable not found")

# Initialize MongoDB client with options
try:
    # Connect with proper error handling
    client = MongoClient(uri, serverSelectionTimeoutMS=5000, server_api=ServerApi('1'))
    
    # Test connection with timeout
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(f"MongoDB connection error: {str(e)}")
    # Provide fallback connection method if SRV format fails
    try:
        # Extract credentials and host from the URI if possible
        print("Attempting alternative connection method...")
        if "mongodb+srv://" in uri:
            # Parse parts manually if needed
            parts = uri.replace("mongodb+srv://", "").split("@")
            if len(parts) == 2:
                credentials = parts[0]
                host_part = parts[1].split("/?")[0]
                alt_uri = f"mongodb://{credentials}@{host_part}/?retryWrites=true&w=majority"
                client = MongoClient(alt_uri, serverSelectionTimeoutMS=5000)
                client.admin.command('ping')
                print("Connected with alternative method!")
            else:
                raise Exception("Could not parse MongoDB URI")
        else:
            raise Exception("Not a srv:// URI format")
    except Exception as alt_e:
        print(f"Alternative connection also failed: {str(alt_e)}")
        # Last resort - use a hardcoded but functional URI structure
        print("Using direct connection as last resort")
        direct_uri = "mongodb+srv://AuragensAI_admin:2t6ubBsqqwZtGPw4@auragens-ai.6zehw.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(direct_uri, serverSelectionTimeoutMS=5000)

# Initialize database and collection
db = client['Auragens_AI']
chats = db['chats']
vector_embeddings = db['vector_embeddings']

# Create index for semantic search
try:
    vector_embeddings.create_index([("embedding", "2dsphere")])
except Exception as e:
    print(f"Error creating index: {str(e)}")

logger = logging.getLogger(__name__)

# Set environment variables for better memory management
os.environ['TRANSFORMERS_CACHE'] = '/tmp/transformers_cache'
os.environ['TORCH_CUDA_ARCH_LIST'] = '3.5;5.0;6.0;7.0;7.5'  # Optimize CUDA architectures

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

# Initialize at startup
tokenizer, model = initialize_models()

def save_chat(user_id, user_message, bot_response):
    try:
        # Verify connection before saving
        client.admin.command('ping')
        
        chat = {
            'user_id': user_id,
            'user_message': user_message,
            'bot_response': bot_response,
            'timestamp': datetime.utcnow()
        }
        result = chats.insert_one(chat)
        print(f"✅ Chat saved successfully with ID: {result.inserted_id}")
        return result.inserted_id
    except Exception as e:
        print(f"❌ Error saving chat: {str(e)}")
        print("Attempting to reconnect...")
        try:
            client.admin.command('ping')
            result = chats.insert_one(chat)
            print(f"✅ Chat saved successfully after retry with ID: {result.inserted_id}")
            return result.inserted_id
        except Exception as retry_error:
            print(f"❌ Retry failed: {str(retry_error)}")
        raise

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