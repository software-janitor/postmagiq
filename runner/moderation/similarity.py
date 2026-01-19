"""Similarity checker for plagiarism detection.

Checks if generated content is too similar to source material.
Uses multiple approaches:
- N-gram overlap (fast, local)
- Semantic similarity via embeddings (optional, requires API)

Usage:
    checker = SimilarityChecker()
    result = checker.compute_similarity(generated, source)

    if result.score > 0.8:
        print(f"Too similar: {result.matching_phrases}")
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SimilarityResult:
    """Result of similarity comparison."""
    score: float  # 0.0 to 1.0
    matching_phrases: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


class SimilarityChecker:
    """Check content similarity for plagiarism detection.

    Uses n-gram overlap for fast local comparison.
    For more accurate results, use semantic similarity via embeddings.

    Usage:
        checker = SimilarityChecker(ngram_size=3)
        result = checker.compute_similarity(content, source)

        if result.score > 0.8:
            # Content is too similar to source
            ...
    """

    def __init__(
        self,
        ngram_size: int = 3,
        min_phrase_length: int = 4,
    ):
        """Initialize similarity checker.

        Args:
            ngram_size: Size of n-grams to compare (default 3 = trigrams)
            min_phrase_length: Minimum words for a matching phrase
        """
        self.ngram_size = ngram_size
        self.min_phrase_length = min_phrase_length

    def compute_similarity(
        self, content: str, source: str
    ) -> SimilarityResult:
        """Compute similarity between content and source.

        Args:
            content: The generated content
            source: The source material

        Returns:
            SimilarityResult with score and matching phrases
        """
        # Normalize text
        content_words = self._normalize(content)
        source_words = self._normalize(source)

        if not content_words or not source_words:
            return SimilarityResult(score=0.0)

        # Compute n-gram overlap
        content_ngrams = self._get_ngrams(content_words)
        source_ngrams = self._get_ngrams(source_words)

        if not content_ngrams or not source_ngrams:
            return SimilarityResult(score=0.0)

        # Count overlapping n-grams
        overlap = content_ngrams & source_ngrams
        overlap_count = sum(overlap.values())
        total_content = sum(content_ngrams.values())

        # Calculate Jaccard-like similarity
        score = overlap_count / total_content if total_content > 0 else 0.0

        # Find matching phrases
        matching_phrases = self._find_matching_phrases(
            content_words, source_words
        )

        return SimilarityResult(
            score=min(score, 1.0),
            matching_phrases=matching_phrases[:10],  # Top 10 matches
            details={
                "ngram_size": self.ngram_size,
                "overlap_count": overlap_count,
                "total_ngrams": total_content,
            },
        )

    def _normalize(self, text: str) -> list[str]:
        """Normalize text for comparison."""
        # Lowercase, remove punctuation, split into words
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        words = text.split()
        return [w for w in words if len(w) > 1]

    def _get_ngrams(self, words: list[str]) -> Counter:
        """Generate n-grams from word list."""
        if len(words) < self.ngram_size:
            return Counter()

        ngrams = [
            tuple(words[i:i + self.ngram_size])
            for i in range(len(words) - self.ngram_size + 1)
        ]
        return Counter(ngrams)

    def _find_matching_phrases(
        self, content_words: list[str], source_words: list[str]
    ) -> list[str]:
        """Find matching phrases between content and source."""
        matches = []
        source_set = set(" ".join(source_words[i:i+self.min_phrase_length])
                        for i in range(len(source_words) - self.min_phrase_length + 1))

        # Slide window over content
        for i in range(len(content_words) - self.min_phrase_length + 1):
            phrase = " ".join(content_words[i:i+self.min_phrase_length])
            if phrase in source_set:
                # Extend the match as far as possible
                end = i + self.min_phrase_length
                while end < len(content_words):
                    extended = " ".join(content_words[i:end+1])
                    if extended in source_set or self._is_in_source(
                        content_words[i:end+1], source_words
                    ):
                        end += 1
                    else:
                        break

                full_phrase = " ".join(content_words[i:end])
                if full_phrase not in matches:
                    matches.append(full_phrase)

        # Sort by length (longest first)
        matches.sort(key=len, reverse=True)
        return matches

    def _is_in_source(self, phrase_words: list[str], source_words: list[str]) -> bool:
        """Check if phrase exists in source."""
        phrase_len = len(phrase_words)
        for i in range(len(source_words) - phrase_len + 1):
            if source_words[i:i+phrase_len] == phrase_words:
                return True
        return False


class SemanticSimilarityChecker:
    """Check semantic similarity using embeddings.

    More accurate than n-gram overlap for paraphrased content.
    Requires OpenAI API for embeddings.

    Usage:
        checker = SemanticSimilarityChecker(api_key="...")
        result = await checker.compute_similarity(content, source)
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        """Initialize with OpenAI API key."""
        self.api_key = api_key
        self.model = model

    async def compute_similarity(
        self, content: str, source: str
    ) -> SimilarityResult:
        """Compute semantic similarity using embeddings.

        Args:
            content: The generated content
            source: The source material

        Returns:
            SimilarityResult with cosine similarity score
        """
        if not self.api_key:
            # Fall back to n-gram similarity
            basic = SimilarityChecker()
            return basic.compute_similarity(content, source)

        try:
            from openai import AsyncOpenAI
            import numpy as np

            client = AsyncOpenAI(api_key=self.api_key)

            # Get embeddings for both texts
            response = await client.embeddings.create(
                model=self.model,
                input=[content, source],
            )

            content_embedding = np.array(response.data[0].embedding)
            source_embedding = np.array(response.data[1].embedding)

            # Compute cosine similarity
            similarity = np.dot(content_embedding, source_embedding) / (
                np.linalg.norm(content_embedding) * np.linalg.norm(source_embedding)
            )

            return SimilarityResult(
                score=float(similarity),
                matching_phrases=[],  # Semantic similarity doesn't identify phrases
                details={
                    "method": "semantic",
                    "model": self.model,
                },
            )

        except ImportError:
            # Fall back to n-gram
            basic = SimilarityChecker()
            return basic.compute_similarity(content, source)
        except Exception as e:
            # API error, fall back
            basic = SimilarityChecker()
            result = basic.compute_similarity(content, source)
            result.details["warning"] = f"Semantic check failed: {str(e)}"
            return result
