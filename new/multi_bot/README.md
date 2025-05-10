# RAGify India: Multi-Domain Legal Assistant

A comprehensive RAG-based system with multiple domain-specific bots for Indian legal queries, accessible through both a web interface and RESTful API.

## Features

- **Multiple Domain-Specific Bots**:
  - IPC Bot: Indian Penal Code specialist
  - RTI Bot: Right to Information expert
  - Labor Law Bot: Labor regulations advisor
  - Constitution Bot: Constitutional expert

- **Efficient Document Management**:
  - Handles 5000+ pages of legal documents
  - Organizes content by legal domain
  - Persistent vector stores for each domain

- **Advanced RAG Implementation**:
  - Domain-specific prompt engineering
  - Optimized retrieval parameters
  - Source citations for transparency

- **Multiple Access Methods**:
  - Web UI using Streamlit
  - RESTful API using FastAPI
  - Python client library

## Directory Structure

```
multi_bot/
├── ingest/
│   ├── __init__.py
│   ├── base_ingestion.py
│   ├── custom_loaders.py
│   ├── domain_ingestion.py
│   └── ingest_all.py
├── prompts/
│   ├── __init__.py
│   └── domain_prompts.py
├── data/
│   ├── ipc/
│   ├── rti/
│   ├── labor_law/
│   └── constitution/
├── vectorstores/
│   ├── ipc_index/
│   ├── rti_index/
│   ├── labor_law_index/
│   └── constitution_index/
├── app.py            # Streamlit web interface
├── api.py            # FastAPI server
├── utils.py
├── client_examples.py
├── requirements.txt
└── README.md
```

## Setup Instructions

1. **Install Requirements**:
   ```
   pip install -r requirements.txt
   ```

2. **Create Data Directories**:
   Create directories for each domain under `data/`:
   ```
   mkdir -p data/ipc data/rti data/labor_law data/constitution
   ```

3. **Add Legal Documents**:
   Place PDF and text files in the corresponding domain directories:
   - `data/ipc/`: IPC sections, case laws, etc.
   - `data/rti/`: RTI Act, circulars, guidelines, etc.
   - `data/labor_law/`: Labor codes, factory acts, etc.
   - `data/constitution/`: Constitution of India, amendments, etc.

4. **Set Environment Variables**:
   Create a `.env` file with:
   ```
   GOOGLE_API_KEY=your_google_api_key
   ```

5. **Ingest Documents**:
   Process all domains:
   ```
   python ingest/ingest_all.py
   ```
   
   Or process a specific domain:
   ```
   python ingest/ingest_all.py --domain ipc
   ```

## Running the Applications

### Web Interface

Start the Streamlit web interface:
```
streamlit run app.py
```

### API Server

Start the FastAPI server:
```
uvicorn api:app --reload --port 8000
```

Once running, you can access:
- API endpoints at http://localhost:8000
- Interactive API documentation at http://localhost:8000/docs

## API Documentation

### Authentication

Currently, the API does not require authentication. For production deployments, consider adding authentication.

### API Endpoints

#### System Endpoints

##### Health Check
```
GET /health
```
Checks if the API service is running.

**Response:**
```json
{
  "status": "ok",
  "message": "API is running"
}
```

#### Bot Management

##### List All Bots
```
GET /bots
```
Returns a list of all bots with their availability status.

**Response:**
```json
[
  {
    "name": "IPC Bot",
    "description": "Specialized in Indian Penal Code (IPC) sections, criminal offenses, and punishments.",
    "available": true
  },
  {
    "name": "RTI Bot",
    "description": "Expert on Right to Information (RTI) Act, filing procedures, and information access rights.",
    "available": false
  },
  ...
]
```

##### Query a Bot
```
POST /bots/{bot_name}/query
```
Query a specific bot with a question.

**Request Body:**
```json
{
  "query": "What is the punishment for theft under IPC?"
}
```

**Response:**
```json
{
  "answer": "According to Section 379 of the Indian Penal Code, the punishment for theft is imprisonment of either description for a term which may extend to three years, or with fine, or with both.",
  "sources": [
    {
      "content": "379. Punishment for theft.—Whoever commits theft shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both.",
      "metadata": {
        "source": "data/ipc/ipc_chapter_17.pdf",
        "page": 5
      }
    }
  ]
}
```

#### Document Management

##### Upload Document
```
POST /upload
```
Upload a document to a specific domain.

**Form Parameters:**
- `file`: The file to upload (PDF or TXT)
- `domain`: Domain to upload to (ipc, rti, labor_law, constitution)

**Response:**
```json
{
  "status": "success",
  "message": "File uploaded successfully to ipc. Run ingestion to process the document."
}
```

##### Start Document Ingestion
```
POST /ingest/{domain}
```
Start the ingestion process for a specific domain or all domains.

**Path Parameters:**
- `domain`: Domain to ingest (ipc, rti, labor_law, constitution, all)

**Response:**
```json
{
  "status": "processing",
  "message": "Document ingestion started for ipc"
}
```

## API Usage Examples

### Python Example

```python
import requests

# Query IPC Bot
response = requests.post(
    "http://localhost:8000/bots/IPC Bot/query",
    json={"query": "What is the punishment for theft?"}
)
print(response.json()["answer"])

# Upload a document
with open("new_law.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/upload",
        files={"file": f},
        data={"domain": "ipc"}
    )
print(response.json())

# Start ingestion
response = requests.post("http://localhost:8000/ingest/ipc")
print(response.json())
```

### cURL Example

```bash
# Query IPC Bot
curl -X 'POST' \
  'http://localhost:8000/bots/IPC%20Bot/query' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the punishment for theft?"}'

# Upload a document
curl -X 'POST' \
  'http://localhost:8000/upload' \
  -F 'file=@/path/to/your/document.pdf' \
  -F 'domain=ipc'

# Start ingestion
curl -X 'POST' 'http://localhost:8000/ingest/ipc'
```

## Technical Details

- **Embeddings**: HuggingFace sentence-transformers
- **Vector Store**: ChromaDB
- **LLM**: Google Gemini
- **Framework**: LangChain
- **Web UI**: Streamlit
- **API**: FastAPI

## Adding More Documents

To expand the knowledge base:
1. Add new PDF or text files to the appropriate domain folder (via API or directly)
2. Run the ingestion process for that domain (via API or Python script)
3. The bot will now have access to the new information

## Advanced Configuration

For production deployment, consider:
- Adding authentication to the API
- Using a production ASGI server for the API (like Gunicorn)
- Setting up proper CORS policies
- Implementing rate limiting
- Setting up a reverse proxy (Nginx, etc.)

# Voice Call Integration

This project now includes a voice call integration using Twilio. Users can call a Twilio number, select their preferred language, choose a legal domain, ask a question verbally, and receive an answer in the selected language.

## Setup Voice Call Integration

1. **Sign up for a Twilio Account**
   - Go to [Twilio](https://www.twilio.com/try-twilio) and create an account
   - Get a Twilio phone number with voice capabilities

2. **Set Environment Variables**
   - Make sure your `.env` file includes both GOOGLE_API_KEY and OPENAI_API_KEY

3. **Run the Voice Server**
   ```
   python voice_server.py
   ```

4. **Expose the Server with ngrok**
   - Download [ngrok](https://ngrok.com/download) and set it up
   - Run: `ngrok http 5001`
   - Copy the HTTPS URL provided by ngrok (e.g., `https://abc123.ngrok.io`)

5. **Configure Twilio**
   - Go to the Twilio Console > Phone Numbers > Your Twilio number
   - Under "Voice & Fax" > "A Call Comes In", set the Webhook to:
     ```
     https://abc123.ngrok.io/voice
     ```
   - Set the HTTP method to POST
   - Save your changes

## Voice Call Flow

1. **User calls the Twilio number**
2. **Language Selection**
   - Press 1 for English
   - Press 2 for Hindi
   - Press 3 for Tamil
   - Press 4 for Telugu
   - Press 5 for Marathi

3. **Domain Selection**
   - Press 1 for Indian Penal Code
   - Press 2 for Right to Information
   - Press 3 for Labor Law
   - Press 4 for Constitution

4. **Ask Question**
   - User speaks their question after the beep
   - Recording lasts up to 30 seconds

5. **Get Response**
   - The system transcribes the question
   - Queries the appropriate legal bot
   - Reads the answer back in the selected language

6. **Ask Another Question**
   - Press 1 to ask another question
   - Press 2 to end the call

# Web-Based Voice Interface

In addition to the phone-based voice system, this project now includes a web-based voice interface that allows users to interact with the legal assistant using their browser's microphone without making a phone call.

## Setup Web Voice Interface

1. **Set up Google Speech-to-Text**
   - Create a Google Cloud project if you don't have one
   - Enable the Speech-to-Text API
   - Create a service account and download the JSON credentials
   - Set the GOOGLE_APPLICATION_CREDENTIALS environment variable in your .env file

2. **Run the Web Voice Server**
   ```
   python web_voice_server.py
   ```

3. **Access the Interface**
   - Open your browser and navigate to: `http://localhost:5002`
   - Allow microphone permissions when prompted

## Using the Web Voice Interface

1. **Select Language**
   - Choose your preferred language from the dropdown menu

2. **Select Legal Domain**
   - Select which legal bot you want to query (IPC, RTI, Labor Law, or Constitution)

3. **Ask Your Question**
   - Press and hold the Record button while speaking your question
   - Release when finished

4. **Get Your Answer**
   - The system will transcribe your question using Google Speech-to-Text
   - Query the appropriate legal bot
   - Display the answer and sources on the page
   
5. **Continue or Start New**
   - Ask additional questions by pressing the Record button again
   - Start a new conversation with different settings by pressing "Start New Conversation"

# WhatsApp Bot Integration

This project now includes a WhatsApp bot that allows users to interact with the legal assistant through WhatsApp messages.

## Setting Up the WhatsApp Bot

1. **Configure Twilio for WhatsApp**
   - Sign up for a Twilio account: [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)
   - Join the Twilio Sandbox for WhatsApp: [https://www.twilio.com/console/sms/whatsapp/learn](https://www.twilio.com/console/sms/whatsapp/learn)
   - Follow the instructions to connect your WhatsApp account to the Twilio Sandbox

2. **Update Environment Variables**
   - Make sure your .env file has the following Twilio credentials:
     ```
     TWILIO_ACCOUNT_SID=your-twilio-account-sid
     TWILIO_AUTH_TOKEN=your-twilio-auth-token
     TWILIO_PHONE_NUMBER=your-twilio-phone-number
     ```

3. **Run the WhatsApp Bot Server**
   ```
   python whatsapp_bot.py
   ```

4. **Expose your Local Server**
   - Use a tool like ngrok to expose your local server:
     ```
     ngrok http 5003
     ```
   - Copy the HTTPS URL provided by ngrok (e.g., `https://abc123.ngrok.io`)

5. **Configure Twilio Webhook**
   - Go to the Twilio Console > WhatsApp Sandbox
   - Set the "When a message comes in" webhook to:
     ```
     https://abc123.ngrok.io/whatsapp
     ```
   - Set the HTTP method to POST
   - Save your changes

## Using the WhatsApp Bot

1. **Start the Conversation**
   - Send a message to your Twilio WhatsApp number
   - Follow the instructions to join the sandbox if needed
   - The bot will respond with a menu of legal domains

2. **Select a Legal Domain**
   - Reply with the number corresponding to your choice:
     - 1: IPC Bot (Indian Penal Code)
     - 2: RTI Bot (Right to Information Act)
     - 3: Labor Law Bot
     - 4: Constitution Bot

3. **Ask Your Legal Question**
   - After selecting a domain, simply type and send your legal question
   - The bot will process your query and respond with an answer

4. **Additional Commands**
   - "menu" - Show the domain selection menu again
   - "help" - Show help instructions
   - "exit" - Reset the conversation
