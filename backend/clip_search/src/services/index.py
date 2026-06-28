"""Image embedding index for CLIP semantic search.

On startup we either load a cached embedding matrix or build it once in a
background thread (encoding every image under IMAGES_DIR). A text query is
embedded into the same space at request time and ranked by cosine similarity
(a single matrix-vector product over ~8k rows — milliseconds, no vector DB).

The image filename is the file id (see init_loader), so the index keys line up
directly with the files service / gateway image URLs.
"""
import glob
import os
import threading

import numpy as np
from PIL import Image

from src.config import (
    EMBEDDINGS_PATH,
    IMAGES_DIR,
    INDEX_BATCH,
    MIN_SCORE,
    MODEL_NAME,
    SCORE_GAP,
    TEXT_PROMPT_TEMPLATE,
)

_IMAGE_GLOBS = ("*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.webp")

# Guarded shared state. `_state` is a small status dict surfaced via /health.
_lock = threading.Lock()
_state = {"ready": False, "error": None, "indexed": 0, "total": 0}
_ids: list = []
_matrix: np.ndarray = np.zeros((0, 0), dtype=np.float32)
_model = None
_model_lock = threading.Lock()


class IndexNotReady(Exception):
    """Raised when a search arrives before the embedding index is built."""


def status() -> dict:
    with _lock:
        return dict(_state)


def _set_state(**updates) -> None:
    with _lock:
        _state.update(updates)


def _get_model():
    """Load the sentence-transformers CLIP model once (thread-safe, lazy)."""
    global _model
    with _model_lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(MODEL_NAME)
        return _model


def _list_image_paths() -> list:
    paths: list = []
    for pattern in _IMAGE_GLOBS:
        paths.extend(glob.glob(os.path.join(IMAGES_DIR, pattern)))
    return sorted(set(paths))


def _normalize(matrix: np.ndarray) -> np.ndarray:
    """L2-normalize rows so a dot product equals cosine similarity."""
    if matrix.size == 0:
        return matrix
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    zero_mask = norms[:, 0] == 0
    norms[zero_mask, 0] = 1.0
    return matrix / norms


def _encode_text(model, query: str) -> np.ndarray:
    """Embed a user query in CLIP text space using the standard photo prompt."""
    prompt = TEXT_PROMPT_TEMPLATE.format(query=query.strip())
    return np.asarray(
        model.encode(
            [prompt],
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        ),
        dtype=np.float32,
    )[0]


def _encode_images(model, images: list) -> np.ndarray:
    return np.asarray(
        model.encode(
            images,
            batch_size=len(images),
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        ),
        dtype=np.float32,
    )


def _select_meaningful(scores: np.ndarray, limit: int) -> list:
    """Pick semantically relevant matches from the full scored index.

    Two fixed rules (neither depends on how many images are indexed):
    1. Absolute floor — score must reach MIN_SCORE (real CLIP similarity).
    2. Score-gap cliff — stop when the next match drops sharply (unrelated tail).
    """
    above = np.where(scores >= MIN_SCORE)[0]
    if above.size == 0:
        return []

    ordered = above[np.argsort(-scores[above])]
    kept: list = [int(ordered[0])]
    for pos in range(1, ordered.size):
        prev_idx = int(ordered[pos - 1])
        curr_idx = int(ordered[pos])
        if scores[prev_idx] - scores[curr_idx] >= SCORE_GAP:
            break
        kept.append(curr_idx)

    if len(kept) > limit:
        kept = kept[:limit]
    return kept


def _save(ids: list, matrix: np.ndarray) -> None:
    os.makedirs(os.path.dirname(EMBEDDINGS_PATH) or ".", exist_ok=True)
    # Write to a temp file then atomically rename, so a crash mid-write can't
    # leave a half-written index that would later load as "ready". The temp name
    # ends in .npz so numpy doesn't append its own extension.
    tmp_path = f"{EMBEDDINGS_PATH}.tmp.npz"
    np.savez(tmp_path, ids=np.array(ids, dtype=object), matrix=matrix)
    os.replace(tmp_path, EMBEDDINGS_PATH)


def build() -> None:
    """Encode every image once and persist the normalized embedding matrix."""
    global _ids, _matrix
    try:
        paths = _list_image_paths()
        _set_state(total=len(paths), indexed=0, error=None)
        if not paths:
            _ids = []
            _matrix = np.zeros((0, 0), dtype=np.float32)
            _set_state(ready=True)
            return

        model = _get_model()
        ids: list = []
        chunks: list = []
        for start in range(0, len(paths), INDEX_BATCH):
            batch_paths = paths[start:start + INDEX_BATCH]
            images = []
            batch_ids = []
            for path in batch_paths:
                try:
                    with Image.open(path) as raw:
                        images.append(raw.convert("RGB"))
                    batch_ids.append(os.path.basename(path))
                except Exception:
                    continue
            if images:
                embeddings = _encode_images(model, images)
                chunks.append(embeddings)
                ids.extend(batch_ids)
            _set_state(indexed=min(start + INDEX_BATCH, len(paths)))
            print(f"[clip] indexed {min(start + INDEX_BATCH, len(paths))}/{len(paths)}", flush=True)

        matrix = _normalize(np.vstack(chunks)) if chunks else np.zeros((0, 0), dtype=np.float32)
        _save(ids, matrix)
        _ids = ids
        _matrix = matrix
        _set_state(ready=True)
        print(f"[clip] index ready: {len(ids)} images", flush=True)
    except Exception as exc:  # noqa: BLE001 - report any failure via /health
        _set_state(error=str(exc))
        print(f"[clip] index build failed: {exc}", flush=True)


def load_or_build() -> None:
    """Load the cached index if present, else kick off a background build."""
    global _ids, _matrix
    if os.path.exists(EMBEDDINGS_PATH):
        data = np.load(EMBEDDINGS_PATH, allow_pickle=True)
        _ids = list(data["ids"])
        _matrix = np.asarray(data["matrix"], dtype=np.float32)
        _set_state(ready=True, total=len(_ids), indexed=len(_ids))
        print(f"[clip] loaded cached index: {len(_ids)} images", flush=True)
        # Warm the text encoder so the first query isn't slow.
        threading.Thread(target=_get_model, daemon=True).start()
    else:
        threading.Thread(target=build, daemon=True).start()


def search(query: str, limit: int) -> list:
    """Return semantically matching images as [{id, score}], best first."""
    with _lock:
        ready = _state["ready"]
    if not ready:
        raise IndexNotReady()

    count = len(_ids)
    if count == 0:
        return []

    model = _get_model()
    vector = _encode_text(model, query)

    scores = _matrix @ vector
    selected = _select_meaningful(scores, limit)
    return [{"id": _ids[i], "score": float(scores[i])} for i in selected]
