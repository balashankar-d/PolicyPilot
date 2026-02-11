"""
RAG Chain Orchestrator.

Multi-step pipeline that chains together:
  1. Intent & Entity Extraction
  2. User memory context injection
  3. History-aware document retrieval
  4. Chunk re-ranking
  5. LLM response generation
  6. Response validation / hallucination guard
  7. Personal info auto-extraction & memory update

All steps are modular and can be individually swapped or extended.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from intent_extractor import IntentExtractor
from user_memory import UserMemoryManager
from conversation_memory import ConversationMemory
from retrieval import Retriever
from reranker import ChunkReranker
from llm_client import GroqLLMClient
from response_validator import ResponseValidator, FALLBACK_ANSWER

logger = logging.getLogger(__name__)


class RAGChain:
    """
    Orchestrates the full advanced RAG pipeline.

    Usage:
        chain = RAGChain(retriever, llm_client, ...)
        result = chain.run(query, user_id, db)
    """

    def __init__(
        self,
        retriever: Retriever,
        llm_client: GroqLLMClient,
        conversation_memory: ConversationMemory,
        intent_extractor: IntentExtractor,
        user_memory_manager: UserMemoryManager,
        reranker: ChunkReranker,
        response_validator: ResponseValidator,
    ):
        self.retriever = retriever
        self.llm = llm_client
        self.memory = conversation_memory
        self.intent_extractor = intent_extractor
        self.user_memory = user_memory_manager
        self.reranker = reranker
        self.validator = response_validator
        self.logger = logger

    # ------------------------------------------------------------------ #
    #  Main entry-point                                                    #
    # ------------------------------------------------------------------ #

    def run(self, query: str, user_id: int, db: Session) -> Dict[str, Any]:
        """
        Execute the full RAG pipeline.

        Args:
            query: User question.
            user_id: Authenticated user ID.
            db: SQLAlchemy session.

        Returns:
            Dict with answer, sources, metadata, and validation info.
        """
        self.logger.info(f"=== RAG Chain started for user {user_id} ===")

        # ------ Step 1: Conversation history ------
        history_items = self.memory.get_recent_history(db, user_id)
        history_context = self.memory.format_history_context(history_items)
        last_exchange = self.memory.get_last_exchange(db, user_id)
        self.logger.info(
            f"Step 1 — History: {len(history_items)} items, "
            f"last_exchange={'yes' if last_exchange else 'no'}"
        )

        # ------ Step 2: Intent & Entity Extraction ------
        # Pass last_exchange explicitly so the extractor can resolve
        # vague follow-ups like "tell me more" or "what about eligibility?"
        intent_result = self.intent_extractor.extract(
            query, history_context, last_exchange=last_exchange
        )
        search_query = intent_result.get("search_query", query)
        intent = intent_result.get("intent", "question")
        is_followup = intent_result.get("is_followup", False)
        personal_info = intent_result.get("personal_info", {})
        self.logger.info(
            f"Step 2 — Intent: {intent}, followup: {is_followup}, "
            f"search_query: {search_query[:80]}"
        )

        # ------ Step 3: Auto-extract & store personal info ------
        if personal_info:
            self.user_memory.update_from_extracted_info(db, user_id, personal_info)
            self.logger.info(f"Step 3 — Stored personal info keys: {list(personal_info.keys())}")

        # ------ Step 4: User context (profile + memory) ------
        user_context = self.user_memory.format_user_context(db, user_id)
        self.logger.info(f"Step 4 — User context length: {len(user_context)} chars")

        # ------ Step 4b: Handle greetings / pure conversational intents ------
        # Greetings and simple conversational messages don't need document
        # retrieval at all — let the LLM respond naturally using only the
        # user context and conversation history.
        if intent in ("greeting",):
            enriched_context = self._build_enriched_context(
                [], history_context, user_context
            )
            # Even an empty enriched_context is okay — the LLM can greet back
            if not enriched_context.strip():
                enriched_context = "(No documents or history available yet.)"
            llm_result = self.llm.generate_answer(query, enriched_context, chat_history="")
            answer = llm_result.get("answer", "Hello! How can I help you?")
            self._save_conversation(db, user_id, query, answer, [], True)
            return self._build_response(
                answer=answer,
                sources=[],
                success=True,
                message="Greeting handled",
                intent=intent,
                validation={"is_valid": True, "is_grounded": True,
                             "confidence": "high", "flags": ["greeting"]},
            )

        # ------ Step 5: Document retrieval ------
        retrieval_result = self.retriever.retrieve_relevant_chunks(
            search_query, user_id=user_id
        )
        chunks = retrieval_result.get("chunks", [])
        sources = retrieval_result.get("sources", [])
        self.logger.info(f"Step 5 — Retrieved {len(chunks)} chunks")

        # Handle no-document case —
        # If this is a follow-up question AND we have conversation history,
        # we should still let the LLM answer using the history context rather
        # than returning a hard fallback.  Only bail out if there is truly
        # nothing to work with (no chunks AND no history).
        if not chunks and not history_context:
            answer = FALLBACK_ANSWER
            self._save_conversation(db, user_id, query, answer, [], False)
            return self._build_response(
                answer=answer,
                sources=[],
                success=True,
                message="No relevant information found",
                intent=intent,
                validation={"is_valid": True, "is_grounded": True,
                             "confidence": "high", "flags": ["no_documents"]},
            )

        # ------ Step 6: Re-rank chunks ------
        if chunks:
            rerank_result = self.reranker.rerank(search_query, chunks)
            ranked_chunks = rerank_result["ranked_chunks"]
            self.logger.info(f"Step 6 — Re-ranked to {len(ranked_chunks)} chunks")
        else:
            ranked_chunks = []
            self.logger.info("Step 6 — No chunks to re-rank (follow-up with history only)")

        # ------ Step 7: Build enriched context ------
        enriched_context = self._build_enriched_context(
            ranked_chunks, history_context, user_context
        )
        self.logger.info(f"Step 7 — Enriched context: {len(enriched_context)} chars")

        # ------ Step 8: LLM generation ------
        llm_result = self.llm.generate_answer(query, enriched_context, chat_history="")
        raw_answer = llm_result.get("answer", FALLBACK_ANSWER)
        self.logger.info(f"Step 8 — LLM success: {llm_result.get('success')}")

        # ------ Step 9: Response validation ------
        # Build a combined grounding corpus that includes document chunks,
        # conversation history, and user context so the validator doesn't
        # penalise answers that reference prior exchanges or user details.
        grounding_corpus = list(ranked_chunks)
        if history_context:
            grounding_corpus.append(history_context)
        if user_context:
            grounding_corpus.append(user_context)

        validation = self.validator.validate(
            answer=raw_answer,
            context_chunks=grounding_corpus,
            sources=sources,
            query=query,
        )
        final_answer = validation["answer"]
        self.logger.info(
            f"Step 9 — Validation: grounded={validation['is_grounded']}, "
            f"confidence={validation['confidence']}"
        )

        # ------ Step 10: Save conversation ------
        self._save_conversation(
            db, user_id, query, final_answer, sources,
            was_successful=validation["is_valid"],
        )

        self.logger.info("=== RAG Chain completed ===")

        return self._build_response(
            answer=final_answer,
            sources=sources,
            success=llm_result.get("success", False),
            message=llm_result.get("message", ""),
            intent=intent,
            validation=validation,
        )

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _build_enriched_context(
        self, chunks: list, history_context: str, user_context: str
    ) -> str:
        """Combine document chunks, conversation history, and user context."""
        parts: list[str] = []

        if user_context:
            parts.append(f"[User Context]\n{user_context}")

        if history_context:
            parts.append(f"[Conversation History]\n{history_context}")

        if chunks:
            chunk_text = "\n\n".join(
                f"Document {i}:\n{c.strip()}" for i, c in enumerate(chunks, 1)
            )
            parts.append(f"[Retrieved Documents]\n{chunk_text}")

        return "\n\n---\n\n".join(parts)

    def _save_conversation(
        self, db: Session, user_id: int, query: str, answer: str,
        sources: list, was_successful: bool
    ) -> None:
        """Persist the conversation turn."""
        try:
            self.memory.save_conversation(
                db, user_id, query, answer,
                sources=sources, was_successful=was_successful,
            )
        except Exception as e:
            self.logger.error(f"Failed to save conversation: {e}")

    @staticmethod
    def _build_response(
        answer: str, sources: list, success: bool,
        message: str, intent: str, validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "answer": answer,
            "sources": sources,
            "success": success,
            "message": message,
            "intent": intent,
            "confidence": validation.get("confidence", "unknown"),
            "is_grounded": validation.get("is_grounded", False),
            "flags": validation.get("flags", []),
        }
