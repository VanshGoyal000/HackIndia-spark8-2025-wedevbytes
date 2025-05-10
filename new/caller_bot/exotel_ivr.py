from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import PlainTextResponse
import httpx
import logging
import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Exotel IVR System")

# Define the base URLs for APIs
TRANSLATOR_API = os.getenv("TRANSLATOR_API", "http://localhost:8000")
RAG_API_URL = os.getenv("RAG_API_URL", "http://localhost:8000") # RAG API URL

# Define answers for each option
answers = {
    1: "For Right to Information Act, you need to file an RTI application with the concerned Public Information Officer. The fee is generally Rs. 10, and you can expect a response within 30 days.",
    2: "Under Indian Penal Code, Section 420 deals with cheating and dishonestly inducing delivery of property, punishable with imprisonment up to 7 years and fine.",
    3: "For labor law matters, you can approach the labor commissioner or file a case in the labor court. You may also seek help from trade unions if available in your workplace.",
    4: "As per the Constitution of India, Article 32 provides the right to constitutional remedies, which allows citizens to move the Supreme Court for enforcement of fundamental rights."
}

# Exotel AppID and Secret for authentication
EXOTEL_APP_ID = os.getenv("EXOTEL_APP_ID")
EXOTEL_APP_SECRET = os.getenv("EXOTEL_APP_SECRET")

# Map numeric options to bot names
bot_mapping = {
    1: "RTI Bot",
    2: "IPC Bot",
    3: "Labor Law Bot",
    4: "Constitution Bot"
}

# Store user context
user_sessions = {}

# Generate welcome menu in various languages
async def generate_menu_audios():
    """Generate welcome and menu audio files in supported languages"""
    lang_clients = httpx.AsyncClient()
    
    welcome_text = {
        "english": "Welcome to the Legal Assistant. Press 1 for English, 2 for Hindi.",
        "hindi": "कानूनी सहायक में आपका स्वागत है। अंग्रेजी के लिए 1 दबाएं, हिंदी के लिए 2 दबाएं।"
    }
    
    menu_text = {
        "english": "Please select an option. Press 1 for RTI information. Press 2 for IPC information. Press 3 for labor laws. Press 4 for constitutional rights.",
        "hindi": "कृपया एक विकल्प चुनें। आरटीआई जानकारी के लिए 1 दबाएं। आईपीसी जानकारी के लिए 2 दबाएं। श्रम कानूनों के लिए 3 दबाएं। संवैधानिक अधिकारों के लिए 4 दबाएं।"
    }
    
    # Map to store audio file paths
    audio_files = {}
    
    for lang, text in welcome_text.items():
        try:
            # Create welcome audio
            response = await lang_clients.post(
                f"{TRANSLATOR_API}/translate/{lang}",
                json={"text": text}
            )
            response.raise_for_status()
            audio_files[f"welcome_{lang}"] = response.json()["audio_file"]
            
            # Create menu audio
            response = await lang_clients.post(
                f"{TRANSLATOR_API}/translate/{lang}",
                json={"text": menu_text[lang]}
            )
            response.raise_for_status()
            audio_files[f"menu_{lang}"] = response.json()["audio_file"]
            
            logger.info(f"Created menu audios for {lang}")
        except Exception as e:
            logger.error(f"Failed to create {lang} audios: {e}")
    
    await lang_clients.aclose()
    return audio_files

# Initialize audio files - will be populated during startup
menu_audios = {}

@app.on_event("startup")
async def startup_event():
    """Generate menu audios on startup"""
    global menu_audios
    try:
        menu_audios = await generate_menu_audios()
        logger.info("Generated menu audio files")
    except Exception as e:
        logger.error(f"Failed to generate menu audios: {e}")

@app.get("/")
def read_root():
    return {"message": "Exotel IVR System is running"}

@app.post("/ivr/welcome")
async def welcome_ivr(
    CallSid: str = Form(...),
    From: str = Form(...),
    digits_entered: str = Form(None)
):
    """Initial welcome message and language selection"""
    logger.info(f"Call from {From}, CallSid: {CallSid}, digits: {digits_entered}")
    
    # If no digits entered, play welcome message
    if not digits_entered:
        # Construct Exotel OBD flow XML to play welcome and gather digits
        welcome_audio = menu_audios.get("welcome_english", "")
        
        response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Play>{TRANSLATOR_API}/audio/{welcome_audio}</Play>
            <GetDigits timeout="5" numDigits="1" callbackUrl="{request.url}"/>
        </Response>
        """
        return PlainTextResponse(content=response_xml, media_type="application/xml")
    
    # Process language selection
    lang = "english" if digits_entered == "1" else "hindi" if digits_entered == "2" else "english"
    
    # Play menu options in selected language
    menu_audio = menu_audios.get(f"menu_{lang}", "")
    
    response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Play>{TRANSLATOR_API}/audio/{menu_audio}</Play>
        <GetDigits timeout="5" numDigits="1" callbackUrl="/ivr/menu/{lang}"/>
    </Response>
    """
    return PlainTextResponse(content=response_xml, media_type="application/xml")

@app.post("/ivr/menu/{language}")
async def menu_selection(
    language: str,
    CallSid: str = Form(...),
    From: str = Form(...),
    digits_entered: str = Form(None)
):
    """Process menu selection and play appropriate answer"""
    logger.info(f"Menu selection for {language}, CallSid: {CallSid}, Digits: {digits_entered}")
    
    # Validate input
    if not digits_entered or digits_entered not in ["1", "2", "3", "4"]:
        # Invalid or no input, replay menu
        menu_audio = menu_audios.get(f"menu_{language}", "")
        
        response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say>Invalid selection.</Say>
            <Play>{TRANSLATOR_API}/audio/{menu_audio}</Play>
            <GetDigits timeout="5" numDigits="1" callbackUrl="/ivr/menu/{language}"/>
        </Response>
        """
        return PlainTextResponse(content=response_xml, media_type="application/xml")
    
    # Store the selected bot in the session
    option_num = int(digits_entered)
    selected_bot = bot_mapping.get(option_num)
    
    user_sessions[CallSid] = {
        "selected_bot": selected_bot,
        "language": language
    }
    
    # Prompt user to ask a question
    prompt_text = {
        "english": f"You've selected {selected_bot}. Please ask your question after the beep.",
        "hindi": f"आपने {selected_bot} का चयन किया है। कृपया बीप के बाद अपना सवाल पूछें।"
    }.get(language, f"You've selected {selected_bot}. Please ask your question after the beep.")

    try:
        # Get translated prompt
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TRANSLATOR_API}/translate/{language}",
                json={"text": prompt_text}
            )
            response.raise_for_status()
            prompt_data = response.json()
            audio_file = prompt_data["audio_file"]
            
            # Ask user to record their question
            response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Play>{TRANSLATOR_API}/audio/{audio_file}</Play>
                <Record maxLength="30" playBeep="true" callbackUrl="/ivr/process_question/{CallSid}"/>
            </Response>
            """
            return PlainTextResponse(content=response_xml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error creating prompt: {e}")
        
        # Fallback response
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say>Sorry, we couldn't process your request. Please try again later.</Say>
            <Hangup/>
        </Response>
        """
        return PlainTextResponse(content=response_xml, media_type="application/xml")

@app.post("/ivr/process_question/{call_sid}")
async def process_question(
    call_sid: str,
    CallSid: str = Form(...),
    From: str = Form(...),
    RecordingUrl: str = Form(None),
    RecordingStatus: str = Form(None)
):
    """Process the recorded question and get answer from RAG"""
    logger.info(f"Processing question for Call: {call_sid}, Recording: {RecordingUrl}, Status: {RecordingStatus}")
    
    if RecordingStatus != "completed" or not RecordingUrl:
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say>We couldn't record your question. Please try again later.</Say>
            <Hangup/>
        </Response>
        """
        return PlainTextResponse(content=response_xml, media_type="application/xml")
    
    try:
        # Get session data
        session = user_sessions.get(call_sid, {})
        selected_bot = session.get("selected_bot")
        language = session.get("language", "english")
        
        if not selected_bot:
            raise ValueError("No bot selected for this call")
        
        # 1. Convert speech to text
        async with httpx.AsyncClient() as client:
            # Send recording to speech-to-text service
            stt_response = await client.post(
                f"{RAG_API_URL}/speech-to-text",
                json={"audio_url": RecordingUrl, "language": language}
            )
            stt_response.raise_for_status()
            stt_data = stt_response.json()
            question_text = stt_data["text"]
            
            logger.info(f"Transcribed question: {question_text}")
            
            # 2. Query RAG API with the question
            rag_response = await client.post(
                f"{RAG_API_URL}/bots/{selected_bot}/query",
                json={"query": question_text}
            )
            rag_response.raise_for_status()
            rag_data = rag_response.json()
            answer_text = rag_data["answer"]
            
            # 3. Convert answer to speech in the selected language
            tts_response = await client.post(
                f"{RAG_API_URL}/text-to-speech",
                json={"text": answer_text, "language": language}
            )
            tts_response.raise_for_status()
            tts_data = tts_response.json()
            audio_file = tts_data["audio_file"]
            
            # 4. Play the answer to the user with option to ask another question
            response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Play>{RAG_API_URL}/audio/{audio_file}</Play>
                <Gather numDigits="1" timeout="5" action="/ivr/after_answer/{call_sid}">
                    <Say>Press 1 to ask another question. Press 2 to end the call.</Say>
                </Gather>
                <Say>Thank you for using our service. Goodbye.</Say>
                <Hangup/>
            </Response>
            """
            return PlainTextResponse(content=response_xml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        
        # Fallback response
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say>Sorry, we couldn't process your question. Please try again later.</Say>
            <Hangup/>
        </Response>
        """
        return PlainTextResponse(content=response_xml, media_type="application/xml")

@app.post("/ivr/after_answer/{call_sid}")
async def after_answer(
    call_sid: str,
    CallSid: str = Form(...),
    From: str = Form(...),
    Digits: str = Form(None)
):
    """Handle user's choice after hearing the answer"""
    logger.info(f"After answer for Call: {call_sid}, Choice: {Digits}")
    
    session = user_sessions.get(call_sid, {})
    selected_bot = session.get("selected_bot")
    language = session.get("language", "english")
    
    if Digits == "1" and selected_bot:
        # User wants to ask another question
        prompt_text = {
            "english": "Please ask your next question after the beep.",
            "hindi": "कृपया बीप के बाद अपना अगला सवाल पूछें।"
        }.get(language, "Please ask your next question after the beep.")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{TRANSLATOR_API}/translate/{language}",
                    json={"text": prompt_text}
                )
                response.raise_for_status()
                prompt_data = response.json()
                audio_file = prompt_data["audio_file"]
                
                # Ask user to record their next question
                response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
                <Response>
                    <Play>{TRANSLATOR_API}/audio/{audio_file}</Play>
                    <Record maxLength="30" playBeep="true" callbackUrl="/ivr/process_question/{call_sid}"/>
                </Response>
                """
                return PlainTextResponse(content=response_xml, media_type="application/xml")
        except Exception as e:
            logger.error(f"Error creating prompt: {e}")
    
    # Default: end call
    goodbye_text = {
        "english": "Thank you for using our Legal Assistant. Goodbye.",
        "hindi": "हमारे लीगल असिस्टेंट का उपयोग करने के लिए धन्यवाद। अलविदा।"
    }.get(language, "Thank you for using our Legal Assistant. Goodbye.")
    
    response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say>{goodbye_text}</Say>
        <Hangup/>
    </Response>
    """
    return PlainTextResponse(content=response_xml, media_type="application/xml")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if RAG API is accessible
        async with httpx.AsyncClient() as client:
            rag_health = await client.get(f"{RAG_API_URL}/health", timeout=2.0)
            rag_health.raise_for_status()
            
        return {
            "status": "healthy",
            "rag_api": "connected",
            "sessions_active": len(user_sessions)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "error": str(e),
            "sessions_active": len(user_sessions)
        }

if __name__ == "__main__":
    uvicorn.run("exotel_ivr:app", host="0.0.0.0", port=8080, reload=True)
