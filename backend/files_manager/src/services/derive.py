"""Lightweight derived fields computed from a sample's captions/dimensions.

No ML models are used; these are cheap, deterministic signals. Shared by the
files service and (later) reused by the ingestion step.
"""
import re
from typing import List

_WORD_RE = re.compile(r"[a-z']+")


def _tokens(text: str) -> List[str]:
    if not text:
        return []
    return _WORD_RE.findall(text.lower())


def compute_caption_length(captions: List[str]) -> int:
    """Average word count across the captions (rounded)."""
    counts = [len(_tokens(caption)) for caption in captions if caption]
    if len(counts) == 0:
        return 0
    return round(sum(counts) / len(counts))


def compute_agreement(captions: List[str]) -> float:
    """Average pairwise Jaccard similarity of caption token-sets (0..1).

    High = the human annotators described the image similarly (clear image);
    low = they diverged (ambiguous / complex image).
    """
    token_sets = [set(_tokens(caption)) for caption in captions if caption]
    count = len(token_sets)
    if count < 2:
        return 1.0

    total = 0.0
    pairs = 0
    for i in range(count):
        for j in range(i + 1, count):
            union = token_sets[i] | token_sets[j]
            if len(union) == 0:
                similarity = 0.0
            else:
                similarity = len(token_sets[i] & token_sets[j]) / len(union)
            total += similarity
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
