from flask import Flask, request, Response, render_template, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import os
import logging
from utils import LegalBotManager
from dotenv import load_dotenv
import openai
import requests
import tempfile
import time
import datetime
import base64
import uuid
from langchain_community.embeddings import HuggingFaceEmbeddings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the Flask application
app = Flask(__name__)

# Create templates and static directories if they don't exist
os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)

# Initialize OpenAI (for Whisper)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize bot manager
bot_manager = LegalBotManager(google_api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize Twilio client for sending SMS
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")

# Initialize Twilio client if credentials are provided
twilio_client = None
if twilio_account_sid and twilio_auth_token:
    twilio_client = Client(twilio_account_sid, twilio_auth_token)
    logger.info("Twilio client initialized for outbound communications")

# Available languages
LANGUAGES = {
    "1": {"code": "en-IN", "name": "English", "tts": "en-US"},
    "2": {"code": "hi-IN", "name": "Hindi", "tts": "hi-IN"},
    "3": {"code": "ta-IN", "name": "Tamil", "tts": "ta-IN"},
    "4": {"code": "te-IN", "name": "Telugu", "tts": "te-IN"},
    "5": {"code": "mr-IN", "name": "Marathi", "tts": "mr-IN"}
}

# Available bots
LEGAL_BOTS = {
    "1": "IPC Bot",
    "2": "RTI Bot",
    "3": "Labor Law Bot",
    "4": "Constitution Bot"
}

# Global session storage (in production, use a database)
call_sessions = {}

# Call analytics storage
call_analytics = {
    "total_calls": 0,
    "completed_queries": 0,
    "languages": {},
    "bots": {},
    "avg_response_time": 0,
    "total_response_time": 0
}

@app.route("/voice", methods=["POST"])
def voice():
    """Handle incoming voice calls."""
    # Get the caller's phone number
    caller_id = request.values.get("From", "Unknown")
    call_sid = request.values.get("CallSid", "Unknown")
    
    # Update call analytics
    call_analytics["total_calls"] += 1
    
    # Initialize or retrieve session
    if call_sid not in call_sessions:
        call_sessions[call_sid] = {
            "caller_id": caller_id,
            "language": None,
            "selected_bot": None,
            "start_time": datetime.datetime.now().isoformat()
        }
    
    # Create TwiML response
    response = VoiceResponse()
    response.say("Welcome to the Legal Assistant System.", voice="woman")
    
    # Ask for language preference
    gather = Gather(
        num_digits=1,
        action="/select_language",
        method="POST",
        timeout=10
    )
    gather.say(
        "Please select your language. "
        "Press 1 for English. "
        "Press 2 for Hindi. "
        "Press 3 for Tamil. "
        "Press 4 for Telugu. "
        "Press 5 for Marathi."
    )
    response.append(gather)
    
    # If no response, repeat the options
    response.redirect("/voice")
    
    return Response(str(response), mimetype="text/xml")

@app.route("/select_language", methods=["POST"])
def select_language():
    """Handle language selection."""
    # Get the digit pressed by the user
    digit = request.values.get("Digits", None)
    call_sid = request.values.get("CallSid", "Unknown")
    
    if digit in LANGUAGES:
        # Store the language preference
        call_sessions[call_sid]["language"] = LANGUAGES[digit]
        
        # Update analytics
        language_name = LANGUAGES[digit]["name"]
        call_analytics["languages"][language_name] = call_analytics["languages"].get(language_name, 0) + 1
        
        # Create TwiML response
        response = VoiceResponse()
        
        # Ask for bot selection
        gather = Gather(
            num_digits=1,
            action="/select_bot",
            method="POST",
            timeout=10
        )
        
        language_code = call_sessions[call_sid]["language"]["tts"]
        
        if language_code == "en-US":
            gather.say(
                "Please select a legal domain. "
                "Press 1 for Indian Penal Code. "
                "Press 2 for Right to Information. "
                "Press 3 for Labor Law. "
                "Press 4 for Constitution.",
                language=language_code
            )
        elif language_code == "hi-IN":
            gather.say(
                "कृपया एक कानूनी क्षेत्र चुनें। "
                "भारतीय दंड संहिता के लिए 1 दबाएं। "
                "सूचना के अधिकार के लिए 2 दबाएं। "
                "श्रम कानून के लिए 3 दबाएं। "
                "संविधान के लिए 4 दबाएं।",
                language=language_code
            )
        else:
            # For other languages, use English
            gather.say(
                "Please select a legal domain. "
                "Press 1 for Indian Penal Code. "
                "Press 2 for Right to Information. "
                "Press 3 for Labor Law. "
                "Press 4 for Constitution.",
                language="en-US"
            )
            
        response.append(gather)
        
        # If no response, repeat the options
        response.redirect("/select_language?Digits=" + digit)
        
        return Response(str(response), mimetype="text/xml")
    
    # Invalid selection
    response = VoiceResponse()
    response.say("Invalid selection. Please try again.")
    response.redirect("/voice")
    
    return Response(str(response), mimetype="text/xml")

@app.route("/select_bot", methods=["POST"])
def select_bot():
    """Handle bot selection."""
    # Get the digit pressed by the user
    digit = request.values.get("Digits", None)
    call_sid = request.values.get("CallSid", "Unknown")
    
    if digit in LEGAL_BOTS:
        # Store the bot selection
        call_sessions[call_sid]["selected_bot"] = LEGAL_BOTS[digit]
        
        # Create TwiML response
        response = VoiceResponse()
        
        language_code = call_sessions[call_sid]["language"]["tts"]
        bot_name = LEGAL_BOTS[digit]
        
        if language_code == "en-US":
            response.say(
                f"You have selected {bot_name}. "
                "Please ask your legal question after the beep. "
                "You will have 30 seconds for your question.",
                language=language_code
            )
        elif language_code == "hi-IN":
            response.say(
                f"आपने {bot_name} चुना है। "
                "कृपया बीप के बाद अपना कानूनी प्रश्न पूछें। "
                "आपके पास अपने प्रश्न के लिए 30 सेकंड होंगे।",
                language=language_code
            )
        else:
            # For other languages, use English
            response.say(
                f"You have selected {bot_name}. "
                "Please ask your legal question after the beep. "
                "You will have 30 seconds for your question.",
                language="en-US"
            )
        
        # Record the user's question
        response.record(
            action="/process_question",
            max_length=30,
            timeout=5,
            transcribe=False,  # We'll use our own transcription
            play_beep=True
        )
        
        return Response(str(response), mimetype="text/xml")
    
    # Invalid selection
    response = VoiceResponse()
    response.say("Invalid selection. Please try again.")
    response.redirect("/voice")
    
    return Response(str(response), mimetype="text/xml")

@app.route("/process_question", methods=["POST"])
def process_question():
    """Process the user's question."""
    recording_url = request.values.get("RecordingUrl")
    call_sid = request.values.get("CallSid", "Unknown")
    
    if not recording_url or call_sid not in call_sessions:
        response = VoiceResponse()
        response.say("Sorry, there was an error processing your question.")
        return Response(str(response), mimetype="text/xml")
    
    # Get session data
    session = call_sessions[call_sid]
    language_code = session["language"]["code"]
    language_name = session["language"]["name"]
    bot_name = session["selected_bot"]
    tts_code = session["language"]["tts"]
    
    # Create TwiML response with initial status
    response = VoiceResponse()
    if language_name.lower() == "english":
        response.say("Please wait while I process your question.", language=tts_code)
    elif language_name.lower() == "hindi":
        response.say("कृपया प्रतीक्षा करें जबकि मैं आपके प्रश्न पर काम कर रहा हूं।", language=tts_code)
    else:
        response.say("Please wait while I process your question.", language="en-US")
        
    # Play a brief hold music or comfort tone
    response.play("https://demo.twilio.com/docs/classic.mp3", loop=1)
    
    try:
        start_time = time.time()
        
        # Download and transcribe the audio (with status update)
        logger.info(f"Processing recording from {session['caller_id']}")
        if language_name.lower() == "english":
            response.say("Transcribing your question...", language=tts_code)
        elif language_name.lower() == "hindi":
            response.say("आपके प्रश्न को लिखित रूप में बदल रहा हूं...", language=tts_code)
            
        transcription = transcribe_audio(recording_url, language_name.lower())
        logger.info(f"Transcription: {transcription}")
        
        # Store transcription in session
        session["last_question"] = transcription
        
        # Update user on progress
        if language_name.lower() == "english":
            response.say("Searching for relevant legal information...", language=tts_code)
        elif language_name.lower() == "hindi":
            response.say("प्रासंगिक कानूनी जानकारी खोज रहा हूं...", language=tts_code)
            
        # Get answer from RAG system
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
                for i, doc in enumerate(result["source_documents"][:2]):  # Limit to 2 sources for voice
                    source = doc.metadata.get("source", "").split("/")[-1]
                    page = doc.metadata.get("page", "")
                    if source and page:
                        sources.append(f"Source {i+1}: {source}, page {page}")
            
            # Create source citation text
            if sources:
                source_text = ". ".join(sources)
                if language_name.lower() == "english":
                    answer += f". Based on: {source_text}"
                elif language_name.lower() == "hindi":
                    answer += f". आधारित: {source_text}"
                # Add other languages if needed
                
            # Store answer in session
            session["last_answer"] = answer
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Update analytics
            call_analytics["completed_queries"] += 1
            call_analytics["total_response_time"] += response_time
            call_analytics["avg_response_time"] = (
                call_analytics["total_response_time"] / call_analytics["completed_queries"]
            )
            
            # Log bot usage
            call_analytics["bots"][bot_name] = call_analytics["bots"].get(bot_name, 0) + 1
            
            # Respond with the answer
            response = VoiceResponse()
            
            # Inform user their question is answered
            if language_name.lower() == "english":
                response.say(
                    f"Here's the answer to your question: '{transcription}'", 
                    language=tts_code
                )
            elif language_name.lower() == "hindi":
                response.say(
                    f"आपके प्रश्न का उत्तर यहां है: '{transcription}'", 
                    language=tts_code
                )
                
            # Provide the answer
            response.say(answer, language=tts_code, voice="woman")
            
            # Offer to send answer via SMS
            if twilio_client and session["caller_id"] != "Unknown":
                gather = Gather(
                    num_digits=1,
                    action="/send_sms",
                    method="POST",
                    timeout=5
                )
                
                if language_name.lower() == "english":
                    gather.say(
                        "To receive this answer as a text message, press 1.",
                        language=tts_code
                    )
                elif language_name.lower() == "hindi":
                    gather.say(
                        "इस उत्तर को एसएमएस के रूप में प्राप्त करने के लिए 1 दबाएं।",
                        language=tts_code
                    )
                else:
                    gather.say(
                        "To receive this answer as a text message, press 1.",
                        language="en-US"
                    )
                    
                response.append(gather)
            
        else:
            # Bot not available
            response = VoiceResponse()
            if language_name.lower() == "english":
                response.say(f"Sorry, the {bot_name} is not available at this time.", language=tts_code)
            elif language_name.lower() == "hindi":
                response.say(f"क्षमा करें, {bot_name} इस समय उपलब्ध नहीं है।", language=tts_code)
            else:
                response.say(f"Sorry, the {bot_name} is not available at this time.", language="en-US")
        
        # Add option to ask another question
        gather = Gather(
            num_digits=1,
            action="/another_question",
            method="POST",
            timeout=10
        )
        
        if tts_code == "en-US":
            gather.say(
                "To ask another question, press 1. "
                "To end this call, press 2.",
                language=tts_code
            )
        elif tts_code == "hi-IN":
            gather.say(
                "एक और प्रश्न पूछने के लिए 1 दबाएं। "
                "इस कॉल को समाप्त करने के लिए 2 दबाएं।",
                language=tts_code
            )
        else:
            gather.say(
                "To ask another question, press 1. "
                "To end this call, press 2.",
                language="en-US"
            )
            
        response.append(gather)
        
        return Response(str(response), mimetype="text/xml")
        
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        response = VoiceResponse()
        response.say("Sorry, there was an error processing your question.")
        return Response(str(response), mimetype="text/xml")

@app.route("/send_sms", methods=["POST"])
def send_sms():
    """Send the answer as an SMS to the caller."""
    digit = request.values.get("Digits", None)
    call_sid = request.values.get("CallSid", "Unknown")
    
    response = VoiceResponse()
    
    if digit == "1" and call_sid in call_sessions and twilio_client:
        session = call_sessions[call_sid]
        
        if "last_answer" in session and session["caller_id"] != "Unknown":
            try:
                # Format SMS message
                question = session.get("last_question", "Your legal question")
                answer = session["last_answer"]
                
                # Shorten answer if too long for SMS
                max_sms_length = 1500  # Allow for multi-part SMS
                if len(answer) > max_sms_length:
                    answer = answer[:max_sms_length - 3] + "..."
                
                message = f"Your legal question: {question}\n\nAnswer: {answer}\n\n- Legal Assistant"
                
                # Send SMS
                twilio_client.messages.create(
                    body=message,
                    from_=twilio_phone_number,
                    to=session["caller_id"]
                )
                
                language_code = session["language"]["tts"]
                
                if language_code == "en-US":
                    response.say("Answer sent to your phone as a text message.", language=language_code)
                elif language_code == "hi-IN":
                    response.say("उत्तर आपके फोन पर एसएमएस के रूप में भेजा गया है।", language=language_code)
                else:
                    response.say("Answer sent to your phone as a text message.", language="en-US")
                    
            except Exception as e:
                logger.error(f"Error sending SMS: {e}")
                response.say("Sorry, couldn't send the text message.")
        else:
            response.say("Sorry, couldn't send the text message.")
    
    # Continue to ask if they want another question
    gather = Gather(
        num_digits=1,
        action="/another_question",
        method="POST",
        timeout=10
    )
    
    if call_sid in call_sessions:
        language_code = call_sessions[call_sid]["language"]["tts"]
        
        if language_code == "en-US":
            gather.say(
                "To ask another question, press 1. "
                "To end this call, press 2.",
                language=language_code
            )
        elif language_code == "hi-IN":
            gather.say(
                "एक और प्रश्न पूछने के लिए 1 दबाएं। "
                "इस कॉल को समाप्त करने के लिए 2 दबाएं।",
                language=language_code
            )
        else:
            gather.say(
                "To ask another question, press 1. "
                "To end this call, press 2.",
                language="en-US"
            )
    else:
        gather.say(
            "To ask another question, press 1. "
            "To end this call, press 2."
        )
        
    response.append(gather)
    
    return Response(str(response), mimetype="text/xml")

@app.route("/another_question", methods=["POST"])
def another_question():
    """Handle request for another question."""
    digit = request.values.get("Digits", None)
    call_sid = request.values.get("CallSid", "Unknown")
    
    if digit == "1":
        # Go back to bot selection
        response = VoiceResponse()
        
        # Ask for bot selection
        gather = Gather(
            num_digits=1,
            action="/select_bot",
            method="POST",
            timeout=10
        )
        
        if call_sid in call_sessions:
            language_code = call_sessions[call_sid]["language"]["tts"]
            
            if language_code == "en-US":
                gather.say(
                    "Please select a legal domain. "
                    "Press 1 for Indian Penal Code. "
                    "Press 2 for Right to Information. "
                    "Press 3 for Labor Law. "
                    "Press 4 for Constitution.",
                    language=language_code
                )
            elif language_code == "hi-IN":
                gather.say(
                    "कृपया एक कानूनी क्षेत्र चुनें। "
                    "भारतीय दंड संहिता के लिए 1 दबाएं। "
                    "सूचना के अधिकार के लिए 2 दबाएं। "
                    "श्रम कानून के लिए 3 दबाएं। "
                    "संविधान के लिए 4 दबाएं।",
                    language=language_code
                )
            else:
                gather.say(
                    "Please select a legal domain. "
                    "Press 1 for Indian Penal Code. "
                    "Press 2 for Right to Information. "
                    "Press 3 for Labor Law. "
                    "Press 4 for Constitution.",
                    language="en-US"
                )
        else:
            gather.say(
                "Please select a legal domain. "
                "Press 1 for Indian Penal Code. "
                "Press 2 for Right to Information. "
                "Press 3 for Labor Law. "
                "Press 4 for Constitution."
            )
            
        response.append(gather)
        
        return Response(str(response), mimetype="text/xml")
    else:
        # End the call
        response = VoiceResponse()
        
        if call_sid in call_sessions:
            language_code = call_sessions[call_sid]["language"]["tts"]
            
            if language_code == "en-US":
                response.say("Thank you for using the Legal Assistant. Goodbye.", language=language_code)
            elif language_code == "hi-IN":
                response.say("कानूनी सहायक का उपयोग करने के लिए धन्यवाद। अलविदा।", language=language_code)
            else:
                response.say("Thank you for using the Legal Assistant. Goodbye.", language="en-US")
        else:
            response.say("Thank you for using the Legal Assistant. Goodbye.")
            
        # Clean up the session
        if call_sid in call_sessions:
            del call_sessions[call_sid]
            
        return Response(str(response), mimetype="text/xml")

@app.route("/call_stats", methods=["GET"])
def call_stats():
    """API endpoint to get call statistics."""
    return call_analytics

# Web sessions for browser-based interaction
web_sessions = {}

# Add routes for web-based voice interaction
@app.route("/", methods=["GET"])
def index():
    """Render the web interface for voice interaction."""
    return render_template("voice_interface.html", 
                          available_bots=list(LEGAL_BOTS.values()),
                          available_languages=LANGUAGES)

@app.route("/web_session", methods=["POST"])
def create_web_session():
    """Create a new web session for browser-based interaction."""
    session_id = str(uuid.uuid4())
    web_sessions[session_id] = {
        "language": None,
        "selected_bot": None,
        "start_time": datetime.datetime.now().isoformat()
    }
    return jsonify({"session_id": session_id})

@app.route("/web_set_language", methods=["POST"])
def web_set_language():
    """Set language preference for web session."""
    data = request.json
    session_id = data.get("session_id")
    language_code = data.get("language_code")  # e.g., "2" for Hindi
    
    if not session_id or session_id not in web_sessions:
        return jsonify({"error": "Invalid session"}), 400
    
    if language_code not in LANGUAGES:
        return jsonify({"error": "Invalid language"}), 400
    
    web_sessions[session_id]["language"] = LANGUAGES[language_code]
    
    # Update analytics
    language_name = LANGUAGES[language_code]["name"]
    call_analytics["languages"][language_name] = call_analytics["languages"].get(language_name, 0) + 1
    
    return jsonify({"success": True, "language": LANGUAGES[language_code]["name"]})

@app.route("/web_set_bot", methods=["POST"])
def web_set_bot():
    """Set bot selection for web session."""
    data = request.json
    session_id = data.get("session_id")
    bot_code = data.get("bot_code")  # e.g., "1" for IPC Bot
    
    if not session_id or session_id not in web_sessions:
        return jsonify({"error": "Invalid session"}), 400
    
    if bot_code not in LEGAL_BOTS:
        return jsonify({"error": "Invalid bot"}), 400
    
    web_sessions[session_id]["selected_bot"] = LEGAL_BOTS[bot_code]
    
    return jsonify({"success": True, "bot": LEGAL_BOTS[bot_code]})

@app.route("/web_process_audio", methods=["POST"])
def web_process_audio():
    """Process audio recording from web interface."""
    data = request.json
    session_id = data.get("session_id")
    audio_data = data.get("audio")  # Base64 encoded audio
    
    if not session_id or session_id not in web_sessions:
        return jsonify({"error": "Invalid session"}), 400
    
    if not audio_data:
        return jsonify({"error": "No audio data"}), 400
    
    session = web_sessions[session_id]
    language_name = session["language"]["name"]
    bot_name = session["selected_bot"]
    
    try:
        start_time = time.time()
        
        # Decode and save audio to a temporary file
        audio_bytes = base64.b64decode(audio_data.split(',')[1] if ',' in audio_data else audio_data)
        
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_filename = temp_file.name
            temp_file.write(audio_bytes)
        
        # Transcribe the audio
        with open(temp_filename, "rb") as audio_file:
            result = openai.Audio.transcribe(
                file=audio_file,
                model="whisper-1",
                language=language_name.lower()
            )
        
        transcription = result.text if hasattr(result, 'text') else result['text']
        
        # Clean up the temporary file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)
        
        # Store transcription in session
        session["last_question"] = transcription
        
        # Get answer from RAG system
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
                for i, doc in enumerate(result["source_documents"][:2]):
                    source = doc.metadata.get("source", "").split("/")[-1]
                    page = doc.metadata.get("page", "")
                    if source and page:
                        sources.append({"source": source, "page": page})
            
            # Store answer in session
            session["last_answer"] = answer
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Update analytics
            call_analytics["completed_queries"] += 1
            call_analytics["total_response_time"] += response_time
            call_analytics["avg_response_time"] = (
                call_analytics["total_response_time"] / call_analytics["completed_queries"]
            )
            call_analytics["bots"][bot_name] = call_analytics["bots"].get(bot_name, 0) + 1
            
            return jsonify({
                "success": True,
                "transcription": transcription,
                "answer": answer,
                "sources": sources
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Bot {bot_name} is not available"
            })
    
    except Exception as e:
        logger.error(f"Error processing web audio: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

# Update transcribe_audio function with more robust error handling
def transcribe_audio(audio_url, language):
    """
    Transcribe audio using OpenAI's Whisper API.
    
    Args:
        audio_url (str): URL of the audio file
        language (str): Language of the audio
        
    Returns:
        str: The transcribed text
    """
    # Add .mp3 to the Twilio URL to get downloadable URL
    mp3_url = audio_url + ".mp3"
    
    # Download the audio file (with retry logic)
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            response = requests.get(mp3_url, timeout=10)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            break
        except requests.exceptions.RequestException as e:
            retry_count += 1
            logger.warning(f"Retry {retry_count}/{max_retries} downloading audio: {e}")
            time.sleep(1)
            if retry_count == max_retries:
                logger.error(f"Failed to download audio after {max_retries} attempts")
                raise
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        temp_filename = temp_file.name
        temp_file.write(response.content)
    
    try:
        # Transcribe using OpenAI Whisper (with retry logic)
        retry_count = 0
        while retry_count < max_retries:
            try:
                with open(temp_filename, "rb") as audio_file:
                    result = openai.Audio.transcribe(
                        file=audio_file,
                        model="whisper-1",
                        language=language
                    )
                
                # Get the transcribed text
                text = result.text if hasattr(result, 'text') else result['text']
                return text
            except Exception as e:
                retry_count += 1
                logger.warning(f"Retry {retry_count}/{max_retries} transcribing audio: {e}")
                time.sleep(1)
                if retry_count == max_retries:
                    logger.error(f"Failed to transcribe audio after {max_retries} attempts")
                    raise
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

if __name__ == "__main__":
    # Check if the required API keys are set
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY environment variable not set")
        exit(1)
        
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set")
        exit(1)
    
    # Log Twilio configuration status
    if not (twilio_account_sid and twilio_auth_token and twilio_phone_number):
        logger.warning("Twilio credentials incomplete - SMS functionality disabled")
    else:
        logger.info(f"SMS functionality enabled using Twilio number: {twilio_phone_number}")
    
    logger.info("Voice server starting up...")
    # Run the Flask server
    app.run(host="0.0.0.0", port=5001, debug=True)
