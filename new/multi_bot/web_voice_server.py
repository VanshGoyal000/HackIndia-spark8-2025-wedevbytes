from flask import Flask, request, jsonify, render_template
import os
import uuid
import base64
import tempfile
import logging
from google.cloud import speech
from utils import LegalBotManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the Flask application
app = Flask(__name__, template_folder='templates')

# Initialize Google Speech client
speech_client = speech.SpeechClient.from_service_account_json(
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
)

# Initialize bot manager
bot_manager = LegalBotManager(google_api_key=os.getenv("GOOGLE_API_KEY"))

# Available languages
LANGUAGES = {
    "1": {"code": "en-IN", "name": "English", "tts": "en-US", "speech_code": "en-IN"},
    "2": {"code": "hi-IN", "name": "Hindi", "tts": "hi-IN", "speech_code": "hi-IN"},
    "3": {"code": "ta-IN", "name": "Tamil", "tts": "ta-IN", "speech_code": "ta-IN"},
    "4": {"code": "te-IN", "name": "Telugu", "tts": "te-IN", "speech_code": "te-IN"},
    "5": {"code": "mr-IN", "name": "Marathi", "tts": "mr-IN", "speech_code": "mr-IN"}
}

# Available bots
LEGAL_BOTS = {
    "1": "IPC Bot",
    "2": "RTI Bot",
    "3": "Labor Law Bot",
    "4": "Constitution Bot"
}

# Session storage
web_sessions = {}

@app.route("/")
def index():
    """Render the voice interface."""
    return render_template("voice_interface.html")

@app.route("/web_session", methods=["POST"])
def create_session():
    """Create a new web session."""
    session_id = str(uuid.uuid4())
    web_sessions[session_id] = {
        "language": None,
        "selected_bot": None
    }
    
    logger.info(f"Created new web session: {session_id}")
    return jsonify({"success": True, "session_id": session_id})

@app.route("/web_set_language", methods=["POST"])
def set_language():
    """Set the language for a session."""
    data = request.json
    session_id = data.get("session_id")
    language_code = data.get("language_code")
    
    if not session_id or not language_code:
        return jsonify({"success": False, "error": "Missing session_id or language_code"})
    
    if session_id not in web_sessions:
        return jsonify({"success": False, "error": "Invalid session_id"})
    
    if language_code not in LANGUAGES:
        return jsonify({"success": False, "error": "Invalid language_code"})
    
    web_sessions[session_id]["language"] = LANGUAGES[language_code]
    logger.info(f"Set language to {LANGUAGES[language_code]['name']} for session {session_id}")
    
    return jsonify({"success": True})

@app.route("/web_set_bot", methods=["POST"])
def set_bot():
    """Set the bot for a session."""
    data = request.json
    session_id = data.get("session_id")
    bot_code = data.get("bot_code")
    
    if not session_id or not bot_code:
        return jsonify({"success": False, "error": "Missing session_id or bot_code"})
    
    if session_id not in web_sessions:
        return jsonify({"success": False, "error": "Invalid session_id"})
    
    if bot_code not in LEGAL_BOTS:
        return jsonify({"success": False, "error": "Invalid bot_code"})
    
    web_sessions[session_id]["selected_bot"] = LEGAL_BOTS[bot_code]
    logger.info(f"Set bot to {LEGAL_BOTS[bot_code]} for session {session_id}")
    
    return jsonify({"success": True})

@app.route("/web_process_audio", methods=["POST"])
def process_audio():
    """Process audio from the web interface."""
    data = request.json
    session_id = data.get("session_id")
    audio_b64 = data.get("audio")
    
    if not session_id or not audio_b64:
        return jsonify({"success": False, "error": "Missing session_id or audio"})
    
    if session_id not in web_sessions:
        return jsonify({"success": False, "error": "Invalid session_id"})
    
    session = web_sessions[session_id]
    
    if not session["language"] or not session["selected_bot"]:
        return jsonify({"success": False, "error": "Language or bot not selected"})
    
    try:
        # Extract base64 audio data (remove data URL prefix if present)
        if "," in audio_b64:
            audio_b64 = audio_b64.split(",", 1)[1]
        
        # Decode base64 audio
        audio_data = base64.b64decode(audio_b64)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_filename = temp_file.name
            temp_file.write(audio_data)
        
        try:
            # Transcribe using Google Speech-to-Text
            language_code = session["language"]["speech_code"]
            
            # Read the audio file
            with open(temp_filename, "rb") as audio_file:
                content = audio_file.read()
            
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,  # Standard WebM rate
                language_code=language_code,
                enable_automatic_punctuation=True
            )
            
            response = speech_client.recognize(config=config, audio=audio)
            
            # Extract transcription
            transcription = ""
            for result in response.results:
                transcription += result.alternatives[0].transcript
            
            logger.info(f"Transcription: {transcription}")
            
            # Query the bot
            bot_name = session["selected_bot"]
            language_name = session["language"]["name"]
            
            if bot_name in bot_manager.get_available_bots():
                # Add language instruction if not in English
                if language_name.lower() != "english":
                    query = f"Answer the following query in {language_name}: {transcription}"
                else:
                    query = transcription
                
                # Query the bot
                result = bot_manager.query_bot(bot_name, query)
                answer = result["result"]
                
                # Format sources for citation
                sources = []
                if result.get("source_documents"):
                    for i, doc in enumerate(result["source_documents"][:2]):  # Limit to 2 sources
                        source = doc.metadata.get("source", "").split("/")[-1]
                        page = doc.metadata.get("page", "")
                        if source and page:
                            sources.append({"source": source, "page": page})
                
                return jsonify({
                    "success": True,
                    "transcription": transcription,
                    "answer": answer,
                    "sources": sources
                })
            else:
                return jsonify({
                    "success": False,
                    "error": f"Bot {bot_name} not available",
                    "transcription": transcription
                })
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
                
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    # Check if the required API keys are set
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY environment variable not set")
        exit(1)
    
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.error("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        exit(1)
    
    logger.info("Web voice server starting up...")
    # Run the Flask server
    app.run(host="0.0.0.0", port=5002, debug=True)
