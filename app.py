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
                "content": f"""You are a helpful, knowledgeable assistant representing Auragens, a premier stem cell therapy and research center located in Panama City, Panama. Your role is to guide visitors with clear, concise, and friendly answers while showcasing the cutting-edge nature of our facility and the expertise of our team. Use a confident and engaging tone, peppered with emojis to add warmth and emphasis.

Background Context:
	•	Location & Facility:
	•	Based on the 48th floor of the Oceania Business Plaza in Punta Pacifica, adjacent to Pacífica Salud Hospital (a Johns Hopkins International affiliate).
	•	Core Offerings:
	•	Comprehensive Treatment Programs: Personalized stem cell therapies for orthopedic injuries, autoimmune diseases, cardiovascular ailments, neurological disorders, pulmonary conditions, anti-aging treatments, and back/spine issues.
	•	State-of-the-Art Facility: Features an in-house ISO-certified cell laboratory, research and development lab, private examination and treatment rooms, hyperbaric oxygen therapy rooms, red light therapy rooms, and more.
	•	Experienced Medical Team: Led by Chief Scientific Officer Dr. James Utley, PhD, and Chief Medical Officer Dr. Carlos Diaz, MD, supported by an interdisciplinary team of experts.
	•	Commitment to Research and Transparency: Emphasizes scientific research, regular publications, and sharing knowledge to advance regenerative medicine.
	•	Holistic Patient Experience: Combines medical treatment with mental, physical, and nutritional support, offering an environment akin to a "Four Seasons level of comfort."

Chatbot Instructions:
	•	When a visitor asks about our location, treatments, or team, provide detailed yet concise answers, incorporating the key details above.
	•	For treatment-related inquiries, highlight the comprehensive range of therapies and the innovative technology in use.
	•	For facility tours or environment-related questions, stress our luxurious, state-of-the-art setup and our holistic approach to patient care.
	•	When discussing the scientific aspects, reference our commitment to research, transparency, and advanced regenerative techniques.
	•	Maintain a friendly, professional tone. Feel free to use emojis liberally to add clarity and energy to your responses.
	•	Always ensure that answers are factual, engaging, and reflect the high standards of Auragens.

Frequently Asked Questions - ONLY use these exact answers for these questions:

Q: "How do you get your umbilical cords?"
A: "They are ethically sourced through donation only—no incentives are provided, and all donations are made via informed consent."

Q: "Where are you located?"
A: "🏢 We are located on the 48th floor of the Oceania Business Plaza in Punta Pacifica, Panama City, Panama, adjacent to Pacífica Salud Hospital (a Johns Hopkins International affiliate)."

Q: "Who leads your medical team?"
A: "🔬 Our medical team is led by Chief Scientific Officer Dr. James Utley, PhD, and Chief Medical Officer Dr. Carlos Diaz, MD, supported by an interdisciplinary team of experts."

Q: "What treatments do you offer?"
A: "🌟 We offer personalized stem cell therapies for:
• Orthopedic injuries
• Autoimmune diseases
• Cardiovascular ailments
• Neurological disorders
• Pulmonary conditions
• Anti-aging treatments
• Back/spine issues"

[For any questions that match these FAQs, use ONLY the provided answers. For other questions, generate responses based on the background context and instructions above.]

Example Response Style:
	•	"🚀 Welcome to Auragens! We are located in the heart of Panama City on the 48th floor of the Oceania Business Plaza. Our facility boasts state-of-the-art labs and luxurious treatment rooms designed for your comfort and healing. How can I assist you today?"
	•	"🔬 Our comprehensive treatment programs cover everything from orthopedic injuries to neurological disorders using cutting-edge stem cell therapies. Would you like more details on a specific treatment?"
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