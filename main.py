"""
Advanced Conversational RAG Chatbot API with Personalized Memory.

This module provides the FastAPI application with:
- User authentication (signup, login, JWT)
- User-specific document storage and retrieval
- Persistent conversational memory with summarization
- Personalized user profiles and key-value memory
- Intent & entity extraction from queries
- Chunk re-ranking for improved relevance
- Response validation / hallucination guard
- Multi-step RAG chain orchestration
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import tempfile
import os
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import timedelta

from config import get_settings
from database import get_db, User, Document, ChatHistory, create_tables
from auth import (
    UserCreate, UserLogin, UserResponse, Token,
    create_user, authenticate_user, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from ingestion import PDFProcessor
from chunking import TextChunker
from embeddings import EmbeddingModel
from vector_store import VectorStore
from retrieval import Retriever
from llm_client import GroqLLMClient
from conversation_memory import ConversationMemory
from intent_extractor import IntentExtractor
from user_memory import UserMemoryManager
from reranker import ChunkReranker
from response_validator import ResponseValidator
from rag_chain import RAGChain

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
create_tables()

app = FastAPI(
    title="PolicyPilot RAG Chatbot API",
    description="Advanced conversational RAG chatbot with personalization, memory, and hallucination control",
    version="3.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Initialize components
settings = get_settings()
pdf_processor = PDFProcessor()
text_chunker = TextChunker(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap
)
embedding_model = EmbeddingModel(settings.embedding_model)
vector_store = VectorStore(settings.persist_directory)
retriever = Retriever(vector_store, embedding_model, settings.top_k_results)
llm_client = GroqLLMClient(settings.groq_api_key, settings.model_name)
conversation_memory = ConversationMemory(max_history_items=settings.max_history_items)

# Advanced pipeline components
from groq import Groq as _Groq
_groq_raw = _Groq(api_key=settings.groq_api_key)
intent_extractor = IntentExtractor(client=_groq_raw, model_name=settings.model_name)
user_memory_manager = UserMemoryManager()
reranker = ChunkReranker(top_n=3, use_cross_encoder=False)  # keyword-based by default
response_validator = ResponseValidator(min_grounding_ratio=0.10)

# RAG Chain orchestrator
rag_chain = RAGChain(
    retriever=retriever,
    llm_client=llm_client,
    conversation_memory=conversation_memory,
    intent_extractor=intent_extractor,
    user_memory_manager=user_memory_manager,
    reranker=reranker,
    response_validator=response_validator,
)

logger.info("PolicyPilot RAG Chatbot API initialized successfully (advanced pipeline)")


# ============== Pydantic Schemas ==============

class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str
    sources: list
    success: bool
    message: str


class UploadResponse(BaseModel):
    message: str
    chunks_created: int
    success: bool
    document_id: Optional[int] = None


class DocumentResponse(BaseModel):
    id: int
    filename: str
    chunks_count: int
    upload_status: str
    created_at: str

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    id: int
    question: str
    answer: str
    created_at: str

    class Config:
        from_attributes = True


class UserStatsResponse(BaseModel):
    total_documents: int
    total_conversations: int
    successful_conversations: int


class AdvancedQueryResponse(BaseModel):
    """Extended response with validation and personalization metadata."""
    answer: str
    sources: list
    success: bool
    message: str
    intent: str = "question"
    confidence: str = "unknown"
    is_grounded: bool = False
    flags: list = []


class ProfileUpdateRequest(BaseModel):
    """Request body for updating user profile."""
    name: Optional[str] = None
    state: Optional[str] = None
    occupation: Optional[str] = None
    income: Optional[str] = None
    age: Optional[int] = None
    category: Optional[str] = None
    preferences: Optional[str] = None


class ProfileResponse(BaseModel):
    """User profile response."""
    name: Optional[str] = None
    state: Optional[str] = None
    occupation: Optional[str] = None
    income: Optional[str] = None
    age: Optional[int] = None
    category: Optional[str] = None
    preferences: Optional[str] = None

    class Config:
        from_attributes = True


class MemoryEntry(BaseModel):
    key: str
    value: str


class MemoryResponse(BaseModel):
    memories: Dict[str, str]


# ============== Public Endpoints ==============

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "PolicyPilot RAG Chatbot API",
        "version": "3.0.0",
        "endpoints": {
            "auth": {
                "signup": "POST /auth/signup",
                "login": "POST /auth/login",
                "me": "GET /auth/me"
            },
            "documents": {
                "upload": "POST /documents/upload",
                "list": "GET /documents",
                "delete": "DELETE /documents/{document_id}"
            },
            "chat": {
                "query": "POST /chat/query",
                "advanced_query": "POST /chat/advanced-query",
                "history": "GET /chat/history",
                "clear": "DELETE /chat/history"
            },
            "profile": {
                "get": "GET /profile",
                "update": "PUT /profile"
            },
            "memory": {
                "list": "GET /memory",
                "store": "POST /memory",
                "delete": "DELETE /memory/{key}",
                "clear": "DELETE /memory"
            },
            "status": "GET /status"
        }
    }


@app.get("/status")
async def get_status():
    """Get system status (public endpoint)."""
    try:
        # Get global document count
        doc_count = vector_store.get_collection_count()
        return {
            "status": "healthy",
            "documents_in_store": doc_count,
            "model": settings.model_name,
            "embedding_model": settings.embedding_model,
            "version": "3.0.0"
        }
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="System health check failed")


# ============== Authentication Endpoints ==============

@app.post("/auth/signup", response_model=Token)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        # Create user
        user = create_user(db, user_data)
        
        # Generate access token (sub must be a string for JWT compliance)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        logger.info(f"User registered: {user.email}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")


@app.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    try:
        user = authenticate_user(db, user_data.email, user_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Generate access token (sub must be a string for JWT compliance)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        logger.info(f"User logged in: {user.email}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")


@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's information."""
    return UserResponse.model_validate(current_user)


# ============== Document Endpoints (Protected) ==============

@app.post("/documents/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process a PDF file for the authenticated user.
    Documents are stored in user-specific vector store collection.
    """
    try:
        logger.info(f"User {current_user.email} uploading file: {file.filename}")
        
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        logger.info(f"Read {file_size} bytes from {file.filename}")
        
        # Create document record
        db_document = Document(
            user_id=current_user.id,
            filename=file.filename,
            original_name=file.filename,
            file_size=file_size,
            upload_status="processing"
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Process PDF
            text = pdf_processor.process_pdf(tmp_file_path)
            logger.info(f"Extracted {len(text)} characters from PDF")
            
            # Create chunks
            documents = text_chunker.split_text(text, source=file.filename)
            logger.info(f"Created {len(documents)} chunks")
            
            if not documents:
                db_document.upload_status = "failed"
                db.commit()
                raise ValueError("No chunks created from PDF")
            
            # Store in user-specific vector database collection
            vector_store.add_documents(documents, user_id=current_user.id)
            logger.info(f"Stored {len(documents)} chunks for user {current_user.id}")
            
            # Update document record
            db_document.chunks_count = len(documents)
            db_document.upload_status = "completed"
            db.commit()
            
            logger.info(f"Successfully processed {file.filename} for user {current_user.email}")
            
            return UploadResponse(
                message=f"Successfully processed {file.filename}",
                chunks_created=len(documents),
                success=True,
                document_id=db_document.id
            )
            
        finally:
            # Clean up temporary file
            try:
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temporary file: {cleanup_error}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@app.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of documents uploaded by the current user."""
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            chunks_count=doc.chunks_count,
            upload_status=doc.upload_status,
            created_at=doc.created_at.isoformat()
        )
        for doc in documents
    ]


@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document uploaded by the current user."""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from database
    db.delete(document)
    db.commit()
    
    logger.info(f"Deleted document {document_id} for user {current_user.email}")
    
    return {"message": "Document deleted successfully"}


# ============== Chat Endpoints (Protected) ==============

@app.post("/chat/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query the user's document store and generate an answer.
    Uses the basic RAG pipeline for backward-compatible response format.
    Internally delegates to the advanced RAG chain.
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        query = request.query.strip()
        logger.info(f"User {current_user.email} query: {query[:100]}...")
        
        # Check if user has any documents
        doc_count = vector_store.get_collection_count(user_id=current_user.id)
        if doc_count == 0:
            return QueryResponse(
                answer="Please upload a PDF document first before asking questions.",
                sources=[],
                success=True,
                message="No documents available"
            )
        
        # Run the full advanced RAG chain
        result = rag_chain.run(query, current_user.id, db)
        
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            success=result["success"],
            message=result["message"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        fallback_response = "Sorry, this document doesn't contain enough information to answer that."
        return QueryResponse(
            answer=fallback_response,
            sources=[],
            success=False,
            message=f"Error occurred: {str(e)}"
        )


@app.post("/chat/advanced-query", response_model=AdvancedQueryResponse)
async def advanced_query_documents(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Advanced query endpoint with full pipeline metadata.
    Returns intent, confidence, grounding status, and flags.
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        query = request.query.strip()
        logger.info(f"Advanced query from {current_user.email}: {query[:100]}...")
        
        doc_count = vector_store.get_collection_count(user_id=current_user.id)
        if doc_count == 0:
            return AdvancedQueryResponse(
                answer="Please upload a PDF document first before asking questions.",
                sources=[],
                success=True,
                message="No documents available",
                intent="question",
                confidence="high",
                is_grounded=True,
                flags=["no_documents"],
            )
        
        result = rag_chain.run(query, current_user.id, db)
        
        return AdvancedQueryResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Advanced query error: {str(e)}")
        return AdvancedQueryResponse(
            answer="Sorry, this document doesn't contain enough information to answer that.",
            sources=[],
            success=False,
            message=f"Error occurred: {str(e)}",
            intent="question",
            confidence="none",
            is_grounded=False,
            flags=["error"],
        )


@app.get("/chat/history", response_model=List[ChatHistoryResponse])
async def get_chat_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation history for the current user."""
    history = (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == current_user.id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    
    return [
        ChatHistoryResponse(
            id=item.id,
            question=item.question,
            answer=item.answer,
            created_at=item.created_at.isoformat()
        )
        for item in reversed(history)  # Return in chronological order
    ]


@app.delete("/chat/history")
async def clear_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear conversation history for the current user."""
    deleted = conversation_memory.clear_user_history(db, current_user.id)
    logger.info(f"Cleared {deleted} chat history items for user {current_user.email}")
    return {"message": f"Cleared {deleted} conversation items"}


@app.get("/user/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistics for the current user."""
    # Count documents
    total_documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .count()
    )
    
    # Get conversation stats
    chat_stats = conversation_memory.get_user_stats(db, current_user.id)
    
    return UserStatsResponse(
        total_documents=total_documents,
        total_conversations=chat_stats["total_conversations"],
        successful_conversations=chat_stats["successful_conversations"]
    )


# ============== Profile & Memory Endpoints (Protected) ==============

@app.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's profile."""
    profile = user_memory_manager.get_profile(db, current_user.id)
    if not profile:
        return ProfileResponse()
    return ProfileResponse(
        name=profile.name,
        state=profile.state,
        occupation=profile.occupation,
        income=profile.income,
        age=profile.age,
        category=profile.category,
        preferences=profile.preferences,
    )


@app.put("/profile", response_model=ProfileResponse)
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update the current user's profile."""
    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No profile fields provided")
    
    profile = user_memory_manager.update_profile(db, current_user.id, update_data)
    logger.info(f"Profile updated for user {current_user.email}")
    return ProfileResponse(
        name=profile.name,
        state=profile.state,
        occupation=profile.occupation,
        income=profile.income,
        age=profile.age,
        category=profile.category,
        preferences=profile.preferences,
    )


@app.get("/memory", response_model=MemoryResponse)
async def get_memories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all stored memories for the current user."""
    memories = user_memory_manager.get_memories(db, current_user.id)
    return MemoryResponse(memories=memories)


@app.post("/memory")
async def store_memory(
    entry: MemoryEntry,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Store a key-value memory for the current user."""
    user_memory_manager.store_memory(
        db, current_user.id, entry.key, entry.value, source="manual"
    )
    return {"message": f"Memory '{entry.key}' stored successfully"}


@app.delete("/memory/{key}")
async def delete_memory(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific memory entry."""
    deleted = user_memory_manager.delete_memory(db, current_user.id, key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Memory '{key}' not found")
    return {"message": f"Memory '{key}' deleted successfully"}


@app.delete("/memory")
async def clear_all_memories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear all memories for the current user."""
    count = user_memory_manager.clear_memories(db, current_user.id)
    return {"message": f"Cleared {count} memory entries"}


# ============== Legacy Endpoints (For Backward Compatibility) ==============

@app.post("/upload_pdf", response_model=UploadResponse)
async def upload_pdf_legacy(file: UploadFile = File(...)):
    """
    Legacy endpoint for PDF upload (without authentication).
    Kept for backward compatibility.
    """
    try:
        logger.info(f"Legacy upload: {file.filename}")
        
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        content = await file.read()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            text = pdf_processor.process_pdf(tmp_file_path)
            documents = text_chunker.split_text(text, source=file.filename)
            
            if not documents:
                raise ValueError("No chunks created from PDF")
            
            # Store in default collection (no user isolation)
            vector_store.add_documents(documents)
            
            return UploadResponse(
                message=f"Successfully processed {file.filename}",
                chunks_created=len(documents),
                success=True
            )
            
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Legacy upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def query_documents_legacy(request: QueryRequest):
    """
    Legacy endpoint for querying documents (without authentication).
    Kept for backward compatibility.
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        query = request.query.strip()
        
        doc_count = vector_store.get_collection_count()
        if doc_count == 0:
            return QueryResponse(
                answer="Please upload a PDF document first before asking questions.",
                sources=[],
                success=True,
                message="No documents available"
            )
        
        retrieval_result = retriever.retrieve_relevant_chunks(query)
        
        if not retrieval_result["is_relevant"] or not retrieval_result["chunks"]:
            return QueryResponse(
                answer="Sorry, this document doesn't contain enough information to answer that.",
                sources=[],
                success=True,
                message="No relevant information found"
            )
        
        context = retriever.format_context(retrieval_result["chunks"])
        llm_result = llm_client.generate_answer(query, context)
        
        return QueryResponse(
            answer=llm_result["answer"],
            sources=retrieval_result["sources"],
            success=llm_result["success"],
            message=llm_result["message"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Legacy query error: {str(e)}")
        return QueryResponse(
            answer="Sorry, this document doesn't contain enough information to answer that.",
            sources=[],
            success=False,
            message=f"Error occurred: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
