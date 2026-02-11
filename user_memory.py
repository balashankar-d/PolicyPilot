"""
User Memory Module.

Manages persistent per-user memory for personalized responses.
Stores structured user attributes and conversation-extracted information
in the database for cross-session persistence.
"""

import json
import logging
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from database import UserProfile, UserMemory

logger = logging.getLogger(__name__)


class UserMemoryManager:
    """Manages user profile and key-value memory for personalization."""
    
    def __init__(self):
        self.logger = logger
    
    # ==================== Profile Management ====================
    
    def get_profile(self, db: Session, user_id: int) -> Optional[UserProfile]:
        """Get user profile."""
        return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    def update_profile(self, db: Session, user_id: int, data: Dict) -> UserProfile:
        """Create or update user profile fields."""
        profile = self.get_profile(db, user_id)
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.add(profile)
        
        allowed_fields = {"name", "state", "occupation", "income", "age", "category", "preferences"}
        for key, value in data.items():
            if key in allowed_fields and value is not None:
                if key == "age":
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        continue
                setattr(profile, key, value)
        
        db.commit()
        db.refresh(profile)
        self.logger.info(f"Updated profile for user {user_id}")
        return profile
    
    def profile_to_dict(self, profile: Optional[UserProfile]) -> Dict:
        """Convert profile to dictionary for prompt injection."""
        if not profile:
            return {}
        return {
            "name": profile.name,
            "state": profile.state,
            "occupation": profile.occupation,
            "income": profile.income,
            "age": profile.age,
            "category": profile.category,
        }
    
    # ==================== Key-Value Memory ====================
    
    def store_memory(self, db: Session, user_id: int, key: str, value: str,
                     source: str = "conversation", confidence: float = 1.0) -> UserMemory:
        """Store or update a memory key-value pair."""
        existing = (
            db.query(UserMemory)
            .filter(UserMemory.user_id == user_id, UserMemory.memory_key == key)
            .first()
        )
        
        if existing:
            existing.memory_value = value
            existing.source = source
            existing.confidence = confidence
            db.commit()
            db.refresh(existing)
            return existing
        
        memory = UserMemory(
            user_id=user_id,
            memory_key=key,
            memory_value=value,
            source=source,
            confidence=confidence
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        self.logger.info(f"Stored memory '{key}' for user {user_id}")
        return memory
    
    def get_memories(self, db: Session, user_id: int) -> Dict[str, str]:
        """Get all memory key-value pairs for a user."""
        memories = (
            db.query(UserMemory)
            .filter(UserMemory.user_id == user_id)
            .order_by(UserMemory.updated_at.desc())
            .all()
        )
        return {m.memory_key: m.memory_value for m in memories}
    
    def delete_memory(self, db: Session, user_id: int, key: str) -> bool:
        """Delete a specific memory entry."""
        deleted = (
            db.query(UserMemory)
            .filter(UserMemory.user_id == user_id, UserMemory.memory_key == key)
            .delete()
        )
        db.commit()
        return deleted > 0
    
    def clear_memories(self, db: Session, user_id: int) -> int:
        """Clear all memories for a user."""
        deleted = (
            db.query(UserMemory)
            .filter(UserMemory.user_id == user_id)
            .delete()
        )
        db.commit()
        return deleted
    
    # ==================== Auto-extraction from Conversations ====================
    
    def update_from_extracted_info(self, db: Session, user_id: int, 
                                   personal_info: Dict[str, str]) -> None:
        """
        Update user profile and memories from extracted personal information.
        Called after intent extraction detects personal info in user messages.
        
        Args:
            db: Database session
            user_id: User ID
            personal_info: Dictionary of extracted personal info
        """
        if not personal_info:
            return
        
        # Profile fields go directly to the profile table
        profile_fields = {"name", "state", "occupation", "income", "age", "category"}
        profile_data = {k: v for k, v in personal_info.items() if k in profile_fields}
        
        if profile_data:
            self.update_profile(db, user_id, profile_data)
        
        # All fields also go to key-value memory for flexible access
        for key, value in personal_info.items():
            if value and str(value).strip():
                self.store_memory(
                    db, user_id, key, str(value),
                    source="conversation", confidence=0.8
                )
    
    # ==================== Context Formatting ====================
    
    def format_user_context(self, db: Session, user_id: int) -> str:
        """
        Format user profile and memories into a context string for LLM prompts.
        
        Produces an actionable block that tells the LLM exactly how to use
        the user's personal information when generating answers.
        
        Returns:
            Formatted string with user context, or empty string if no data.
        """
        profile = self.get_profile(db, user_id)
        memories = self.get_memories(db, user_id)
        
        # Collect all known data points
        data_lines = []
        
        # Profile data
        if profile:
            profile_dict = self.profile_to_dict(profile)
            for k, v in profile_dict.items():
                if v is not None and str(v).strip():
                    data_lines.append(f"  {k}: {v}")
        
        # Additional memories (exclude profile fields already shown)
        profile_keys = {"name", "state", "occupation", "income", "age", "category"}
        extra_memories = {k: v for k, v in memories.items() if k not in profile_keys}
        if extra_memories:
            for k, v in extra_memories.items():
                data_lines.append(f"  {k}: {v}")
        
        if not data_lines:
            return ""
        
        # Build an actionable instruction block
        header = (
            "USER PROFILE (personalize your answer using this data):\n"
            "Use the details below to tailor your response. For example, if the\n"
            "user's income or category is known, explain eligibility specifically\n"
            "for their situation. If their state is known, mention state-specific\n"
            "provisions. Address the user by name if available.\n"
        )
        
        return header + "\n".join(data_lines)
