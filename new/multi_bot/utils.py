import os
import logging
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from prompts.domain_prompts import BOT_PROMPTS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LegalBotManager:
    """Manager for legal domain-specific bots."""
    
    def __init__(self, google_api_key=None):
        """Initialize the legal bot manager."""
        # Set Google API key if provided
        if google_api_key:
            os.environ["GOOGLE_API_KEY"] = google_api_key
        
        # Check if API key is set
        if "GOOGLE_API_KEY" not in os.environ:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        # Initialize embeddings
        self.embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)
        
        # Vector store paths
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.vector_stores_dir = os.path.join(self.base_path, "vectorstores")
        
        # Domain mapping
        self.domain_mapping = {
            "IPC Bot": "ipc",
            "RTI Bot": "rti",
            "Labor Law Bot": "labor_law",
            "Constitution Bot": "constitution"
        }
        
        # Available bots
        self.available_bots = []
        self._check_available_bots()
        
    def _check_available_bots(self):
        """Check which bots have vector stores available."""
        self.available_bots = []
        
        for bot_name, domain in self.domain_mapping.items():
            vector_store_path = os.path.join(self.vector_stores_dir, f"{domain}_index")
            if os.path.exists(vector_store_path) and os.path.isdir(vector_store_path):
                self.available_bots.append(bot_name)
        
        logger.info(f"Available bots: {', '.join(self.available_bots)}")
    
    def get_bot(self, bot_name):
        """Get a specific bot by name."""
        if bot_name not in self.domain_mapping:
            raise ValueError(f"Unknown bot: {bot_name}")
        
        domain = self.domain_mapping[bot_name]
        vector_store_path = os.path.join(self.vector_stores_dir, f"{domain}_index")
        
        if not os.path.exists(vector_store_path):
            raise ValueError(f"Vector store for {bot_name} not found at {vector_store_path}")
        
        # Load vector store
        vector_store = Chroma(
            persist_directory=vector_store_path,
            embedding_function=self.embedding
        )
        
        # Get prompt template for this bot
        prompt_template = BOT_PROMPTS[bot_name]
        
        # Create QA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=vector_store.as_retriever(search_kwargs={"k": 4}),
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt_template}
        )
        
        return qa_chain
    
    def get_available_bots(self):
        """Get list of available bots."""
        return self.available_bots
    
    def query_bot(self, bot_name, query):
        """Query a specific bot."""
        if bot_name not in self.available_bots:
            raise ValueError(f"Bot {bot_name} is not available")
        
        logger.info(f"Querying {bot_name} with: '{query}'")
        qa_chain = self.get_bot(bot_name)
        
        try:
            result = qa_chain.invoke({"query": query})
            return result
        except Exception as e:
            logger.error(f"Error querying bot: {e}")
            raise
