"""Embedding and retrieval layer for the payments support assistant.

Loads policy documents from the data/policies/ directory, embeds them with
Voyage AI voyage-3-lite, stores vectors in memory as numpy arrays, and
provides cosine-similarity search returning top-k results with scores.
"""

import os
import glob

import numpy as np
import voyageai
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(__file__)
POLICIES_DIR = os.path.join(BASE_DIR, "data", "policies")
EMBED_MODEL = "voyage-3-lite"
TOP_K = 3

# Load VOYAGE_API_KEY from the repo-root .env
load_dotenv(os.path.join(BASE_DIR, os.pardir, ".env"))

# ---------------------------------------------------------------------------
# In-memory vector store
# ---------------------------------------------------------------------------

_corpus: list[dict] = []
_voyage_client: voyageai.Client | None = None


def _get_client() -> voyageai.Client:
    global _voyage_client
    if _voyage_client is None:
        api_key = os.environ.get("VOYAGE_API_KEY")
        if not api_key:
            raise RuntimeError("VOYAGE_API_KEY is not set. Add it to .env or export it.")
        _voyage_client = voyageai.Client(api_key=api_key)
    return _voyage_client


def load_corpus() -> list[dict]:
    """Load and embed all policy .md files (skipping README). Idempotent."""
    if _corpus:
        return _corpus

    md_files = sorted(glob.glob(os.path.join(POLICIES_DIR, "*.md")))
    docs = []
    texts = []
    for path in md_files:
        name = os.path.basename(path)
        if name == "README.md":
            continue
        with open(path) as f:
            text = f.read()
        docs.append({"filename": name, "text": text})
        texts.append(text)

    if not texts:
        return _corpus

    client = _get_client()
    result = client.embed(texts, model=EMBED_MODEL, input_type="document")

    for doc, emb in zip(docs, result.embeddings):
        doc["embedding"] = np.array(emb, dtype=np.float32)
        _corpus.append(doc)

    return _corpus


def search(query: str, top_k: int = TOP_K) -> list[dict]:
    """Semantic search over the policy corpus.

    Returns the top_k documents ranked by cosine similarity, each with
    keys: filename, score, text.
    """
    load_corpus()
    if not _corpus:
        return []

    client = _get_client()
    result = client.embed([query], model=EMBED_MODEL, input_type="query")
    q_vec = np.array(result.embeddings[0], dtype=np.float32)

    scored = []
    for doc in _corpus:
        d_vec = doc["embedding"]
        cos_sim = float(
            np.dot(q_vec, d_vec) / (np.linalg.norm(q_vec) * np.linalg.norm(d_vec) + 1e-10)
        )
        scored.append((cos_sim, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"filename": doc["filename"], "score": round(score, 4), "text": doc["text"]}
        for score, doc in scored[:top_k]
    ]
