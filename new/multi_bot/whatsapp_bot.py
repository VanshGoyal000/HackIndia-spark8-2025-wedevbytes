from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import logging
from utils import LegalBotManager
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the Flask application
app = Flask(__name__)

# Initialize Twilio client
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_client = Client(account_sid, auth_token)

# Initialize bot manager
bot_manager = LegalBotManager(google_api_key=os.getenv("GOOGLE_API_KEY"))

# Available bots
LEGAL_BOTS = {
    "1": "IPC Bot",
    "2": "RTI Bot",
    "3": "Labor Law Bot",
    "4": "Constitution Bot"
}

# User sessions (in-memory for simplicity, use a database in production)
user_sessions = {}

# Define welcome message
WELCOME_MESSAGE = """🔍 *Welcome to Legal Assistant!*

Please select a legal domain by replying with the number:

1️⃣ *IPC Bot* (Indian Penal Code)
2️⃣ *RTI Bot* (Right to Information Act)
3️⃣ *Labor Law Bot* (Labor and Employment Laws)
4️⃣ *Constitution Bot* (Constitutional Rights & Articles)

_Example: Send "1" to select IPC Bot_
"""

# Define help message
HELP_MESSAGE = """🔎 *Legal Assistant Commands*

• Send a *number (1-4)* to select a legal domain
• Type your *legal question* after selecting a domain
• Type *"menu"* to see the domain selection options again
• Type *"help"* to see this help message
• Type *"exit"* to reset the conversation
"""

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages."""
    # Get the message from the request
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")  # Format: 'whatsapp:+1234567890'
    
    logger.info(f"Received message from {sender}: {incoming_msg}")
    
    # Initialize response
    resp = MessagingResponse()
    msg = resp.message()
    
    # Check for special commands
    if incoming_msg.lower() == "help":
        msg.body(HELP_MESSAGE)
        return str(resp)
    
    if incoming_msg.lower() == "menu":
        msg.body(WELCOME_MESSAGE)
        return str(resp)
    
    if incoming_msg.lower() == "exit":
        if sender in user_sessions:
            del user_sessions[sender]
        msg.body("Conversation reset. Type 'menu' to start again.")
        return str(resp)
    
    # Initialize or retrieve user session
    if sender not in user_sessions:
        user_sessions[sender] = {"selected_bot": None, "stage": "selecting_bot"}
    
    session = user_sessions[sender]
    
    # Handle bot selection
    if session["stage"] == "selecting_bot":
        if incoming_msg in LEGAL_BOTS:
            bot_name = LEGAL_BOTS[incoming_msg]
            
            # Check if bot exists and is available
            if bot_name in bot_manager.get_available_bots():
                session["selected_bot"] = bot_name
                session["stage"] = "asking_question"
                
                msg.body(f"✅ Selected: *{bot_name}*\n\nPlease ask your legal question and I'll provide an answer based on relevant legal documents.")
            else:
                msg.body(f"❌ Sorry, {bot_name} is not available. Please select another option.")
        else:
            msg.body(WELCOME_MESSAGE)
    
    # Handle legal questions
    elif session["stage"] == "asking_question":
        try:
            bot_name = session["selected_bot"]
            result = bot_manager.query_bot(bot_name, incoming_msg)
            
            # Format the answer and sources for WhatsApp
            answer = result["result"]
            
            # Format source citations if available
            source_text = ""
            if result.get("source_documents"):
                sources = []
                for i, doc in enumerate(result["source_documents"][:2]):  # Limit to 2 sources for readability
                    source = doc.metadata.get("source", "").split("/")[-1]
                    page = doc.metadata.get("page", "")
                    if source and page:
                        sources.append(f"Source {i+1}: {source}, Page: {page}")
                
                if sources:
                    source_text = "\n\n*Sources:*\n" + "\n".join(sources)
            
            # Reset session stage to allow another question to the same bot
            session["stage"] = "asking_question"
            
            # Prepare response with emojis for better readability
            response_text = f"🔍 *Question:*\n{incoming_msg}\n\n📝 *Answer:*\n{answer}{source_text}\n\n_(Ask another question or type 'menu' to change legal domain)_"
            
            # Split long messages if needed (WhatsApp has a 1600 character limit)
            if len(response_text) > 1500:
                # Split the response into multiple messages
                parts = [response_text[i:i+1500] for i in range(0, len(response_text), 1500)]
                
                # Send the first part as the immediate response
                msg.body(parts[0])
                
                # Send subsequent parts using the Twilio API
                for part in parts[1:]:
                    twilio_client.messages.create(
                        body=part,
                        from_=request.values.get("To"),  # The WhatsApp number messages are coming into
                        to=sender
                    )
            else:
                msg.body(response_text)
                
        except Exception as e:
            logger.error(f"Error querying bot: {e}")
            msg.body(f"❌ Sorry, I encountered an error while processing your question. Please try again or type 'menu' to restart.")
            
    return str(resp)

@app.route("/")
def index():
    return "WhatsApp Legal Assistant Bot is running!"

if __name__ == "__main__":
    # Check if the required environment variables are set
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY environment variable not set")
        exit(1)
    
    if not account_sid or not auth_token:
        logger.error("TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN environment variable not set")
        exit(1)
    
    logger.info("WhatsApp bot server starting up...")
    # Run the Flask server
    app.run(host="0.0.0.0", port=5003, debug=True)
