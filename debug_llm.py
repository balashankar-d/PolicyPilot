"""Debug script to test the LLM directly."""

import sys
sys.path.append('.')

from llm_client import GroqLLMClient
from config import get_settings

# Initialize LLM client
settings = get_settings()
print(f"Using Groq API Key: {settings.groq_api_key[:10]}...")
print(f"Using Model: {settings.model_name}")

llm_client = GroqLLMClient(settings.groq_api_key, settings.model_name)

# Test with sample context
test_context = """Akash Abraham 8th Semester Computer Science and Engineering Govt. Model Engineering College Thrikkakara, Kochi 05th December, 2025 The Principal Govt. Model Engineering College Thrikkakara, Kochi Subject: Request for No Objection Certificate (NOC) for Internship Dear Sir/Madam, I am writing to request a No Objection Certificate (NOC) to undertake an internship at [Company Name] from [Start Date] to [End Date]. This internship is part of my academic curriculum and will provide me with practical exposure to the industry. I have secured this internship opportunity and would like to proceed with the necessary formalities. I assure you that I will maintain the college's reputation and adhere to all guidelines during my internship period. I kindly request you to issue the NOC at your earliest convenience so that I can proceed with the internship formalities. Thank you for your consideration. Yours sincerely, Akash Abraham"""

test_query = "What is this document about?"

print(f"\n=== Testing LLM with context ===")
print(f"Query: {test_query}")
print(f"Context length: {len(test_context)} characters")

# Test LLM call
result = llm_client.generate_answer(test_query, test_context)

print(f"\n=== LLM Response ===")
print(f"Success: {result['success']}")
print(f"Answer: {result['answer']}")
print(f"Used context: {result['used_context']}")
print(f"Message: {result['message']}")

# Test with empty context
print(f"\n=== Testing with empty context ===")
result_empty = llm_client.generate_answer(test_query, "")
print(f"Answer with empty context: {result_empty['answer']}")

# Test the exact prompt format
print(f"\n=== Testing exact prompt format ===")
prompt = llm_client.build_prompt(test_query, test_context)
print("Generated prompt:")
print("="*50)
print(prompt)
print("="*50)
