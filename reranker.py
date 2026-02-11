"""
Chunk Re-Ranking Module.

Re-ranks retrieved document chunks using cross-encoder scoring
to improve relevance ordering. Falls back to keyword-based scoring
when the cross-encoder model is unavailable.
"""

import logging
from typing import List, Dict, Any, Tuple
import re
from collections import Counter

logger = logging.getLogger(__name__)

# Try to import cross-encoder; fall back to keyword scoring if unavailable
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False


class ChunkReranker:
    """
    Re-ranks retrieved chunks to surface the most relevant ones.
    
    Strategy:
      1. Receive top-K chunks from the vector store (e.g. K=5).
      2. Score each chunk against the query using a cross-encoder.
      3. Return the top-N chunks (e.g. N=3) in descending relevance.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
                 top_n: int = 3, use_cross_encoder: bool = True):
        """
        Args:
            model_name: HuggingFace cross-encoder model name.
            top_n: Number of chunks to keep after re-ranking.
            use_cross_encoder: Whether to attempt cross-encoder loading.
        """
        self.top_n = top_n
        self.cross_encoder = None
        self.logger = logger

        if use_cross_encoder and CROSS_ENCODER_AVAILABLE:
            try:
                self.cross_encoder = CrossEncoder(model_name, max_length=512)
                self.logger.info(f"Loaded cross-encoder model: {model_name}")
            except Exception as e:
                self.logger.warning(f"Cross-encoder load failed, using keyword fallback: {e}")
        else:
            self.logger.info("Using keyword-based re-ranking (cross-encoder not available)")

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def rerank(self, query: str, chunks: List[str],
               metadatas: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
        """
        Re-rank a list of chunks against the query.

        Args:
            query: User query.
            chunks: List of document chunk texts.
            metadatas: Optional parallel list of metadata dicts.

        Returns:
            Dict with keys:
              - ranked_chunks: re-ordered chunk texts (top-N)
              - ranked_metadatas: corresponding metadatas (if provided)
              - scores: relevance scores for the returned chunks
        """
        if not chunks:
            return {"ranked_chunks": [], "ranked_metadatas": [], "scores": []}

        if len(chunks) <= self.top_n:
            # Nothing to trim — return as-is with neutral scores
            return {
                "ranked_chunks": list(chunks),
                "ranked_metadatas": list(metadatas) if metadatas else [],
                "scores": [1.0] * len(chunks),
            }

        # Score every chunk
        if self.cross_encoder is not None:
            scored = self._score_cross_encoder(query, chunks)
        else:
            scored = self._score_keyword(query, chunks)

        # Sort descending by score
        scored.sort(key=lambda x: x[1], reverse=True)

        # Keep top-N
        top_indices = [idx for idx, _ in scored[: self.top_n]]
        top_scores  = [score for _, score in scored[: self.top_n]]
        top_chunks  = [chunks[i] for i in top_indices]
        top_metas   = [metadatas[i] for i in top_indices] if metadatas else []

        self.logger.info(
            f"Re-ranked {len(chunks)} chunks → kept top {len(top_chunks)} "
            f"(scores: {[round(s, 4) for s in top_scores]})"
        )

        return {
            "ranked_chunks": top_chunks,
            "ranked_metadatas": top_metas,
            "scores": top_scores,
        }

    # ------------------------------------------------------------------ #
    #  Scoring strategies                                                  #
    # ------------------------------------------------------------------ #

    def _score_cross_encoder(self, query: str, chunks: List[str]) -> List[Tuple[int, float]]:
        """Score using the cross-encoder model."""
        pairs = [[query, chunk] for chunk in chunks]
        scores = self.cross_encoder.predict(pairs)
        return [(i, float(s)) for i, s in enumerate(scores)]

    def _score_keyword(self, query: str, chunks: List[str]) -> List[Tuple[int, float]]:
        """
        Lightweight keyword-overlap scoring.

        Combines:
          - Jaccard similarity on lowercased words
          - Term frequency boost for query terms in the chunk
        """
        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            return [(i, 0.0) for i in range(len(chunks))]

        scored: List[Tuple[int, float]] = []
        for i, chunk in enumerate(chunks):
            chunk_tokens = self._tokenize(chunk)
            chunk_set = set(chunk_tokens)

            # Jaccard similarity
            intersection = query_tokens & chunk_set
            union = query_tokens | chunk_set
            jaccard = len(intersection) / len(union) if union else 0.0

            # Term-frequency boost: how many times query tokens appear in chunk
            freq = Counter(chunk_tokens)
            tf_score = sum(freq.get(t, 0) for t in query_tokens) / max(len(chunk_tokens), 1)

            # Weighted combination
            score = 0.6 * jaccard + 0.4 * tf_score
            scored.append((i, score))

        return scored

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple whitespace + punctuation tokenizer."""
        return re.findall(r"\b\w+\b", text.lower())
