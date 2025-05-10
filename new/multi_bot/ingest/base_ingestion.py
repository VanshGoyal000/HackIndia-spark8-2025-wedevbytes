import os
import logging
# Use our custom loaders instead of the problematic ones
from .custom_loaders import SimpleTextLoader as TextLoader
from .custom_loaders import SimplePdfLoader as PyPDFLoader
from .custom_loaders import SimpleDirectoryLoader as DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BaseDocumentIngestion:
    """Base class for domain-specific document ingestion."""
    
    def __init__(self, domain_name, data_dir="data", vector_store_dir="vectorstores"):
        """
        Initialize the document ingestion process.
        
        Args:
            domain_name (str): Name of the legal domain (e.g., "ipc", "rti")
            data_dir (str): Directory containing the source documents
            vector_store_dir (str): Directory to store the vector database
        """
        self.domain_name = domain_name
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), data_dir, domain_name)
        self.vector_store_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), vector_store_dir, f"{domain_name}_index")
        
        # Create directories if they don't exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.vector_store_dir, exist_ok=True)
        
        # Initialize the text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        
        # Initialize embeddings (using HuggingFace to avoid API key requirements)
        self.embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        logger.info(f"Initialized {domain_name} document ingestion")
        
    def load_documents(self):
        """Load documents from the data directory."""
        logger.info(f"Loading documents from {self.data_dir}")
        
        # Load PDFs
        pdf_loader = DirectoryLoader(self.data_dir, glob="**/*.pdf", loader_cls=PyPDFLoader)
        pdf_docs = pdf_loader.load()
        
        # Load text files
        text_loader = DirectoryLoader(self.data_dir, glob="**/*.txt", loader_cls=TextLoader)
        text_docs = text_loader.load()
        
        # Combine documents
        documents = pdf_docs + text_docs
        logger.info(f"Loaded {len(documents)} documents")
        
        return documents
    
    def process_documents(self, documents):
        """Split documents into chunks and create embeddings."""
        logger.info(f"Processing {len(documents)} documents")
        
        # Split text into chunks
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"Created {len(chunks)} text chunks")
        
        # Create vector store
        db = Chroma.from_documents(
            documents=chunks,
            embedding=self.embedding,
            persist_directory=self.vector_store_dir
        )
        
        # Persist the database
        db.persist()
        logger.info(f"Vector store created and persisted at {self.vector_store_dir}")
        
        return db
    
    def ingest(self):
        """Execute the complete ingestion process."""
        logger.info(f"Starting ingestion process for {self.domain_name}")
        
        # Load documents
        documents = self.load_documents()
        
        # Process documents
        if documents:
            db = self.process_documents(documents)
            return db
        else:
            logger.warning(f"No documents found in {self.data_dir}")
            return None
    
    def load_vector_store(self):
        """Load an existing vector store."""
        if os.path.exists(self.vector_store_dir):
            logger.info(f"Loading vector store from {self.vector_store_dir}")
            return Chroma(
                persist_directory=self.vector_store_dir,
                embedding_function=self.embedding
            )
        else:
            logger.error(f"Vector store not found at {self.vector_store_dir}")
            return None
