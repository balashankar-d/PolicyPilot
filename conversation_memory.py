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
    
    def __init__(self, max_history_items: int = 5, summary_threshold: int = 8):
        """
        Initialize conversation memory.
        
        Args:
            max_history_items: Maximum number of recent Q&A pairs to include verbatim in context
            summary_threshold: When total fetched history exceeds this, older items are summarized
        """
        self.max_history_items = max_history_items
        self.summary_threshold = summary_threshold
        # We fetch MORE items from DB than we display verbatim so that
        # the summary branch can actually trigger, and so we can surface
        # the full window for follow-up resolution.
        self.fetch_limit = max(max_history_items * 3, summary_threshold + 4)
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
        
        Fetches a generous window (self.fetch_limit) so the summary /
        follow-up-resolution logic has enough material to work with.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Override for the number of items to retrieve
            
        Returns:
            List of conversation dictionaries in chronological order
        """
        try:
            if limit is None:
                limit = self.fetch_limit
            
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
    
    def get_last_exchange(self, db: Session, user_id: int) -> Optional[Dict]:
        """
        Return the single most-recent successful Q&A pair.
        
        This is used by the intent extractor and the retrieval step
        to resolve follow-up references ("tell me more", "what about
        eligibility for that?").
        """
        try:
            item = (
                db.query(ChatHistory)
                .filter(ChatHistory.user_id == user_id)
                .filter(ChatHistory.was_successful == True)
                .order_by(ChatHistory.created_at.desc())
                .first()
            )
            if not item:
                return None
            return {
                "question": item.question,
                "answer": item.answer,
                "timestamp": item.created_at.isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Error fetching last exchange: {e}")
            return None
    
    def format_history_context(self, history: List[Dict]) -> str:
        """
        Format conversation history as a context string for the LLM.
        
        Strategy:
          - If total items ≤ summary_threshold: include all verbatim.
          - If total items > summary_threshold: summarize the older items and
            keep the most recent max_history_items verbatim so the LLM can
            resolve follow-up references.
        
        Args:
            history: List of conversation dicts (chronological)
            
        Returns:
            Formatted string of previous conversations
        """
        if not history:
            return ""
        
        if len(history) > self.summary_threshold:
            older = history[:-self.max_history_items]
            recent = history[-self.max_history_items:]
            
            summary = self._summarize_history(older)
            formatted = f"Summary of earlier conversation:\n{summary}\n\n"
            formatted += "Recent conversation (use this to resolve follow-up references):\n"
            for i, item in enumerate(recent, 1):
                formatted += f"User: {item['question']}\n"
                formatted += f"Assistant: {item['answer']}\n\n"
            return formatted.strip()
        
        formatted = "Conversation history (use this to resolve follow-up references):\n"
        for i, item in enumerate(history, 1):
            formatted += f"User: {item['question']}\n"
            formatted += f"Assistant: {item['answer']}\n\n"
        
        return formatted.strip()
    
    def _summarize_history(self, history: List[Dict]) -> str:
        """
        Create a compact summary of older conversation history.
        Uses extractive summarization (key topics) to stay lightweight.
        
        Args:
            history: Older conversation items to summarize
            
        Returns:
            Compact summary string
        """
        if not history:
            return "No earlier conversation."
        
        topics = []
        for item in history:
            # Extract the core question topic (first 80 chars)
            q = item["question"].strip()
            if len(q) > 80:
                q = q[:77] + "..."
            topics.append(f"- Asked about: {q}")
        
        return "The user previously discussed:\n" + "\n".join(topics)
    
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
