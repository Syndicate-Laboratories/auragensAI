from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv
from datetime import datetime
from bson import ObjectId
from sentence_transformers import SentenceTransformer
import numpy as np
import logging

load_dotenv(override=True)

# Debug: Print current working directory and env vars
print(f"Current working directory: {os.getcwd()}")
print(f"All environment variables: {os.environ.keys()}")

# Force the correct MongoDB Atlas URI
uri = "mongodb+srv://AuragensAI_admin:2t6ubBsqqwZtGPw4@auragens-ai.6zehw.mongodb.net/?retryWrites=true&w=majority&appName=Auragens-AI"
print(f"Loaded URI: {uri[:30]}..." if uri else "URI not loaded")

if not uri:
    raise Exception("MONGO_URI environment variable not found")

# Initialize MongoDB client with options
client = MongoClient(uri, server_api=ServerApi('1'))

# Verify connection on startup
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Initialize database and collection
db = client['Auragens_AI']
chats = db['chats']
vector_embeddings = db['vector_embeddings']

# Create index for semantic search
vector_embeddings.create_index([("embedding", "2dsphere")])

logger = logging.getLogger(__name__)

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
    model = SentenceTransformer('all-MiniLM-L6-v2')
    return model.encode(text).tolist()

# Function to insert document with embedding
def insert_document_with_embedding(title, content, category):
    embedding = generate_embedding(content)
    document = {
        "title": title,
        "content": content,
        "category": category,
        "embedding": embedding,
        "timestamp": datetime.utcnow()
    }
    return vector_embeddings.insert_one(document)

# Function for semantic search
def semantic_search(query, limit=5):
    try:
        logger.info(f"🔄 Generating embedding for search query...")
        query_embedding = generate_embedding(query)
        
        logger.info(f"🔍 Searching vector database with limit={limit}")
        results = vector_embeddings.aggregate([
            {
                "$search": {
                    "knnBeta": {
                        "vector": query_embedding,
                        "path": "embedding",
                        "k": limit
                    }
                }
            }
        ])
        
        results_list = list(results)
        logger.info(f"✅ Semantic search complete. Found {len(results_list)} matches")
        
        # Log titles of found documents
        if results_list:
            titles = [doc.get('title', 'Untitled') for doc in results_list]
            logger.info(f"📑 Found documents: {', '.join(titles)}")
        
        return results_list
    except Exception as e:
        logger.error(f"❌ Semantic search error: {str(e)}")
        return [] 