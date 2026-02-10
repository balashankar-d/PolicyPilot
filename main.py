
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tempfile
import os
import logging
from pathlib import Path
from typing import Dict, Any

from config import get_settings
from ingestion import PDFProcessor
from chunking import TextChunker
from embeddings import EmbeddingModel
from vector_store import VectorStore
from retrieval import Retriever
from llm_client import GroqLLMClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Chatbot API",
    description="Retrieval-Augmented Generation chatbot for PDF documents",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

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

logger.info("RAG Chatbot API initialized successfully")


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


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RAG Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload_pdf",
            "query": "/query",
            "status": "/status"
        }
    }


@app.get("/status")
async def get_status():
    """Get system status."""
    try:
        doc_count = vector_store.get_collection_count()
        return {
            "status": "healthy",
            "documents_in_store": doc_count,
            "model": settings.model_name,
            "embedding_model": settings.embedding_model
        }
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="System health check failed")


@app.post("/upload_pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload and process a PDF file.
    Extracts text, chunks it, and stores embeddings in ChromaDB.
    """
    try:
        logger.info(f"Received file upload request: {file.filename}")
        
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            logger.error(f"Invalid file type: {file.filename}")
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        logger.info(f"Processing upload: {file.filename}")
        
        # Read file content
        content = await file.read()
        logger.info(f"Read {len(content)} bytes from {file.filename}")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            logger.info(f"Processing PDF at {tmp_file_path}")
            
            # Process PDF
            text = pdf_processor.process_pdf(tmp_file_path)
            logger.info(f"Extracted {len(text)} characters from PDF")
            
            # Create chunks
            documents = text_chunker.split_text(text, source=file.filename)
            logger.info(f"Created {len(documents)} chunks")
            
            if not documents:
                raise ValueError("No chunks created from PDF")
            
            # Store in vector database
            vector_store.add_documents(documents)
            logger.info(f"Successfully stored {len(documents)} chunks in vector database")
            
            logger.info(f"Successfully processed {file.filename}: {len(documents)} chunks created")
            
            return UploadResponse(
                message=f"Successfully processed {file.filename}",
                chunks_created=len(documents),
                success=True
            )
            
        finally:
            # Clean up temporary file
            try:
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                    logger.info(f"Cleaned up temporary file: {tmp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temporary file: {cleanup_error}")
                
    except HTTPException:
        logger.error(f"HTTP exception during upload processing")
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing PDF upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Query the document store and generate an answer.
    Implements the RAG pipeline with hallucination control.
    """
    try:
        # Validate input
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        query = request.query.strip()
        logger.info(f"Processing query: {query[:100]}...")
        
        # Check if we have any documents
        doc_count = vector_store.get_collection_count()
        if doc_count == 0:
            return QueryResponse(
                answer="Please upload a PDF document first before asking questions.",
                sources=[],
                success=True,
                message="No documents available"
            )
        
        # Retrieve relevant chunks
        retrieval_result = retriever.retrieve_relevant_chunks(query)
        logger.info(f"Retrieval result: relevant={retrieval_result['is_relevant']}, chunks={len(retrieval_result['chunks'])}")
        
        # Check if we found relevant content
        if not retrieval_result["is_relevant"] or not retrieval_result["chunks"]:
            fallback_response = "Sorry, this document doesn't contain enough information to answer that."
            logger.warning(f"No relevant chunks found for query: {query[:50]}...")
            
            return QueryResponse(
                answer=fallback_response,
                sources=[],
                success=True,
                message="No relevant information found"
            )
        
        # Format context for LLM
        context = retriever.format_context(retrieval_result["chunks"])
        logger.info(f"Context length: {len(context)} characters")
        
        # Generate answer using LLM
        llm_result = llm_client.generate_answer(query, context)
        logger.info(f"LLM result: success={llm_result['success']}, used_context={llm_result['used_context']}")
        
        return QueryResponse(
            answer=llm_result["answer"],
            sources=retrieval_result["sources"],
            success=llm_result["success"],
            message=llm_result["message"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        
        # Return fallback response on any error
        fallback_response = "Sorry, this document doesn't contain enough information to answer that."
        return QueryResponse(
            answer=fallback_response,
            sources=[],
            success=False,
            message=f"Error occurred: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
