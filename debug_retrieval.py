"""Debug script to check what's stored in ChromaDB and test retrieval."""

import sys
import os
sys.path.append('.')

from vector_store import VectorStore
from retrieval import Retriever
from embeddings import EmbeddingModel
from config import get_settings

# Initialize components
settings = get_settings()
vector_store = VectorStore(settings.persist_directory)
embedding_model = EmbeddingModel(settings.embedding_model)
retriever = Retriever(vector_store, embedding_model, settings.top_k_results)

print("=== ChromaDB Debug Information ===")
print(f"Total documents in store: {vector_store.get_collection_count()}")

# Test a simple query
test_queries = [
    "What is this about?",
    "What is the main topic?",
    "Tell me about the content",
    "Summary"
]

for query in test_queries:
    print(f"\n--- Testing query: '{query}' ---")
    
    # Get retrieval results
    retrieval_result = retriever.retrieve_relevant_chunks(query)
    
    print(f"Is relevant: {retrieval_result['is_relevant']}")
    print(f"Number of chunks found: {len(retrieval_result['chunks'])}")
    print(f"Sources: {retrieval_result['sources']}")
    
    if retrieval_result['chunks']:
        print("First chunk preview:")
        print(retrieval_result['chunks'][0][:200] + "...")
    else:
        print("No chunks retrieved!")

print("\n=== Raw ChromaDB Query Test ===")
# Test ChromaDB directly
try:
    raw_results = vector_store.query("document content", n_results=3)
    print(f"Raw ChromaDB results: {len(raw_results['documents'])} documents")
    if raw_results['documents']:
        print("First document preview:")
        print(raw_results['documents'][0][:200] + "...")
except Exception as e:
    print(f"Error with raw query: {e}")
