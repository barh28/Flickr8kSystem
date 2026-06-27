"""Lightweight derived fields computed from a sample's captions/dimensions.

No ML models are used; these are cheap, deterministic signals. Shared by the
files service and reused by the ingestion step.

Agreement measures how similarly the human annotators described the image.
Raw token Jaccard punishes harmless wording differences too hard (e.g.
"running" vs "jumps", "white and brown dog" vs "white dog with brown patches"
score very low even though they describe the same scene). To be smarter without
pulling in any ML model we:
  * drop stopwords so only content words count,
  * apply light stemming so word forms collapse (run/running/runs -> run),
  * compare captions with set cosine similarity (Otsuka-Ochiai), which is far
    less sensitive to caption length differences than Jaccard.
"""
import math
import re
from typing import List, Set

_WORD_RE = re.compile(r"[a-z']+")

# Common English function words that carry no scene content. Kept small and
# explicit (no external corpora) so ingestion stays dependency-free.
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "at", "by",
    "for", "with", "from", "into", "onto", "over", "under", "up", "down", "out",
    "off", "through", "as", "is", "are", "was", "were", "be", "been", "being",
    "am", "it", "its", "this", "that", "these", "those", "there", "here",
    "his", "her", "hers", "their", "theirs", "him", "she", "he", "they", "them",
    "you", "your", "we", "our", "i", "me", "my", "who", "whom", "which", "what",
    "while", "during", "near", "next", "then", "than", "so", "very", "some",
    "has", "have", "had", "do", "does", "did", "will", "would", "can", "could",
})


def _undouble(base: str) -> str:
    """Collapse a trailing doubled consonant left by -ing/-ed stripping.

    e.g. "running" -> "runn" -> "run". Uses len()-based indexing (no negative
    indices) so the logic also holds under C-compiled builds.
    """
    n = len(base)
    if n >= 2:
        last = base[n - 1]
        prev = base[n - 2]
        if last == prev and last not in "aeiou":
            return base[: n - 1]
    return base


def _stem(word: str) -> str:
    """Minimal suffix-stripping stemmer (good enough to align caption wording)."""
    n = len(word)
    if n > 4 and word.endswith("ies"):
        return word[: n - 3] + "y"
    if n > 4 and word.endswith("ing"):
        return _undouble(word[: n - 3])
    if n > 3 and word.endswith("ed"):
        return _undouble(word[: n - 2])
    if n > 3 and word.endswith("es"):
        return word[: n - 2]
    if n > 3 and word.endswith("s"):
        return word[: n - 1]
    return word


def _tokens(text: str) -> List[str]:
    if not text:
        return []
    return _WORD_RE.findall(text.lower())


def _content_stems(text: str) -> Set[str]:
    """Stopword-free, stemmed set of content words for one caption."""
    result: Set[str] = set()
    for token in _tokens(text):
        if token in _STOPWORDS:
            continue
        result.add(_stem(token))
    return result


def compute_caption_length(captions: List[str]) -> int:
    """Average word count across the captions (rounded)."""
    counts = [len(_tokens(caption)) for caption in captions if caption]
    if len(counts) == 0:
        return 0
    return round(sum(counts) / len(counts))


def _cosine(a: Set[str], b: Set[str]) -> float:
    """Set cosine similarity: |A∩B| / sqrt(|A|*|B|)."""
    if len(a) == 0 or len(b) == 0:
        return 0.0
    return len(a & b) / math.sqrt(len(a) * len(b))


def compute_agreement(captions: List[str]) -> float:
    """Mean pairwise content-word cosine similarity of the captions (0..1).

    High = annotators described the image similarly (clear image);
    low = they diverged (ambiguous / complex image).
    """
    stem_sets = [_content_stems(caption) for caption in captions if caption]
    count = len(stem_sets)
    if count < 2:
        return 1.0

    total = 0.0
    pairs = 0
    for i in range(count):
        for j in range(i + 1, count):
            total += _cosine(stem_sets[i], stem_sets[j])
            pairs += 1

    if pairs == 0:
        return 0.0
    return total / pairs


def compute_orientation(width: int, height: int) -> str:
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"
