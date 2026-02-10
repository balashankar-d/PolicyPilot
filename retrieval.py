"""Retrieval module for RAG pipeline."""

from typing import List, Dict, Any, Optional
import logging
from vector_store import VectorStore
from embeddings import EmbeddingModel

logger = logging.getLogger(__name__)


class Retriever:
    """Handles document retrieval for RAG queries with user isolation support."""
    
    def __init__(self, vector_store: VectorStore, embedding_model: EmbeddingModel, 
                 top_k: int = 5, similarity_threshold: float = 0.1):
        """
        Initialize the retriever.
        
        Args:
            vector_store: ChromaDB vector store instance
            embedding_model: Sentence transformer embedding model
            top_k: Number of top documents to retrieve
            similarity_threshold: Minimum similarity score to consider relevant (lowered)
        """
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.logger = logger
    
    def retrieve_relevant_chunks(self, query: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieve relevant document chunks for a given query.
        
        Args:
            query: User's question/query
            user_id: Optional user ID for user-specific retrieval
            
        Returns:
            Dictionary with retrieved chunks and metadata
        """
        try:
            if not query or not query.strip():
                raise ValueError("Empty query provided")
            
            # Clean query
            clean_query = query.strip()
            
            # Query the vector store (with user_id for isolation)
            results = self.vector_store.query(
                query_text=clean_query,
                n_results=self.top_k,
                user_id=user_id
            )
            
            # Check if we got any results
            if not results["documents"]:
                self.logger.warning(f"No documents found for query: {clean_query[:50]}...")
                return {
                    "chunks": [],
                    "sources": [],
                    "is_relevant": False,
                    "message": "No relevant documents found"
                }
            
            # Filter by similarity if distances are available
            filtered_chunks = []
            filtered_sources = []
            
            for i, (doc, metadata) in enumerate(zip(results["documents"], results["metadatas"])):
                # Include all results for now (ChromaDB handles similarity internally)
                # In a production system, you might want to filter by distance threshold
                if doc.strip():  # Only include non-empty documents
                    filtered_chunks.append(doc)
                    filtered_sources.append(metadata.get("source", "unknown"))
            
            # Check if we have relevant results
            is_relevant = len(filtered_chunks) > 0
            
            if not is_relevant:
                self.logger.warning(f"No relevant chunks found for query: {clean_query[:50]}...")
                return {
                    "chunks": [],
                    "sources": [],
                    "is_relevant": False,
                    "message": "No sufficiently relevant documents found"
                }
            
            self.logger.info(f"Retrieved {len(filtered_chunks)} relevant chunks for query")
            
            return {
                "chunks": filtered_chunks,
                "sources": list(set(filtered_sources)),  # Unique sources
                "is_relevant": True,
                "message": f"Found {len(filtered_chunks)} relevant chunks"
            }
            
        except Exception as e:
            self.logger.error(f"Error retrieving chunks for query: {str(e)}")
            return {
                "chunks": [],
                "sources": [],
                "is_relevant": False,
                "message": "Error occurred during retrieval"
            }
    
    def format_context(self, chunks: List[str], conversation_history: str = "") -> str:
        """
        Format retrieved chunks into a context string for the LLM.
        
        Args:
            chunks: List of retrieved document chunks
            conversation_history: Optional formatted conversation history
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return conversation_history if conversation_history else ""
        
        # Combine chunks with clear separation
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"Document {i}:\n{chunk.strip()}")
        
        document_context = "\n\n".join(context_parts)
        
        # Include conversation history if available
        if conversation_history:
            return f"{conversation_history}\n\n---\n\nRelevant document content:\n{document_context}"
        
        return document_context
