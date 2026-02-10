# RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot that allows users to upload PDF documents and ask questions about their content. The system uses ChromaDB for vector storage, Sentence Transformers for embeddings, and Groq's Mixtral model for answer generation.

## Architecture

### Backend
- **FastAPI** - REST API server
- **PyMuPDF/pdfplumber** - PDF text extraction
- **LangChain** - Text chunking
- **Sentence Transformers** - Text embeddings (all-MiniLM-L6-v2)
- **ChromaDB** - Vector database with DuckDB+Parquet backend
- **Groq API** - LLM inference (Mixtral-8x7b-32768)

### Frontend
- **React** - User interface
- **React Dropzone** - File upload
- **Axios** - API communication

## Features

✅ **PDF Upload & Processing**
- Drag-and-drop PDF upload
- Text extraction and cleaning
- Semantic chunking (500 chars with 50 char overlap)

✅ **Vector Storage**
- Persistent ChromaDB storage
- Automatic embedding generation
- Efficient similarity search

✅ **RAG Pipeline**
- Context retrieval from uploaded documents
- Grounded answer generation
- Hallucination prevention with strict prompting

✅ **Chat Interface**
- Real-time conversation
- Source citations
- Error handling

## Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js 18+
- Groq API key

### 1. Clone and Setup Backend

```bash
# Navigate to project directory
cd policypilot

# Install Python dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Setup Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install
```

### 3. Run the Application

#### Option A: Development Mode

**Terminal 1 - Backend:**
```bash
# From project root
python main.py
# API will be available at http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
# From frontend directory
npm start
# UI will be available at http://localhost:3000
```

#### Option B: Docker Compose

```bash
# From project root
docker-compose up --build
# Full application available at http://localhost:3000
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key (required) | - |
| `MODEL_NAME` | Groq model name | `mixtral-8x7b-32768` |
| `EMBEDDING_MODEL` | Sentence transformer model | `all-MiniLM-L6-v2` |
| `CHUNK_SIZE` | Text chunk size | `500` |
| `CHUNK_OVERLAP` | Chunk overlap | `50` |
| `TOP_K_RESULTS` | Number of retrieved chunks | `5` |
| `PERSIST_DIRECTORY` | ChromaDB storage path | `db/` |

## API Endpoints

### POST /upload_pdf
Upload and process a PDF file.

**Request:** Multipart form with PDF file
**Response:**
```json
{
  "message": "Successfully processed document.pdf",
  "chunks_created": 42,
  "success": true
}
```

### POST /query
Ask a question about uploaded documents.

**Request:**
```json
{
  "query": "What is the main topic of the document?"
}
```

**Response:**
```json
{
  "answer": "The document discusses...",
  "sources": ["document.pdf"],
  "success": true,
  "message": "Answer generated successfully"
}
```

### GET /status
Get system status and document count.

**Response:**
```json
{
  "status": "healthy",
  "documents_in_store": 5,
  "model": "mixtral-8x7b-32768",
  "embedding_model": "all-MiniLM-L6-v2"
}
```

## Hallucination Prevention

The system implements multiple layers of hallucination control:

1. **Strict Prompting**: LLM instructed to only use provided context
2. **Fallback Responses**: Returns "Sorry, this document doesn't contain enough information to answer that." when no relevant content is found
3. **Context Validation**: Checks relevance before calling LLM
4. **Source Citations**: Shows which documents were used for answers

## Project Structure

```
policypilot/
├── main.py              # FastAPI application
├── config.py            # Configuration settings
├── ingestion.py         # PDF processing
├── chunking.py          # Text chunking
├── embeddings.py        # Embedding model
├── vector_store.py      # ChromaDB interface
├── retrieval.py         # RAG retrieval logic
├── llm_client.py        # Groq API client
├── requirements.txt     # Python dependencies
├── Dockerfile           # Backend container
├── docker-compose.yml   # Full stack deployment
├── .env                 # Environment variables
├── db/                  # ChromaDB persistence
└── frontend/
    ├── src/
    │   ├── App.js
    │   ├── components/
    │   │   ├── Upload.js
    │   │   ├── Chat.js
    │   │   └── Message.js
    │   └── *.css
    ├── package.json
    └── Dockerfile
```

## Dependencies

### Backend
- `fastapi==0.104.1` - Web framework
- `uvicorn==0.24.0` - ASGI server
- `pymupdf==1.23.14` - PDF processing
- `langchain-text-splitters==0.0.1` - Text chunking
- `sentence-transformers==2.2.2` - Embeddings
- `chromadb==0.4.18` - Vector database
- `groq==0.4.1` - LLM API client

### Frontend
- `react==18.2.0` - UI framework
- `react-dropzone==14.2.3` - File upload
- `axios==1.6.2` - HTTP client

## Usage

1. **Start the application** using one of the setup methods above
2. **Upload a PDF** by dragging it to the upload area or clicking to select
3. **Wait for processing** - the system will extract text, create chunks, and generate embeddings
4. **Ask questions** about the document content in the chat interface
5. **View answers** with source citations showing which parts of the document were used

## Error Handling

- **PDF parsing failures** return 400 errors with details
- **Empty queries** are rejected with validation messages
- **Groq API failures** trigger fallback responses
- **No relevant content** returns the standard "insufficient information" message

## Logging

The application logs all major operations:
- PDF processing start/completion
- Chunk creation counts
- Query processing and results
- Errors with full context

Logs use Python's standard logging module with INFO level for operations and ERROR for exceptions.

---

This implementation follows the exact specifications from instructions.md, ensuring grounded responses and preventing hallucinations through strict prompt engineering and fallback mechanisms.
