"""
Intent & Entity Extraction Module.

Uses the LLM to extract structured intent and entities from user queries,
enabling smarter retrieval and personalized responses.
"""

import json
import logging
from typing import Dict, Any, Optional
from groq import Groq

logger = logging.getLogger(__name__)


class IntentExtractor:
    """Extracts intent, entities, and key information from user queries using LLM."""
    
    def __init__(self, client: Groq, model_name: str):
        self.client = client
        self.model_name = model_name
        self.logger = logger
    
    def extract(self, query: str, conversation_history: str = "",
                last_exchange: dict = None) -> Dict[str, Any]:
        """
        Extract intent and entities from a user query.
        
        Args:
            query: The user's current question
            conversation_history: Formatted recent conversation context
            last_exchange: Dict with "question" and "answer" of the most
                           recent Q&A pair (used for follow-up resolution)
            
        Returns:
            Dictionary with intent, entities, search_query, is_followup, personal_info
        """
        try:
            prompt = self._build_extraction_prompt(query, conversation_history, last_exchange)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an intent and entity extraction engine. "
                            "You output ONLY valid JSON. No explanations, no markdown."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=512,
                temperature=0.0,
                top_p=0.9
            )
            
            raw = response.choices[0].message.content.strip()
            # Clean markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()
            
            result = json.loads(raw)
            self.logger.info(f"Extracted intent: {result.get('intent', 'unknown')}")
            return result
            
        except (json.JSONDecodeError, Exception) as e:
            self.logger.warning(f"Intent extraction failed, using defaults: {e}")
            return {
                "intent": "question",
                "entities": [],
                "search_query": query,
                "is_followup": bool(conversation_history),
                "personal_info": {}
            }
    
    def _build_extraction_prompt(self, query: str, history: str,
                                  last_exchange: dict = None) -> str:
        """Build the extraction prompt with follow-up resolution context."""
        prompt = """Analyze the following user query and extract structured information.
Your MOST IMPORTANT job is to produce a good "search_query" — a self-contained
search string that can be used to find relevant documents in a vector database.

"""
        # Give the extractor the last Q&A pair explicitly so it can resolve
        # vague follow-ups like "tell me more", "what about eligibility?", etc.
        if last_exchange:
            prompt += "=== LAST Q&A EXCHANGE ===\n"
            prompt += f"User asked: {last_exchange.get('question', '')}\n"
            # Truncate long answers to keep prompt reasonable
            prev_answer = last_exchange.get("answer", "")
            if len(prev_answer) > 500:
                prev_answer = prev_answer[:500] + "…"
            prompt += f"Assistant answered: {prev_answer}\n\n"
        
        if history and not last_exchange:
            prompt += f"Recent conversation:\n{history}\n\n"
        
        prompt += f"""Current query: "{query}"

Return a JSON object with exactly these fields:
{{
  "intent": "question" | "followup" | "greeting" | "clarification" | "personal_update",
  "entities": ["list of key entities mentioned"],
  "search_query": "<CRITICAL: If the current query is vague or a follow-up (e.g. 'tell me more', 'what about eligibility?', 'explain that'), you MUST rewrite it into a fully self-contained search query by combining it with the topic from the LAST Q&A EXCHANGE above. Never return a vague search_query.>",
  "is_followup": true/false,
  "personal_info": {{}}
}}

For personal_info, extract any user details mentioned like name, state, occupation, income, age, category.
Only include fields that are explicitly stated.

Output ONLY the JSON object, nothing else."""
        
        return prompt
    
    def extract_personal_info(self, query: str) -> Dict[str, str]:
        """
        Extract personal information from a user's message.
        Used to auto-populate user memory from conversation.
        
        Args:
            query: User's message
            
        Returns:
            Dictionary of personal info fields found
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract personal information from the user message. "
                            "Return ONLY a JSON object. Empty {} if nothing found."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f'Message: "{query}"\n\n'
                            "Extract any of: name, state, occupation, income, age, category.\n"
                            "Return ONLY JSON like: {\"name\": \"...\", \"state\": \"...\"}\n"
                            "Only include fields explicitly mentioned. Empty {} if none."
                        )
                    }
                ],
                max_tokens=256,
                temperature=0.0
            )
            
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()
            
            return json.loads(raw)
        except Exception as e:
            self.logger.debug(f"No personal info extracted: {e}")
            return {}
