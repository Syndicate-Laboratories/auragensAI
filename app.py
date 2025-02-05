from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
from database import save_chat, get_user_chats, client as db_client, get_chat_by_id
import os
from dotenv import load_dotenv
import anthropic
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from anthropic import HUMAN_PROMPT, AI_PROMPT

# Load environment variables from .env file
load_dotenv()

# Initialize Claude client
claude = anthropic.Client(api_key=os.getenv('ANTHROPIC_API_KEY'))

app = Flask(__name__, 
    template_folder='templates',    # Explicitly set template folder
    static_folder='static'         # Explicitly set static folder
)
app.secret_key = os.getenv("SECRET_KEY")

def get_claude_response(message):
    try:
        response = claude.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"""You are a stem cell therapy consultant for Auragens. 
                    Follow these rules for all responses:
                    1. Only use **bold** for key medical terms, specific procedures, or important numbers
                    2. Structure your response in clear sections with headers in **bold**
                    3. Use bullet points for lists, with a line break before and after lists
                    4. Start with a brief overview
                    5. Break down complex topics into digestible chunks
                    6. End with a "**Key Takeaways:**" section
                    7. Keep paragraphs short (2-3 sentences max)
                    8. Add a line break between sections
                    
                    User question: {message}"""
            }]
        )
        # Process markdown in the response
        formatted_response = response.content[0].text.replace('**', '<strong>').replace('</strong>**', '</strong>')
        return formatted_response
    except Exception as e:
        print(f"Claude API Error: {str(e)}")
        return "I apologize, but I'm having trouble processing your request. Please try again."

@app.errorhandler(500)
def handle_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'Database connection failed. Please try again later.'
    }), 500

@app.route('/')
def home():
    try:
        # Test database connection before rendering
        db_client.admin.command('ping')
    except Exception as e:
        print("❌ Database error:", e)
        print(f"Warning: Database connection failed but continuing: {e}")
    
    # Return the template regardless of database connection
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    response = get_claude_response(user_message)
    
    # Save to database with error handling
    try:
        save_chat('guest', user_message, response)
    except Exception as e:
        print(f"Warning: Failed to save chat: {e}")
        # Continue even if save fails
    
    return jsonify({'response': response})

@app.route('/chat-history', methods=['GET'])
def chat_history():
    try:
        history = get_user_chats('guest')
        return jsonify({'history': history})
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return jsonify({'history': [], 'error': 'Failed to fetch chat history'}), 500

@app.route('/chat/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    try:
        chat = get_chat_by_id(chat_id)
        if chat:
            return jsonify(chat)
        return jsonify({'error': 'Chat not found'}), 404
    except Exception as e:
        print(f"Error fetching chat: {e}")
        return jsonify({'error': 'Failed to fetch chat'}), 500

if __name__ == '__main__':
    app.run(debug=True) 