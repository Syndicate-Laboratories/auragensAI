# AuragensAI - Advanced Stem Cell Therapy Chatbot

AuragensAI is a specialized AI assistant for Auragens focused on stem cell therapy and regenerative medicine. The application uses advanced language models to provide accurate, concise information about stem cell treatments, with an emphasis on Auragens' specialized protocols and expertise.

## Features

- **AI-Powered Chat Interface**: Utilizes Mixtral-8x7B (via Groq) and Claude (Anthropic) models for intelligent, context-aware conversations
- **Vector Search**: Semantic document search using transformer-based embeddings
- **User Authentication**: Secure Auth0 integration for user management
- **Chat History**: Persistent storage of conversations for reference
- **Document Upload**: Support for uploading relevant medical documents and research papers
- **Responsive Design**: Modern web interface that works across devices

## Technology Stack

- **Backend**: Python/Flask
- **Database**: MongoDB Atlas
- **AI Models**: 
  - Groq API (Mixtral-8x7B)
  - Anthropic API (Claude)
- **NLP**: Hugging Face Transformers for document embeddings
- **Authentication**: Auth0
- **Deployment**: Compatible with Heroku/similar platforms

## Installation

### Prerequisites

- Python 3.8+
- MongoDB Atlas account
- API keys for Groq and Anthropic
- Auth0 account

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/your-username/auragensAI.git
   cd auragensAI
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file with the following variables:
   ```
   MONGO_URI=your_mongodb_connection_string
   GROQ_API_KEY=your_groq_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   SECRET_KEY=your_flask_secret_key
   AUTH0_CLIENT_ID=your_auth0_client_id
   AUTH0_CLIENT_SECRET=your_auth0_client_secret
   AUTH0_DOMAIN=your_auth0_domain
   ```

5. Run the application:
   ```
   python app.py
   ```

## Usage

1. Navigate to `http://localhost:5000` in your browser
2. Log in using Auth0 credentials
3. Interact with the chatbot by asking questions about stem cell therapy
4. Access chat history and manage uploaded documents through the UI

## API Endpoints

- `GET /`: Home page
- `POST /chat`: Submit a chat message
- `GET /chat-history`: Get user's chat history
- `GET /chat/<chat_id>`: Get a specific chat
- `GET /upload`: Get the document upload form
- `POST /upload`: Upload a document
- `GET /login`: Auth0 login
- `GET /logout`: Log out of the system
- `GET /callback`: Auth0 callback URL

## Project Structure

```
auragensAI/
├── app.py                  # Main Flask application
├── auth.py                 # Authentication utilities
├── config.py               # Configuration variables
├── database.py             # MongoDB connection and database functions
├── requirements.txt        # Python dependencies
├── static/                 # CSS, JS, and static files
├── templates/              # HTML templates
│   ├── index.html          # Main chat interface
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── thank_you.html      # Confirmation page
│   └── upload.html         # Document upload interface
├── .env                    # Environment variables (not in repository)
├── Procfile                # For deployment to platforms like Heroku
└── runtime.txt             # Python runtime specification
```

## Development

### Adding New Features

1. Create a new branch for your feature
2. Implement and test the feature
3. Submit a pull request

### Running Tests

```
# TODO: Add test instructions
```

## License

This project is licensed under the terms of the license included in the repository.

## Contact

For questions or support, please contact Dr. James Utley, PhD at [contact information].
