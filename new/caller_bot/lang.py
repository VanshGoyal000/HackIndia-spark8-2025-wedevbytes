from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline
from gtts import gTTS
import logging
import uuid
import os
from fastapi.responses import FileResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Indian Language Translator API")

class TextIn(BaseModel):
    text: str

# Supported language to model map
language_models = {
    "hindi": "Helsinki-NLP/opus-mt-en-hi",
    "malayalam": "Helsinki-NLP/opus-mt-en-ml",
    "marathi": "Helsinki-NLP/opus-mt-en-mr",
    "urdu": "Helsinki-NLP/opus-mt-en-ur",
}

# Preload models
translators = {
    lang: pipeline("translation", model=model)
    for lang, model in language_models.items()
}

@app.get("/")
def read_root():
    return {"message": "Translator API is running"}

@app.post("/translate/{lang}")
async def translate_text_endpoint(lang: str, text_in: TextIn):
    translator = translators.get(lang)
    if not translator:
        logger.error(f"Model for '{lang}' could not be loaded or is unsupported.")
        raise HTTPException(status_code=400, detail=f"Model for '{lang}' could not be loaded or is unsupported.")

    input_text = text_in.text
    words = input_text.split()
    max_words = 100
    translated_text = ""

    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i+max_words])
        try:
            logger.info(f"Translating words {i+1} to {min(i+max_words, len(words))}")
            translated = translator(chunk, max_length=512)
            translated_text += translated[0]['translation_text'] + " "
        except Exception as e:
            logger.error(f"Translation failed for words {i+1}-{i+max_words} with error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Translation failed for words {i+1}-{i+max_words}.")

    translated_text = translated_text.strip()

    # Convert to speech
    try:
        tts = gTTS(text=translated_text, lang='hi' if lang == 'hindi' else 'ur' if lang == 'urdu' else 'ml' if lang == 'malayalam' else 'mr')
        file_name = f"tts_{uuid.uuid4().hex}.mp3"
        tts.save(file_name)
    except Exception as e:
        logger.error(f"TTS conversion failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Text-to-speech conversion failed.")

    return {
        "language": lang.capitalize(),
        "translated_text": translated_text,
        "audio_file": file_name
    }

@app.get("/audio/{file_name}")
async def get_audio(file_name: str):
    path = f"./{file_name}"
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/mpeg", filename=file_name)
    else:
        raise HTTPException(status_code=404, detail="Audio file not found")