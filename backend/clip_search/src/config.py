"""Configuration for the CLIP semantic-search service (read from environment)."""
import os

from shared_libraries.env import get_env, get_env_int

SERVICE_NAME = "clip"
HOST = get_env("CLIP_SERVICE_HOST", "0.0.0.0")
PORT = get_env_int("CLIP_SERVICE_PORT", 8000)

DATA_DIR = get_env("DATA_DIR", "/data")
IMAGES_DIR = get_env("IMAGES_DIR", os.path.join(DATA_DIR, "images"))

# Where the precomputed image embeddings are cached. Built once on first boot
# (background thread), then loaded instantly on every subsequent start.
EMBEDDINGS_PATH = get_env("CLIP_EMBEDDINGS_PATH", os.path.join(DATA_DIR, "embeddings.npz"))

# Open-source CLIP model that maps images AND text into one shared 512-d space.
MODEL_NAME = get_env("CLIP_MODEL_NAME", "clip-ViT-B-32")

# CLIP text queries work best with a short prompt template (image-side stays as-is).
TEXT_PROMPT_TEMPLATE = get_env("CLIP_TEXT_PROMPT", "a photo of {query}")

# Minimum cosine similarity for a real semantic match (clip-ViT-B-32, photo prompt).
# Calibrated on Flickr8k: strong matches ~0.26+, unrelated images ~0.14–0.22.
# Applied to the full index — result count depends on meaning, not dataset size.
MIN_SCORE = float(get_env("CLIP_MIN_SCORE", "0.25"))

# After the absolute cutoff, stop at the first large score drop (end of the
# relevant cluster). Ignores how many images exist in the index.
SCORE_GAP = float(get_env("CLIP_SCORE_GAP", "0.012"))

# How many images to encode per forward pass while indexing (CPU-friendly).
INDEX_BATCH = get_env_int("CLIP_INDEX_BATCH", 32)

# Result-count guards for /search.
DEFAULT_LIMIT = get_env_int("CLIP_DEFAULT_LIMIT", 500)
MAX_LIMIT = get_env_int("CLIP_MAX_LIMIT", 2000)
