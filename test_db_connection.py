import os
import sys
import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_mongodb_connection():
    """Test connection to MongoDB and insert a test document."""
    print('Checking MongoDB connection...')
    print(f'Python version: {sys.version}')
    
    # Get MongoDB URI from environment
    mongodb_uri = os.getenv('MONGODB_URI')
    print(f'MongoDB URI available: {mongodb_uri is not None}')
    
    if not mongodb_uri:
        print("ERROR: MONGODB_URI environment variable not set!")
        return False
    
    try:
        # Create a new client and connect to the server
        print("Attempting to connect to MongoDB...")
        client = MongoClient(mongodb_uri, server_api=ServerApi('1'))
        
        # Send a ping to confirm a successful connection
        client.admin.command('ping')
        print('✅ Successfully connected to MongoDB!')
        
        # Get database and collection
        db = client['Auragens_AI']
        test_collection = db['connection_tests']
        
        # Insert a test document
        test_doc = {
            'message': 'Connection test from Claude',
            'timestamp': datetime.datetime.utcnow(),
            'success': True
        }
        
        result = test_collection.insert_one(test_doc)
        print(f'✅ Test document inserted with ID: {result.inserted_id}')
        
        # Retrieve and verify the document
        found_doc = test_collection.find_one({'_id': result.inserted_id})
        print(f'✅ Retrieved document: {found_doc}')
        
        return True
        
    except Exception as e:
        print(f'❌ Error connecting to MongoDB: {e}')
        return False

if __name__ == "__main__":
    success = test_mongodb_connection()
    print(f"\nConnection test {'succeeded' if success else 'failed'}") 