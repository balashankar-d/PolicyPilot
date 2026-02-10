"""Test script to verify backend is working correctly."""

import requests
import os

# Test 1: Check status endpoint
print("Testing status endpoint...")
try:
    response = requests.get("http://localhost:8000/status")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Test file upload (if you have a sample PDF)
print("\nTesting file upload...")
try:
    # You can replace this with an actual PDF file path
    sample_files_dir = "."
    pdf_files = [f for f in os.listdir(sample_files_dir) if f.endswith('.pdf')]
    
    if pdf_files:
        pdf_path = pdf_files[0]
        print(f"Found PDF: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path, f, 'application/pdf')}
            response = requests.post("http://localhost:8000/upload_pdf", files=files)
            print(f"Upload status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {response.json()}")
            else:
                print(f"Error: {response.text}")
    else:
        print("No PDF files found in current directory")
        
except Exception as e:
    print(f"Upload error: {e}")

# Test 3: Test query endpoint
print("\nTesting query endpoint...")
try:
    query_data = {"query": "What is this document about?"}
    response = requests.post("http://localhost:8000/query", json=query_data)
    print(f"Query status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Answer: {result.get('answer', 'No answer')}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Query error: {e}")
