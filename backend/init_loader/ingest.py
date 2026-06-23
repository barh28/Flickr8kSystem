"""Idempotent ingestion of the Flickr8k dataset into the files service DB.

Runs once as an init container, then exits. It downloads the dataset's parquet
shards from HuggingFace, writes each image once to the shared images volume, and
inserts the metadata (with derived fields) through the *files service's own data
layer* so the schema and derivations stay defined in a single place.

Re-runs are safe:
  * a marker file short-circuits an already-completed load,
  * image files are only written if missing,
  * rows are inserted with INSERT OR REPLACE (see files db_operations).
"""
import hashlib
import io
import os
import sys

# Make shared_libraries (backend root) and the files service's `src` package
# importable, so we reuse files' config / db / derive instead of duplicating.
_SERVICE_ROOT = os.path.dirname(os.path.abspath(__file__))   # /app/init_loader
_BACKEND_ROOT = os.path.dirname(_SERVICE_ROOT)               # /app
_FILES_ROOT = os.path.join(_BACKEND_ROOT, "files_manager")   # /app/files_manager
for _path in (_BACKEND_ROOT, _FILES_ROOT, _SERVICE_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import httpx
import pyarrow.parquet as pq
from PIL import Image

from shared_libraries.env import get_env, get_env_int
from src.config import DATA_DIR, DEFAULT_DATASET, IMAGES_DIR
from src.db.connection import init_db
from src.services import files_manager

# Auto-converted parquet copies served by the HF datasets-server.
PARQUET_BASE = get_env(
    "FLICKR8K_PARQUET_BASE",
    "https://huggingface.co/datasets/jxie/flickr8k/resolve/refs%2Fconvert%2Fparquet/default",
)
# split -> number of parquet shards published for that split.
SPLIT_SHARDS = {"train": 2, "validation": 1, "test": 1}

CAPTION_COLUMNS = ("caption_0", "caption_1", "caption_2", "caption_3", "caption_4")
BATCH_SIZE = get_env_int("INGEST_BATCH_SIZE", 128)
# Optional cap per split for quick local runs (0 = ingest everything).
MAX_PER_SPLIT = get_env_int("INGEST_MAX_PER_SPLIT", 0)

MARKER_PATH = os.path.join(DATA_DIR, ".ingest_done")
_FORMAT_EXT = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "BMP": "bmp", "WEBP": "webp"}


def _download(url: str, dest: str) -> None:
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"  cached {os.path.basename(dest)}", flush=True)
        return
    print(f"  downloading {url}", flush=True)
    tmp = dest + ".part"
    with httpx.stream("GET", url, timeout=None, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(tmp, "wb") as handle:
            for chunk in resp.iter_bytes(chunk_size=1 << 20):
                handle.write(chunk)
    os.replace(tmp, dest)


def _captions(row: dict) -> list:
    result = []
    for column in CAPTION_COLUMNS:
        value = row.get(column)
        if value is not None and value != "":
            result.append(value)
    return result


def _store_image(data: bytes) -> tuple:
    """Write image bytes once (named by content hash); return (id, path, w, h)."""
    digest = hashlib.md5(data).hexdigest()
    with Image.open(io.BytesIO(data)) as img:
        width, height = img.size
        ext = _FORMAT_EXT.get(img.format or "JPEG", "jpg")
    file_id = f"{digest}.{ext}"
    path = os.path.join(IMAGES_DIR, file_id)
    if not os.path.exists(path):
        tmp = path + ".part"
        with open(tmp, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    return file_id, path, width, height


def _ingest_parquet(path: str, split: str, seen: set) -> int:
    added = 0
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(batch_size=BATCH_SIZE,
                                      columns=["image", *CAPTION_COLUMNS]):
        for row in batch.to_pylist():
            if MAX_PER_SPLIT and added >= MAX_PER_SPLIT:
                return added
            image = row.get("image") or {}
            data = image.get("bytes")
            if not data:
                continue
            file_id, image_path, width, height = _store_image(data)
            if file_id in seen:
                continue
            seen.add(file_id)
            files_manager.add_file(
                file_id=file_id,
                split=split,
                width=width,
                height=height,
                captions=_captions(row),
                image_path=image_path,
                dataset=DEFAULT_DATASET,
            )
            added += 1
    return added


def main() -> None:
    if os.path.exists(MARKER_PATH):
        print(f"Ingestion already complete (marker {MARKER_PATH}); skipping.", flush=True)
        return

    os.makedirs(IMAGES_DIR, exist_ok=True)
    init_db()

    cache_dir = os.path.join(DATA_DIR, ".parquet_cache")
    os.makedirs(cache_dir, exist_ok=True)

    total = 0
    seen: set = set()
    for split, shards in SPLIT_SHARDS.items():
        print(f"[{split}] {shards} shard(s)", flush=True)
        for shard in range(shards):
            name = f"{shard:04d}.parquet"
            url = f"{PARQUET_BASE}/{split}/{name}"
            local = os.path.join(cache_dir, f"{split}_{name}")
            _download(url, local)
            count = _ingest_parquet(local, split, seen)
            total += count
            print(f"  {split} shard {shard}: +{count} (running total {total})", flush=True)
            os.remove(local)

    with open(MARKER_PATH, "w") as handle:
        handle.write("done\n")
    print(f"Ingestion complete: {total} samples loaded.", flush=True)


if __name__ == "__main__":
    main()
