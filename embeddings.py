"""Embeddings module using Sentence Transformers."""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
import logging

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Handles text embedding using Sentence Transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding model.
        
        Args:
            model_name: Name of the Sentence Transformers model to use
        """
        self.model_name = model_name
        self.logger = logger
        
        try:
            self.model = SentenceTransformer(model_name)
            self.logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            self.logger.error(f"Failed to load embedding model {model_name}: {str(e)}")
            raise
    
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Encode text(s) into embeddings.
        
        Args:
            texts: Single text string or list of text strings
            
        Returns:
            Numpy array of embeddings
        """
        try:
            if isinstance(texts, str):
                texts = [texts]
            
            if not texts or not any(text.strip() for text in texts):
                raise ValueError("No valid text provided for encoding")
            
            embeddings = self.model.encode(texts)
            self.logger.debug(f"Generated embeddings for {len(texts)} texts")
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    def encode_query(self, query: str) -> np.ndarray:
        """
        Encode a single query text.
        
        Args:
            query: Query text to encode
            
        Returns:
            Numpy array of the query embedding
        """
        if not query or not query.strip():
            raise ValueError("Empty query provided for encoding")
        
        return self.encode(query.strip())[0]
