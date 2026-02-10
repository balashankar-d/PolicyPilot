"""Text chunking module using LangChain's RecursiveCharacterTextSplitter."""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List
import logging

logger = logging.getLogger(__name__)


class TextChunker:
    """Handles text splitting into semantically coherent chunks."""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize the text chunker.
        
        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        self.logger = logger
    
    def split_text(self, text: str, source: str = "unknown") -> List[dict]:
        """
        Split text into chunks and create documents with metadata.
        
        Args:
            text: The text to split
            source: Source identifier (e.g., PDF filename)
            
        Returns:
            List of dictionaries containing chunk text, metadata, and IDs
        """
        try:
            if not text or not text.strip():
                raise ValueError("Empty text provided for chunking")
            
            # Split text into chunks
            chunks = self.splitter.split_text(text)
            
            if not chunks:
                raise ValueError("No chunks created from text")
            
            # Create document objects with metadata
            documents = []
            for i, chunk in enumerate(chunks):
                if chunk.strip():  # Only include non-empty chunks
                    doc = {
                        "text": chunk.strip(),
                        "id": f"{source}-{i}",
                        "metadata": {
                            "source": source,
                            "chunk_index": i,
                            "chunk_size": len(chunk)
                        }
                    }
                    documents.append(doc)
            
            self.logger.info(f"Created {len(documents)} chunks from {source}")
            return documents
            
        except Exception as e:
            self.logger.error(f"Error chunking text from {source}: {str(e)}")
            raise
