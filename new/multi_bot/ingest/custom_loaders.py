import os
import glob
from typing import List, Dict, Any, Optional
from langchain.docstore.document import Document
import logging
from pypdf import PdfReader

logger = logging.getLogger(__name__)

class SimpleTextLoader:
    """Load text files."""
    
    def __init__(self, file_path: str):
        """Initialize with file path."""
        self.file_path = file_path
        
    def load(self) -> List[Document]:
        """Load text file."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            metadata = {"source": self.file_path}
            return [Document(page_content=text, metadata=metadata)]
        except Exception as e:
            logger.error(f"Error loading text file {self.file_path}: {e}")
            return []

class SimplePdfLoader:
    """Load PDFs using PyPDF."""
    
    def __init__(self, file_path: str):
        """Initialize with file path."""
        self.file_path = file_path
    
    def load(self) -> List[Document]:
        """Load PDF file."""
        try:
            pdf = PdfReader(self.file_path)
            documents = []
            
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text.strip():  # Skip empty pages
                    metadata = {"source": self.file_path, "page": i}
                    documents.append(Document(page_content=text, metadata=metadata))
            
            return documents
        except Exception as e:
            logger.error(f"Error loading PDF {self.file_path}: {e}")
            return []

class SimpleDirectoryLoader:
    """Load documents from a directory."""
    
    def __init__(self, directory: str, glob: str = "**/*", loader_cls=None):
        """Initialize with directory and glob pattern."""
        self.directory = directory
        self.glob_pattern = glob  # store internally as glob_pattern
        self.loader_cls = loader_cls
    
    def load(self) -> List[Document]:
        """Load all documents matching the pattern from the directory."""
        documents = []
        pattern = os.path.join(self.directory, self.glob_pattern)
        
        for file_path in glob.glob(pattern, recursive=True):
            if not os.path.isfile(file_path):
                continue
                
            try:
                if self.loader_cls:
                    loader = self.loader_cls(file_path)
                    docs = loader.load()
                    documents.extend(docs)
            except Exception as e:
                logger.error(f"Error loading file {file_path}: {e}")
        
        return documents
