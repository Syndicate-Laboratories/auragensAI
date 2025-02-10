from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
from database import save_chat, get_user_chats, client as db_client, get_chat_by_id
import os
from dotenv import load_dotenv
import anthropic
import openai
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from anthropic import HUMAN_PROMPT, AI_PROMPT

# Load environment variables from .env file
load_dotenv()

# Initialize clients
groq_client = openai.OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY", "")  # Explicitly pass GROQ_API_KEY
)
claude = anthropic.Client(api_key=os.getenv('ANTHROPIC_API_KEY'))

app = Flask(__name__, 
    template_folder='templates',    # Explicitly set template folder
    static_folder='static'         # Explicitly set static folder
)
app.secret_key = os.getenv("SECRET_KEY")

def get_ai_response(message):
    """
    Try Mixtral-8x7B through Groq first, then fall back to Claude if it fails
    """
    system_prompt = """You are Auragens' AI assistant. Provide extremely concise, focused responses about stem cell therapy.

CRITICAL OUTPUT RULES:
1. Maximum 2-3 sentences per response
2. ONLY answer what is specifically asked
3. Format key terms as: <span style="color:#0066cc">**term**</span>
4. No greetings or closings
5. No unrequested lists or context
6. No emojis or decorative elements

RESPONSE STRUCTURE:
- Direct answer first
- Supporting detail second (if needed)
- Mention Auragens only if directly relevant

Example Good Response:
User: What are MSCs?
Assistant: <span style="color:#0066cc">**Mesenchymal stem cells (MSCs)**</span> are specialized cells that can develop into different tissue types. At Auragens, we source MSCs from Wharton's Jelly tissue for optimal therapeutic results.

Example Bad Response:
User: What are MSCs?
Assistant: Hello! Let me tell you about stem cells. MSCs are interesting cells that... [too long, includes greeting]

CORE KNOWLEDGE BASE:
- MSCs from Wharton's Jelly tissue
- Superior to bone marrow/adipose sources
- Led by Dr. James Utley PhD
- Panama City location, ISO-certified lab
- Treatment areas: orthopedic, autoimmune, cardiovascular, neurological, pulmonary, anti-aging, spine

TONE:
- Professional and academic
- Direct and concise
- Evidence-based
- No marketing language"""

    try:
        # First attempt: Mixtral-8x7B through Groq
        groq_response = groq_client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        return groq_response.choices[0].message.content
    except Exception as e:
        print(f"Groq Mixtral Error: {str(e)}")
        try:
            # Fallback: Claude
            claude_response = claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
            )
            return claude_response.content[0].text
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
    response = get_ai_response(user_message)
    
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