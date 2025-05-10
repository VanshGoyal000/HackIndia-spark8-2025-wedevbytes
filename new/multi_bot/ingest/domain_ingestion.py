import logging
# Use a relative import with dot notation to import from the same package
from .base_ingestion import BaseDocumentIngestion

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IPCDocumentIngestion(BaseDocumentIngestion):
    """Document ingestion for Indian Penal Code (IPC)."""
    
    def __init__(self, data_dir="data", vector_store_dir="vectorstores"):
        super().__init__("ipc", data_dir, vector_store_dir)
        logger.info("IPC Document Ingestion initialized")
        
    def load_documents(self):
        """Load IPC-specific documents."""
        documents = super().load_documents()
        logger.info(f"Loaded {len(documents)} IPC documents")
        return documents


class RTIDocumentIngestion(BaseDocumentIngestion):
    """Document ingestion for Right to Information (RTI)."""
    
    def __init__(self, data_dir="data", vector_store_dir="vectorstores"):
        super().__init__("rti", data_dir, vector_store_dir)
        logger.info("RTI Document Ingestion initialized")


class LaborLawDocumentIngestion(BaseDocumentIngestion):
    """Document ingestion for Labor Laws."""
    
    def __init__(self, data_dir="data", vector_store_dir="vectorstores"):
        super().__init__("labor_law", data_dir, vector_store_dir)
        logger.info("Labor Law Document Ingestion initialized")


class ConstitutionDocumentIngestion(BaseDocumentIngestion):
    """Document ingestion for Constitution of India."""
    
    def __init__(self, data_dir="data", vector_store_dir="vectorstores"):
        super().__init__("constitution", data_dir, vector_store_dir)
        logger.info("Constitution Document Ingestion initialized")
