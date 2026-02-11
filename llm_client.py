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
        
        The context block arriving here is *enriched* — it already contains
        clearly labelled sections:
          [User Context]          – profile, preferences, memories
          [Conversation History]  – recent Q&A pairs (and optional summary)
          [Retrieved Documents]   – top-ranked document chunks
        
        This method wraps them with explicit instructions so the LLM knows
        exactly how to leverage each section for personalised, follow-up-aware
        answers.
        
        Args:
            query: User's current question
            context: Enriched context string with labelled sections
            chat_history: Additional chat history override (optional)
            
        Returns:
            Formatted prompt string
        """
        prompt = """You are a document-based policy assistant called PolicyPilot.

RULES — follow them strictly:
1. Base your answers primarily on the [Retrieved Documents] provided below.
2. If [User Context] is present, PERSONALIZE your answer to the user's
   specific situation (e.g. their state, occupation, income, category, age).
   Address the user by name if known. Every policy fact you state must
   still come from the [Retrieved Documents].
3. If [Conversation History] is present, use it to resolve follow-up
   questions. When the user says things like "tell me more", "what about
   eligibility?", "explain that", "can you summarize that?", or uses
   pronouns like "it" or "that", look at the previous Q&A exchanges in the
   Conversation History to understand what they are referring to, and
   answer accordingly.  You MAY use information from your previous answers
   in the conversation history to provide continuity.
4. For greetings, clarifications, or conversational messages (e.g. "hi",
   "thanks", "who are you?"), respond naturally and helpfully.  You do NOT
   need to cite documents for these.
5. When quoting a policy or rule from documents, mention the source document
   name if known.
6. ONLY if the user asks a specific policy/document question AND neither the
   [Retrieved Documents] nor the [Conversation History] contain relevant
   information, respond with:
   "Sorry, this document does not contain enough information to answer that."
7. Do NOT fabricate policy details that are not in the provided context.
8. Keep answers concise, clear, and well-structured.

"""
        # Chat history (if supplied separately — the enriched context already
        # contains history, but the caller may pass an override)
        if chat_history and chat_history.strip():
            prompt += f"Previous Conversation:\n{chat_history.strip()}\n\n"

        # Main context block (already includes user context + history + docs)
        prompt += f"Context:\n{context.strip()}\n\n"

        # Current question
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
                        "content": (
                            "You are PolicyPilot, a helpful document-based policy assistant. "
                            "You answer policy questions using the provided [Retrieved Documents] "
                            "and do not fabricate policy details.\n\n"
                            "PERSONALIZATION: If a [User Context] section is present, tailor "
                            "your answer to the user's profile (state, occupation, income, "
                            "category, age, name, etc.).\n\n"
                            "FOLLOW-UPS & CONVERSATION: If a [Conversation History] section is "
                            "present, use it to resolve follow-up questions. When the user says "
                            "'tell me more', 'what about eligibility?', 'explain that', or uses "
                            "pronouns like 'it'/'that', refer to the previous exchanges to "
                            "understand the topic and answer in full context. You may reference "
                            "information from your own prior answers in the history.\n\n"
                            "GREETINGS & CHAT: For greetings, thanks, or conversational messages, "
                            "respond naturally. You do NOT need document citations for these.\n\n"
                            "CITATIONS: Cite the source document name when quoting policy.\n\n"
                            "Only say you cannot answer if the user asks a specific policy question "
                            "and neither the documents nor conversation history contain the answer."
                        )
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
