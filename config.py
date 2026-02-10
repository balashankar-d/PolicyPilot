"""Configuration settings for the RAG chatbot backend."""

from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings using Pydantic Settings for environment config."""
    
    # Groq LLM settings
    groq_api_key: str
    model_name: str = "llama3-8b-8192"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_results: int = 5
    persist_directory: str = "db/"
    
    # Authentication settings
    secret_key: str = "your-secret-key-change-in-production-32chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    
    # Database settings
    database_url: str = "sqlite:///./policypilot.db"
    
    # Conversation memory settings
    max_history_items: int = 5
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
