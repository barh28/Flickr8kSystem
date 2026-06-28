# Flickr8k Explorer

A web tool for Computer-Vision researchers to **browse, search, filter, tag, and export** the
[Flickr8k](https://huggingface.co/datasets/jxie/flickr8k) image-captioning dataset, so they can
judge data quality, explore concepts, and analyze model failures before/after training.

The system is a small set of **FastAPI microservices** behind a single **API Gateway**, a
**React** frontend, and a one-shot **init** job that loads the dataset. Everything runs with a
single `docker compose up`.

---

## Architecture at a glance

```
                       ┌────────────────────────────────────────────┐
  Browser  ──────────► │  gateway  (:8080)                          │
  (React frontend)     │  • /api/{service}/{action}  generic proxy  │
        ▲              │  • /images/*  static image files           │
        │              └───┬─────────┬─────────┬─────────┬─────────┘
        │                  │         │         │         │
        │          ┌───────▼──┐ ┌────▼────┐ ┌──▼─────┐ ┌▼──────────┐
   frontend (:5173)│  users   │ │  files  │ │  tags  │ │   clip    │
                   │ (:8000)  │ │ (:8000) │ │(:8000) │ │  (:8000)  │
                   └────┬─────┘ └────┬────┘ └──┬──┬──┘ └─────┬─────┘
                        │              │         │  │          │
                    users.db       files.db   tags.db │      embeddings
                                                      └──────────┘
                                              (direct calls: users + files + clip)
                       ┌──────────────────────────────────────────────┐
                       │  init (runs once, then exits)                │
                       │  downloads Flickr8k → images/ + files.db     │
                       └──────────────────────────────────────────────┘
```

**Key principles**

- **Gateway is the only public entry point.** It is generic: a service registry maps a name to a
  URL, and the single route `/api/{service}/{action}` proxies to that service's `/{action}`.
  Adding a service later = one registry entry, no new routes.
- **Database-per-service.** Each service owns its own SQLite file (isolation, no cross-service
  locking).
- **Services call each other directly** (not through the gateway) using `*_SERVICE_URL` env vars.
- **Server-side filtering & pagination** over the whole dataset (the client never holds everything).
- **Shared code** lives in `backend/shared_libraries/` and is copied into each image.

---

## Services & scope

| Service    | Port  | Public? | Scope / responsibility |
|------------|-------|---------|------------------------|
| `gateway`  | 8080  | ✅ yes  | Single entry point. Generic reverse proxy to all services + serves image files statically. Handles CORS. |
| `frontend` | 5173  | ✅ yes  | React UI: gallery, keyword + **meaning (CLIP) search**, filters, image detail view, tagging (pass/fail), labels, bulk tagging, export, statistics. Talks only to the gateway. |
| `users`    | 8000  | internal| Lightweight registration: username + password, where only a salted password **hash** is stored (never the plaintext). Returns a stable user id used for tagging. |
| `files`    | 8000  | internal| Dataset metadata: captions + derived fields (caption length, orientation, annotator agreement). Rich filtering, full-text search (FTS5), sorting, pagination. Read-only over HTTP. |
| `tags`     | 8000  | internal| Per-user tagging (pass/fail) + free-form labels. Orchestrates the gallery (`/query` = files + the user's tags), meaning search (via `clip`), and exports. |
| `clip`     | 8000  | internal| **Semantic search**: embeds every image once with open-source CLIP (`clip-ViT-B-32`), caches vectors locally, ranks images by cosine similarity to a text query. Called directly by `tags` (not by the browser). |
| `init`     | —     | one-shot| Downloads Flickr8k parquet shards, writes each image once to the images volume, and fills `files.db` through the files data layer. Idempotent; exits 0 when done. |

### Endpoints (reached via the gateway as `/api/{service}/{action}`)

| Service | Action | Method | Purpose |
|---------|--------|--------|---------|
| users   | `/health` | GET | Liveness |
| users   | `/create` | POST | Register with `{username, password}` (password stored hashed); returns a **token**, or `400` if the username already exists. **Public** (no token needed) |
| users   | `/login`  | POST | Authenticate `{username, password}` → **token** (`401` on mismatch). **Public** (no token needed) |
| users   | `/get`    | GET (`?id=`) | Fetch a user — only your **own** record (the requested `id` must match the token's user; otherwise `403`) |
| files   | `/health` | GET | Liveness |
| files   | `/list`   | GET | Filter/search/sort/paginate files (`q, dataset, split, length, orientation, agreement, sort, page, page_size, ids`) |
| files   | `/get`    | GET (`?id=`) | One file with all metadata |
| files   | `/options`| GET | Available filter values (datasets, splits, orientations, caption-length bounds) |
| tags    | `/health` | GET | Liveness |
| tags    | `/set`    | POST | Tag files as `passed`/`failed` (user taken from the token, not the body) |
| tags    | `/remove` | POST | Remove the user's tags |
| tags    | `/query`  | GET | Gallery for the current user: files + their tag status (same filters as files `/list`, plus `status`, `labels`, and `search_mode=meaning` for CLIP semantic search) |
| tags    | `/export` | GET (`?format=csv\|json`) | Download the current user's tagged subset |
| tags    | `/export_filtered` | GET | Export all files matching filters (supports `search_mode=meaning`) |
| clip    | `/health` | GET | Liveness + index build progress (`ready`, `indexed`, `total`) |
| clip    | `/search` | GET (`?q=&limit=`) | Rank images by semantic similarity to a text query (internal; called by `tags`) |
| gateway | `/health` | GET | Liveness + list of registered services |
| gateway | `/images/{file_id}` | GET | Static image bytes |

> Example: the frontend calls `GET http://localhost:8080/api/files/list?split=train&length=short`.

---

## Authentication (token-based, gateway-enforced)

A lightweight, **stateless** token (a mini-JWT) mimics a real auth flow without
sessions or a token store:

1. **Get a token** — `POST /api/users/create` (register) or `POST /api/users/login`
   returns `{user_id, username, token}`. The token is `base64(payload).HMAC_SHA256(payload, AUTH_SECRET)`
   where the payload holds `user_id`, `username`, and an expiry (`exp`).
2. **Use it** — the frontend sends `Authorization: Bearer <token>` on every call.
3. **Gateway enforces + identifies** — for any endpoint that isn't public
   (everything except `users/create` and `users/login`), the gateway verifies the
   token's signature/expiry. On success it **injects a trusted `X-User-Id`
   header** to the upstream service; on failure it returns `401`.
4. **Anti-spoofing** — the gateway always strips any client-supplied
   `Authorization` / `X-User-Id` / `X-Username` headers before proxying, so a
   client can never claim another user's id. Downstream services trust
   `X-User-Id` precisely because only the gateway can set it.
5. **Per-user isolation** — the `tags` service derives the user **only** from
   `X-User-Id`, so every tag read/write/export is scoped to the caller's own data.

> The signing secret (`AUTH_SECRET`) must be identical in the `users` and
> `gateway` services. In `docker-compose.yml` it is shared via a YAML anchor.

---

## Environment variables

All variables have sensible defaults (shown below); override them in `docker-compose.yml`.

### gateway
| Variable | Default | Meaning |
|----------|---------|---------|
| `GATEWAY_HOST` | `0.0.0.0` | Bind address |
| `GATEWAY_PORT` | `8080` | Public port |
| `DATA_DIR` | `/data` | Base dir (unused for DB here; kept for consistency) |
| `IMAGES_DIR` | `/images` | Folder served statically at `/images/*` |
| `USERS_SERVICE_URL` | `http://users:8000` | Registry entry for the users service |
| `FILES_SERVICE_URL` | `http://files:8000` | Registry entry for the files service |
| `TAGS_SERVICE_URL` | `http://tags:8000` | Registry entry for the tags service |
| `CLIP_SERVICE_URL` | `http://clip:8000` | Registry entry for the clip service |
| `PROXY_TIMEOUT` | `30` | Upstream request timeout (seconds) |
| `CORS_ORIGINS` | `*` | Allowed origins (comma-separated, or `*`) |
| `AUTH_SECRET` | `dev-insecure-secret-change-me` | HMAC secret for verifying tokens (**must match `users`**) |

### frontend
| Variable | Default | Meaning |
|----------|---------|---------|
| `VITE_API_BASE_URL` | `http://localhost:8080` | Gateway base URL the React app calls |

### users
| Variable | Default | Meaning |
|----------|---------|---------|
| `USER_SERVICE_HOST` | `0.0.0.0` | Bind address |
| `USER_SERVICE_PORT` | `8000` | Internal port |
| `DATA_DIR` | `/data` | Base data dir |
| `USER_DB_PATH` | `/data/users.db` | SQLite file path |
| `AUTH_SECRET` | `dev-insecure-secret-change-me` | HMAC secret for signing tokens (**must match `gateway`**) |
| `AUTH_TOKEN_TTL_SECONDS` | `86400` | Token lifetime in seconds |

### files
| Variable | Default | Meaning |
|----------|---------|---------|
| `FILES_SERVICE_HOST` | `0.0.0.0` | Bind address |
| `FILES_SERVICE_PORT` | `8000` | Internal port |
| `DATA_DIR` | `/data` | Base data dir |
| `FILES_DB_PATH` | `/data/files.db` | SQLite file path (shared with `init`) |
| `IMAGES_DIR` | `/images` | Image folder (read-only here) |
| `IMAGE_URL_PREFIX` | `/images` | Prefix used to build each file's `image_url` |
| `DEFAULT_DATASET` | `Flickr8k` | Dataset label stamped on rows |
| `FILES_DEFAULT_PAGE_SIZE` | `50` | Default page size |
| `FILES_MAX_PAGE_SIZE` | `200` | Max page size a client may request |
| `FILES_SHORT_MAX_WORDS` | `8` | Upper bound (words) for the "short" caption bucket |
| `FILES_MEDIUM_MAX_WORDS` | `14` | Upper bound (words) for the "medium" caption bucket |

### tags
| Variable | Default | Meaning |
|----------|---------|---------|
| `TAGS_SERVICE_HOST` | `0.0.0.0` | Bind address |
| `TAGS_SERVICE_PORT` | `8000` | Internal port |
| `DATA_DIR` | `/data` | Base data dir |
| `TAGS_DB_PATH` | `/data/tags.db` | SQLite file path |
| `USERS_SERVICE_URL` | `http://users:8000` | Direct call target (validate user) |
| `FILES_SERVICE_URL` | `http://files:8000` | Direct call target (fetch files for the gallery) |
| `CLIP_SERVICE_URL` | `http://clip:8000` | Direct call target (semantic search for meaning mode) |
| `CLIP_CANDIDATES` | `500` | Max semantic matches returned (actual count is decided by score threshold) |
| `PUBLIC_BASE_URL` | `http://localhost:8080` | Gateway URL used to build absolute image URLs in exports |
| `TAGS_DEFAULT_PAGE_SIZE` | `50` | Default page size |
| `TAGS_MAX_PAGE_SIZE` | `200` | Max page size |
| `FILES_PAGE_LIMIT` | `200` | Max ids per call to files `/list` |

### clip
| Variable | Default | Meaning |
|----------|---------|---------|
| `CLIP_SERVICE_HOST` | `0.0.0.0` | Bind address |
| `CLIP_SERVICE_PORT` | `8000` | Internal port |
| `DATA_DIR` | `/data` | Base data dir (holds cached embeddings) |
| `IMAGES_DIR` | `/images` | Image folder to embed (read-only) |
| `CLIP_EMBEDDINGS_PATH` | `/data/embeddings.npz` | Cached embedding matrix (built once, reused) |
| `CLIP_MODEL_NAME` | `clip-ViT-B-32` | Open-source CLIP model (baked into the image at build time) |
| `CLIP_TEXT_PROMPT` | `a photo of {query}` | Prompt template for text queries |
| `CLIP_MIN_SCORE` | `0.25` | Absolute cosine-similarity floor (semantic match, not relative to dataset size) |
| `CLIP_SCORE_GAP` | `0.012` | Stop at the first large score drop after the relevant cluster |
| `CLIP_INDEX_BATCH` | `32` | Images encoded per batch during index build |
| `CLIP_DEFAULT_LIMIT` | `500` | Default number of matches returned by `/search` |
| `CLIP_MAX_LIMIT` | `2000` | Max matches per `/search` request |

### init
| Variable | Default | Meaning |
|----------|---------|---------|
| `DATA_DIR` | `/data` | Base data dir (holds `files.db`, marker, parquet cache) |
| `FILES_DB_PATH` | `/data/files.db` | DB to fill (same as `files`) |
| `IMAGES_DIR` | `/images` | Where image files are written |
| `DEFAULT_DATASET` | `Flickr8k` | Dataset label |
| `FLICKR8K_PARQUET_BASE` | HF parquet URL | Base URL of the parquet shards |
| `INGEST_BATCH_SIZE` | `128` | Rows read per parquet batch |
| `INGEST_MAX_PER_SPLIT` | `0` | Cap rows per split for quick local runs (`0` = all) |

---

## Data & volumes

All persistent data is **bind-mounted into the project** under `./data/`, so it's easy to inspect
directly from the IDE/Finder:

| Host folder | Mounted as | Contents |
|-------------|------------|----------|
| `./data/images/` | `/images` | Image files, named `<md5>.jpg` |
| `./data/files/`  | `/data` (init + files) | `files.db`, ingest marker, temporary parquet cache |
| `./data/users/`  | `/data` (users) | `users.db` |
| `./data/tags/`   | `/data` (tags) | `tags.db` |
| `./data/clip/`   | `/data` (clip) | `embeddings.npz` (CLIP index cache) |

`init` and `files` share `./data/files` and `./data/images`; `files`, `gateway`, and `clip` mount images
read-only (`:ro`).

---

## Quick start

Requirements: **Docker** + **Docker Compose**.

```bash
# from the repo root
docker compose up --build
```

What happens:

1. `init` runs once — downloads Flickr8k, writes images to `./data/images`, fills `./data/files/files.db`,
   then exits (idempotent: a marker file skips an already-completed load).
2. `files` and `clip` start only after `init` **completes successfully**.
3. `users`, `tags`, the `gateway`, and the `frontend` come up.

Then open:

- **Frontend (the app):** http://localhost:5173
- **Gateway API:** http://localhost:8080  (e.g. health: http://localhost:8080/health)
- **An image:** http://localhost:8080/images/<file_id>

> **First run:** `init` downloads ~1&nbsp;GB of parquet (a few minutes). On its first boot,
> `clip` also embeds every image once on CPU (~5–15 minutes depending on hardware) and
> caches the result to `./data/clip/embeddings.npz`; later restarts load instantly.
> While the CLIP index is building, meaning search shows a "building index" message and
> retries automatically. Keyword search works immediately.

For a fast partial load during development, set `INGEST_MAX_PER_SPLIT` (e.g. `50`) on the `init` service.

Run in the background:

```bash
docker compose up --build -d
docker compose logs -f init     # watch ingestion progress
docker compose ps               # see service status
```

### Resetting

```bash
docker compose down          # stop & remove containers + network
rm -rf ./data                # drop all local data → next 'up' re-ingests from scratch
```

---

## Repository layout

```
.
├── docker-compose.yml          # one-command stack (incl. frontend)
├── data/                       # bind-mounted runtime data (gitignored)
├── frontend/                   # React app (talks to the gateway)
└── backend/
    ├── shared_libraries/       # env, error responses, http client (copied into images)
    ├── api_gateway/            # gateway service
    ├── user_manager/           # users service
    ├── files_manager/          # files service (schema + derived fields live here)
    ├── tags_manager/           # tags service (orchestrates gallery + meaning search)
    ├── clip_search/            # CLIP semantic search (embeddings + /search)
    └── init_loader/            # one-shot ingestion job (reuses files' data layer)
```
