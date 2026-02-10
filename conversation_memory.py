"""Conversation memory module for storing and retrieving chat history."""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json
import logging

from database import ChatHistory, User

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Manages conversation history for RAG context enhancement."""
    
    def __init__(self, max_history_items: int = 5):
        """
        Initialize conversation memory.
        
        Args:
            max_history_items: Maximum number of previous Q&A pairs to include in context
        """
        self.max_history_items = max_history_items
        self.logger = logger
    
    def save_conversation(
        self,
        db: Session,
        user_id: int,
        question: str,
        answer: str,
        sources: List[str] = None,
        was_successful: bool = True
    ) -> ChatHistory:
        """
        Save a conversation exchange to the database.
        
        Args:
            db: Database session
            user_id: User ID
            question: User's question
            answer: System's answer
            sources: List of source documents used
            was_successful: Whether the answer was successful
            
        Returns:
            Created ChatHistory record
        """
        try:
            sources_json = json.dumps(sources) if sources else None
            
            chat_record = ChatHistory(
                user_id=user_id,
                question=question,
                answer=answer,
                sources=sources_json,
                was_successful=was_successful
            )
            
            db.add(chat_record)
            db.commit()
            db.refresh(chat_record)
            
            self.logger.info(f"Saved conversation for user {user_id}")
            return chat_record
            
        except Exception as e:
            self.logger.error(f"Error saving conversation: {str(e)}")
            db.rollback()
            raise
    
    def get_recent_history(
        self,
        db: Session,
        user_id: int,
        limit: int = None
    ) -> List[Dict]:
        """
        Get recent conversation history for a user.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of items to retrieve (defaults to max_history_items)
            
        Returns:
            List of conversation dictionaries with question and answer
        """
        try:
            if limit is None:
                limit = self.max_history_items
            
            history = (
                db.query(ChatHistory)
                .filter(ChatHistory.user_id == user_id)
                .filter(ChatHistory.was_successful == True)
                .order_by(ChatHistory.created_at.desc())
                .limit(limit)
                .all()
            )
            
            # Reverse to get chronological order
            history = list(reversed(history))
            
            result = []
            for item in history:
                result.append({
                    "question": item.question,
                    "answer": item.answer,
                    "timestamp": item.created_at.isoformat()
                })
            
            self.logger.info(f"Retrieved {len(result)} history items for user {user_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error retrieving history: {str(e)}")
            return []
    
    def format_history_context(self, history: List[Dict]) -> str:
        """
        Format conversation history as context string for the LLM.
        
        Args:
            history: List of conversation dictionaries
            
        Returns:
            Formatted string of previous conversations
        """
        if not history:
            return ""
        
        formatted = "Previous conversation:\n"
        for i, item in enumerate(history, 1):
            formatted += f"Q{i}: {item['question']}\n"
            formatted += f"A{i}: {item['answer']}\n\n"
        
        return formatted.strip()
    
    def clear_user_history(self, db: Session, user_id: int) -> int:
        """
        Clear all conversation history for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Number of deleted records
        """
        try:
            deleted = (
                db.query(ChatHistory)
                .filter(ChatHistory.user_id == user_id)
                .delete()
            )
            db.commit()
            
            self.logger.info(f"Cleared {deleted} history items for user {user_id}")
            return deleted
            
        except Exception as e:
            self.logger.error(f"Error clearing history: {str(e)}")
            db.rollback()
            raise
    
    def get_user_stats(self, db: Session, user_id: int) -> Dict:
        """
        Get conversation statistics for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dictionary with conversation statistics
        """
        try:
            total_conversations = (
                db.query(ChatHistory)
                .filter(ChatHistory.user_id == user_id)
                .count()
            )
            
            successful_conversations = (
                db.query(ChatHistory)
                .filter(ChatHistory.user_id == user_id)
                .filter(ChatHistory.was_successful == True)
                .count()
            )
            
            return {
                "total_conversations": total_conversations,
                "successful_conversations": successful_conversations,
                "success_rate": (
                    successful_conversations / total_conversations * 100 
                    if total_conversations > 0 else 0
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error getting stats: {str(e)}")
            return {
                "total_conversations": 0,
                "successful_conversations": 0,
                "success_rate": 0
            }
