"""Test the full API flow with a real query."""

import requests
import time

# Wait a moment for server to start
time.sleep(3)

# Test query
print("=== Testing full API query ===")

query_data = {
    "query": "What is this document about?"
}

try:
    response = requests.post("http://localhost:8000/query", json=query_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result['success']}")
        print(f"Answer: {result['answer']}")
        print(f"Sources: {result['sources']}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Request error: {e}")

# Test another query
print("\n=== Testing another query ===")

query_data2 = {
    "query": "Who wrote this letter?"
}

try:
    response2 = requests.post("http://localhost:8000/query", json=query_data2)
    print(f"Status: {response2.status_code}")
    
    if response2.status_code == 200:
        result2 = response2.json()
        print(f"Success: {result2['success']}")
        print(f"Answer: {result2['answer']}")
        print(f"Sources: {result2['sources']}")
    else:
        print(f"Error: {response2.text}")
        
except Exception as e:
    print(f"Request error: {e}")
