"""Vector store module using ChromaDB for document storage and retrieval."""

import chromadb
from typing import List, Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)


class VectorStore:
    """Handles document storage and retrieval using ChromaDB with user isolation."""
    
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
            
            # Default collection for backward compatibility
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"description": "RAG chatbot document collection"}
            )
            
            self.logger.info(f"Initialized ChromaDB with persistence at {persist_directory}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise
    
    def _get_user_collection_name(self, user_id: int) -> str:
        """Get collection name for a specific user."""
        return f"user_{user_id}_documents"
    
    def get_user_collection(self, user_id: int):
        """
        Get or create a collection specific to a user for data isolation.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            ChromaDB collection for the user
        """
        collection_name = self._get_user_collection_name(user_id)
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": f"Documents for user {user_id}"}
        )
    
    def add_documents(self, documents: List[Dict[str, Any]], user_id: Optional[int] = None) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of document dictionaries with 'text', 'id', and 'metadata'
            user_id: Optional user ID for user-specific storage
        """
        try:
            if not documents:
                raise ValueError("No documents provided")
            
            # Get appropriate collection
            if user_id is not None:
                collection = self.get_user_collection(user_id)
            else:
                collection = self.collection
            
            # Extract components for ChromaDB
            texts = [doc["text"] for doc in documents]
            ids = [doc["id"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]
            
            # Add user_id to metadata if provided
            if user_id is not None:
                for meta in metadatas:
                    meta["user_id"] = user_id
            
            # Add to ChromaDB collection
            collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            self.logger.info(f"Added {len(documents)} documents to vector store" + 
                           (f" for user {user_id}" if user_id else ""))
            
        except Exception as e:
            self.logger.error(f"Error adding documents to vector store: {str(e)}")
            raise
    
    def query(self, query_text: str, n_results: int = 5, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Query the vector store for similar documents.
        
        Args:
            query_text: Query text to search for
            n_results: Number of top results to return
            user_id: Optional user ID for user-specific querying
            
        Returns:
            Dictionary containing retrieved documents and metadata
        """
        try:
            if not query_text or not query_text.strip():
                raise ValueError("Empty query provided")
            
            # Get appropriate collection
            if user_id is not None:
                collection = self.get_user_collection(user_id)
            else:
                collection = self.collection
            
            # Query ChromaDB
            results = collection.query(
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
    
    def get_collection_count(self, user_id: Optional[int] = None) -> int:
        """Get the total number of documents in the collection."""
        try:
            if user_id is not None:
                collection = self.get_user_collection(user_id)
            else:
                collection = self.collection
            return collection.count()
        except Exception as e:
            self.logger.error(f"Error getting collection count: {str(e)}")
            return 0
    
    def clear_collection(self, user_id: Optional[int] = None) -> None:
        """Clear all documents from the collection."""
        try:
            if user_id is not None:
                collection_name = self._get_user_collection_name(user_id)
                try:
                    self.client.delete_collection(name=collection_name)
                except Exception:
                    pass  # Collection might not exist
                self.logger.info(f"Cleared documents for user {user_id}")
            else:
                # Delete the default collection and recreate it
                self.client.delete_collection(name="documents")
                self.collection = self.client.get_or_create_collection(
                    name="documents",
                    metadata={"description": "RAG chatbot document collection"}
                )
                self.logger.info("Cleared all documents from default vector store")
        except Exception as e:
            self.logger.error(f"Error clearing collection: {str(e)}")
            raise
    
    def delete_user_documents(self, user_id: int, document_ids: List[str] = None) -> None:
        """
        Delete documents for a specific user.
        
        Args:
            user_id: User's unique identifier
            document_ids: Optional list of specific document IDs to delete
        """
        try:
            collection = self.get_user_collection(user_id)
            
            if document_ids:
                collection.delete(ids=document_ids)
                self.logger.info(f"Deleted {len(document_ids)} documents for user {user_id}")
            else:
                # Delete all documents in user's collection
                self.clear_collection(user_id)
                
        except Exception as e:
            self.logger.error(f"Error deleting user documents: {str(e)}")
            raise
