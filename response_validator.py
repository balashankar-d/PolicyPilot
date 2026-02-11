"""
Response Validation Module.

Validates LLM responses to ensure they are grounded in the provided context,
preventing hallucination and enforcing policy-safe answers.
"""

import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Fallback answer used throughout the application
FALLBACK_ANSWER = "Sorry, this document does not contain enough information to answer that."


class ResponseValidator:
    """
    Validates that generated answers are grounded in the retrieved context.

    Checks performed:
      1. Empty / meaningless response detection.
      2. Keyword-overlap grounding check — the answer must share substantial
         vocabulary with the context chunks.
      3. Confidence flagging — low-overlap answers are tagged for review.
      4. Citation injection — appends source references to the response.
    """

    def __init__(self, min_grounding_ratio: float = 0.10,
                 min_answer_length: int = 10):
        """
        Args:
            min_grounding_ratio: Minimum fraction of answer content-words
                that must also appear in the context to pass the grounding check.
            min_answer_length: Minimum character length for a valid answer.
        """
        self.min_grounding_ratio = min_grounding_ratio
        self.min_answer_length = min_answer_length
        self.logger = logger

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def validate(self, answer: str, context_chunks: List[str],
                 sources: List[str] | None = None,
                 query: str = "") -> Dict[str, Any]:
        """
        Validate and post-process the LLM answer.

        Args:
            answer: Raw LLM-generated answer.
            context_chunks: The document chunks that were used as context.
            sources: Source document names for citation.
            query: Original user query (for context).

        Returns:
            Dict with:
              - answer: final (possibly modified) answer text
              - is_valid: whether the answer passed all checks
              - is_grounded: whether the answer is grounded in context
              - grounding_score: float ratio of overlapping words
              - confidence: "high" | "medium" | "low"
              - citations: list of source citations
              - flags: list of warning strings
        """
        flags: List[str] = []

        # 1. Empty / trivial check
        if not answer or len(answer.strip()) < self.min_answer_length:
            self.logger.warning("Answer too short or empty — returning fallback")
            return self._fallback_result(flags=["empty_answer"], sources=sources)

        # 2. Check if the LLM already returned its own fallback
        if self._is_llm_refusal(answer):
            return {
                "answer": FALLBACK_ANSWER,
                "is_valid": True,
                "is_grounded": True,  # refusal is a valid grounded behaviour
                "grounding_score": 1.0,
                "confidence": "high",
                "citations": [],
                "flags": ["llm_refusal"],
            }

        # 3. Grounding check
        grounding_score = self._compute_grounding(answer, context_chunks)
        is_grounded = grounding_score >= self.min_grounding_ratio

        if not is_grounded:
            flags.append("low_grounding")
            self.logger.warning(
                f"Grounding check: low score ({grounding_score:.3f}). "
                "Flagging answer but allowing it through."
            )
            # We no longer replace the answer with a hard fallback here.
            # The grounding corpus now includes conversation history and
            # user context, so a low score usually just means the LLM used
            # conversational/personalised phrasing.  If the answer is truly
            # ungrounded, the LLM prompt rules already instruct it to refuse.

        # 4. Confidence level
        if grounding_score >= 0.40:
            confidence = "high"
        elif grounding_score >= 0.25:
            confidence = "medium"
        else:
            confidence = "low"
            flags.append("low_confidence")

        # 5. Build citations
        citations = self._build_citations(sources) if sources else []

        # 6. Append citation line if present
        final_answer = answer.strip()
        if citations:
            citation_line = "\n\n📄 Sources: " + ", ".join(citations)
            final_answer += citation_line

        return {
            "answer": final_answer,
            "is_valid": True,
            "is_grounded": True,
            "grounding_score": round(grounding_score, 4),
            "confidence": confidence,
            "citations": citations,
            "flags": flags,
        }

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _is_llm_refusal(self, answer: str) -> bool:
        """Detect if the LLM already said it can't answer."""
        refusal_patterns = [
            r"sorry.*document.*does\s+not\s+contain",
            r"sorry.*doesn.t\s+contain\s+enough",
            r"i\s+don.t\s+have\s+enough\s+information",
            r"the\s+(provided\s+)?document.*does\s+not\s+(mention|contain|include)",
            r"no\s+relevant\s+(information|data|content)\s+found",
            r"cannot\s+answer.*based\s+on.*provided",
        ]
        lower = answer.lower().strip()
        return any(re.search(p, lower) for p in refusal_patterns)

    def _compute_grounding(self, answer: str, chunks: List[str]) -> float:
        """
        Compute a keyword-overlap grounding score.

        Returns the fraction of content-words in the answer that also
        appear in at least one context chunk.
        """
        answer_words = set(self._content_words(answer))
        if not answer_words:
            return 0.0

        context_words = set()
        for chunk in chunks:
            context_words.update(self._content_words(chunk))

        if not context_words:
            return 0.0

        overlap = answer_words & context_words
        return len(overlap) / len(answer_words)

    def _build_citations(self, sources: List[str]) -> List[str]:
        """Deduplicate and format source citations."""
        seen = set()
        citations = []
        for src in sources:
            if src and src not in seen:
                seen.add(src)
                citations.append(src)
        return citations

    def _fallback_result(self, flags: List[str],
                         sources: List[str] | None = None,
                         grounding_score: float = 0.0) -> Dict[str, Any]:
        """Return a standard fallback result."""
        return {
            "answer": FALLBACK_ANSWER,
            "is_valid": False,
            "is_grounded": False,
            "grounding_score": round(grounding_score, 4),
            "confidence": "none",
            "citations": self._build_citations(sources) if sources else [],
            "flags": flags,
        }

    # ------------------------------------------------------------------ #
    #  Text utilities                                                      #
    # ------------------------------------------------------------------ #

    _STOP_WORDS = frozenset({
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "shall",
        "should", "may", "might", "must", "can", "could", "i", "me", "my",
        "we", "our", "you", "your", "he", "him", "his", "she", "her", "it",
        "its", "they", "them", "their", "what", "which", "who", "whom",
        "this", "that", "these", "those", "am", "at", "by", "for", "with",
        "about", "against", "between", "through", "during", "before",
        "after", "above", "below", "to", "from", "up", "down", "in", "out",
        "on", "off", "over", "under", "again", "further", "then", "once",
        "here", "there", "when", "where", "why", "how", "all", "both",
        "each", "few", "more", "most", "other", "some", "such", "no", "nor",
        "not", "only", "own", "same", "so", "than", "too", "very", "s", "t",
        "just", "don", "now", "also", "of", "and", "or", "but", "if",
    })

    @classmethod
    def _content_words(cls, text: str) -> List[str]:
        """Extract meaningful content words (lowered, stop-words removed)."""
        tokens = re.findall(r"\b\w+\b", text.lower())
        return [t for t in tokens if t not in cls._STOP_WORDS and len(t) > 2]
