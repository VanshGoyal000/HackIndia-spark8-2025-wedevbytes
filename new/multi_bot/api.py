from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import os
import shutil
import logging
from utils import LegalBotManager
from ingest.domain_ingestion import (
    IPCDocumentIngestion,
    RTIDocumentIngestion, 
    LaborLawDocumentIngestion,
    ConstitutionDocumentIngestion
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Legal Assistant API",
    description="API for multi-domain legal assistant using RAG",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Check for API key
if "GOOGLE_API_KEY" not in os.environ:
    logger.error("GOOGLE_API_KEY environment variable not set")
    raise ValueError("GOOGLE_API_KEY environment variable not set")

# Create global bot manager instance
bot_manager = LegalBotManager(google_api_key=os.environ["GOOGLE_API_KEY"])

# Pydantic models for request/response
class QueryRequest(BaseModel):
    query: str
    
class IngestRequest(BaseModel):
    domain: str
    
class DocumentResponse(BaseModel):
    content: str
    metadata: Dict[str, Any]
    
class QueryResponse(BaseModel):
    answer: str
    sources: Optional[List[DocumentResponse]] = None
    
class BotInfoResponse(BaseModel):
    name: str
    description: str
    available: bool
    
class StatusResponse(BaseModel):
    status: str
    message: str

# Bot information
BOT_DESCRIPTIONS = {
    "IPC Bot": "Specialized in Indian Penal Code (IPC) sections, criminal offenses, and punishments.",
    "RTI Bot": "Expert on Right to Information (RTI) Act, filing procedures, and information access rights.",
    "Labor Law Bot": "Focused on Indian labor regulations, worker's rights, and workplace laws.",
    "Constitution Bot": "Knowledgeable about Indian Constitution, fundamental rights, and governance structure."
}

# Health check endpoint
@app.get("/health", response_model=StatusResponse, tags=["System"])
async def health_check():
    """Check if the API is running."""
    return StatusResponse(status="ok", message="API is running")

# Get available bots endpoint
@app.get("/bots", response_model=List[BotInfoResponse], tags=["Bots"])
async def get_available_bots():
    """Get list of all available bots."""
    available_bots = bot_manager.get_available_bots()
    
    bots_info = []
    for bot_name in BOT_DESCRIPTIONS.keys():
        bots_info.append(BotInfoResponse(
            name=bot_name,
            description=BOT_DESCRIPTIONS.get(bot_name, ""),
            available=bot_name in available_bots
        ))
    
    return bots_info

# Query bot endpoint
@app.post("/bots/{bot_name}/query", response_model=QueryResponse, tags=["Queries"])
async def query_bot(bot_name: str, request: QueryRequest):
    """Query a specific bot with a question."""
    if bot_name not in BOT_DESCRIPTIONS:
        raise HTTPException(status_code=404, detail=f"Bot '{bot_name}' not found")
        
    if bot_name not in bot_manager.get_available_bots():
        raise HTTPException(status_code=400, detail=f"Bot '{bot_name}' is not available. Documents need to be ingested first.")
    
    try:
        result = bot_manager.query_bot(bot_name, request.query)
        
        # Format source documents
        sources = []
        if "source_documents" in result:
            for doc in result["source_documents"]:
                sources.append(DocumentResponse(
                    content=doc.page_content,
                    metadata=doc.metadata
                ))
        
        return QueryResponse(
            answer=result["result"],
            sources=sources
        )
    except Exception as e:
        logger.error(f"Error querying bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background task for document ingestion
def ingest_documents(domain: str):
    """Background task to ingest documents for a domain."""
    try:
        if domain == "ipc":
            IPCDocumentIngestion().ingest()
        elif domain == "rti":
            RTIDocumentIngestion().ingest()
        elif domain == "labor_law":
            LaborLawDocumentIngestion().ingest()
        elif domain == "constitution":
            ConstitutionDocumentIngestion().ingest()
        else:
            logger.error(f"Unknown domain: {domain}")
            return
        
        # Refresh available bots
        bot_manager._check_available_bots()
        
    except Exception as e:
        logger.error(f"Error ingesting documents for {domain}: {e}")

# Endpoint to trigger document ingestion
@app.post("/ingest/{domain}", response_model=StatusResponse, tags=["Document Management"])
async def start_ingestion(domain: str, background_tasks: BackgroundTasks):
    """Start document ingestion for a specific domain."""
    valid_domains = ["ipc", "rti", "labor_law", "constitution", "all"]
    
    if domain not in valid_domains:
        raise HTTPException(status_code=400, detail=f"Invalid domain. Must be one of: {', '.join(valid_domains)}")
    
    if domain == "all":
        for d in ["ipc", "rti", "labor_law", "constitution"]:
            background_tasks.add_task(ingest_documents, d)
        return StatusResponse(
            status="processing",
            message="Document ingestion started for all domains"
        )
    else:
        background_tasks.add_task(ingest_documents, domain)
        return StatusResponse(
            status="processing",
            message=f"Document ingestion started for {domain}"
        )

# Upload document endpoint
@app.post("/upload", response_model=StatusResponse, tags=["Document Management"])
async def upload_document(
    file: UploadFile = File(...),
    domain: str = Form(...)
):
    """Upload a document file to a specific domain."""
    valid_domains = ["ipc", "rti", "labor_law", "constitution"]
    
    if domain not in valid_domains:
        raise HTTPException(status_code=400, detail=f"Invalid domain. Must be one of: {', '.join(valid_domains)}")
    
    # Check file type
    if file.filename.endswith(('.pdf', '.txt')):
        # Create directory if it doesn't exist
        domain_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", domain)
        os.makedirs(domain_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(domain_dir, file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        return StatusResponse(
            status="success",
            message=f"File uploaded successfully to {domain}. Run ingestion to process the document."
        )
    else:
        raise HTTPException(status_code=400, detail="Only PDF and text files are supported")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
