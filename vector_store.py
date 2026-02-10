"""Vector store module using ChromaDB for document storage and retrieval."""

import chromadb
from typing import List, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)


class VectorStore:
    """Handles document storage and retrieval using ChromaDB."""
    
    def __init__(self, persist_directory: str = "db/"):
        """
        Initialize ChromaDB client with persistence.
        
        Args:
            persist_directory: Directory to persist the database
        """
        self.persist_directory = persist_directory
        self.logger = logger
        
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        try:
            # Initialize ChromaDB client with the new configuration format
            self.client = chromadb.PersistentClient(path=persist_directory)
            
            # Get or create collection for documents
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"description": "RAG chatbot document collection"}
            )
            
            self.logger.info(f"Initialized ChromaDB with persistence at {persist_directory}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of document dictionaries with 'text', 'id', and 'metadata'
        """
        try:
            if not documents:
                raise ValueError("No documents provided")
            
            # Extract components for ChromaDB
            texts = [doc["text"] for doc in documents]
            ids = [doc["id"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]
            
            # Add to ChromaDB collection
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            self.logger.info(f"Added {len(documents)} documents to vector store")
            
        except Exception as e:
            self.logger.error(f"Error adding documents to vector store: {str(e)}")
            raise
    
    def query(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Query the vector store for similar documents.
        
        Args:
            query_text: Query text to search for
            n_results: Number of top results to return
            
        Returns:
            Dictionary containing retrieved documents and metadata
        """
        try:
            if not query_text or not query_text.strip():
                raise ValueError("Empty query provided")
            
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query_text.strip()],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            if results['documents'] and results['documents'][0]:
                retrieved_docs = {
                    "documents": results['documents'][0],
                    "metadatas": results['metadatas'][0],
                    "distances": results['distances'][0] if 'distances' in results else None
                }
                
                self.logger.info(f"Retrieved {len(retrieved_docs['documents'])} documents for query")
                return retrieved_docs
            else:
                self.logger.warning("No documents found for query")
                return {"documents": [], "metadatas": [], "distances": []}
                
        except Exception as e:
            self.logger.error(f"Error querying vector store: {str(e)}")
            raise
    
    def get_collection_count(self) -> int:
        """Get the total number of documents in the collection."""
        try:
            return self.collection.count()
        except Exception as e:
            self.logger.error(f"Error getting collection count: {str(e)}")
            return 0
    
    def clear_collection(self) -> None:
        """Clear all documents from the collection."""
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name="documents")
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"description": "RAG chatbot document collection"}
            )
            self.logger.info("Cleared all documents from vector store")
        except Exception as e:
            self.logger.error(f"Error clearing collection: {str(e)}")
            raise
