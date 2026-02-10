"""LLM client for Groq API integration with conversation memory support."""

from groq import Groq
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class GroqLLMClient:
    """Client for interacting with Groq API using Mixtral model."""
    
    def __init__(self, api_key: str, model_name: str = "mixtral-8x7b-32768"):
        """
        Initialize Groq client.
        
        Args:
            api_key: Groq API key
            model_name: Model name to use (default: mixtral-8x7b-32768)
        """
        self.api_key = api_key
        self.model_name = model_name
        self.logger = logger
        
        try:
            self.client = Groq(api_key=api_key)
            self.logger.info(f"Initialized Groq client with model: {model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Groq client: {str(e)}")
            raise
    
    def build_prompt(self, query: str, context: str, chat_history: str = "") -> str:
        """
        Build the prompt for the LLM following the MANDATORY prompt template.
        
        This follows the exact structure specified in instructions.md for
        hallucination control and grounded answers.
        
        Args:
            query: User's current question
            context: Retrieved document context
            chat_history: Previous conversation context (optional)
            
        Returns:
            Formatted prompt string
        """
        # MANDATORY prompt template as specified in the task requirements
        prompt = """You are a document-based assistant.

You MUST answer only using:
1. Retrieved document content
2. Relevant previous conversation context

Do NOT use external knowledge.

If the answer is not present, respond exactly with:
"Sorry, this document does not contain enough information to answer that."

"""
        # Add previous conversation if available
        if chat_history and chat_history.strip():
            prompt += f"Previous Conversation:\n{chat_history.strip()}\n\n"
        else:
            prompt += "Previous Conversation:\nNo previous conversation.\n\n"
        
        # Add document context
        prompt += f"Document Context:\n{context.strip()}\n\n"
        
        # Add current question
        prompt += f"User Question:\n{query.strip()}\n\nAnswer:"
        
        return prompt
    
    def generate_answer(self, query: str, context: str, chat_history: str = "") -> Dict[str, Any]:
        """
        Generate an answer using the Groq API with conversation memory support.
        
        Args:
            query: User's question
            context: Retrieved document context
            chat_history: Previous conversation history (optional)
            
        Returns:
            Dictionary containing the answer and metadata
        """
        try:
            if not query or not query.strip():
                raise ValueError("Empty query provided")
            
            # If no context, return fallback response immediately
            if not context or not context.strip():
                fallback_response = "Sorry, this document does not contain enough information to answer that."
                self.logger.warning("No context provided, returning fallback response")
                return {
                    "answer": fallback_response,
                    "success": True,
                    "used_context": False,
                    "message": "No relevant context found"
                }
            
            # Build the prompt with conversation history
            prompt = self.build_prompt(query.strip(), context.strip(), chat_history)
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful document-based assistant. You answer questions ONLY using the provided document content and previous conversation context. Never use external knowledge. If the answer is not in the provided content, say so clearly."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1024,
                temperature=0.1,  # Low temperature for consistent, factual responses
                top_p=0.9
            )
            
            # Extract the answer
            answer = response.choices[0].message.content.strip()
            
            if not answer:
                raise ValueError("Empty response from Groq API")
            
            self.logger.info(f"Generated answer for query: {query[:50]}...")
            
            return {
                "answer": answer,
                "success": True,
                "used_context": True,
                "message": "Answer generated successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error generating answer with Groq: {str(e)}")
            
            # Return fallback response on error
            fallback_response = "Sorry, this document doesn't contain enough information to answer that."
            return {
                "answer": fallback_response,
                "success": False,
                "used_context": False,
                "message": f"Error occurred: {str(e)}"
            }
