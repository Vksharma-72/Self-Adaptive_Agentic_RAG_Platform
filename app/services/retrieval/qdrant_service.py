import logfire
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.config import settings
from app.services.retrieval.embeddings import embed_query


# Initialize Qdrant Client
client = QdrantClient(
    url= settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)

def search_workspace(query: str, collection: str, limit: int = 8):
    """
    Performs a high-precision semantic search in one workspace's collection.
    Uses the modern query_points interface.
    """
    try:
        query_vector = embed_query(query)

        # Using query_points - the modern standard for Qdrant
        response = client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=limit,
            with_payload=True # JSON
        )

        results = []
        for res in response.points:
            results.append({
                "content": res.payload.get("text", " "),
                "source" : res.payload.get("source", "Unknown"),
                "document_id" : res.payload.get("document_id", ""),
                "score" : res.score
            })

        return results
    except Exception as e:
        logfire.error(f"Qdrant Search Failed: {e}")
        return []


# Backwards-compatible alias for the legacy single-collection setup (evals/CLI)
def search_enterprise_knowledge(query: str, limit: int = 8):
    return search_workspace(query, settings.QDRANT_COLLECTION, limit=limit)


def delete_document_points(collection: str, document_id: str) -> int:
    """Removes all points belonging to a document. Returns number deleted (best effort)."""
    try:
        client.delete(
            collection_name=collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )]
                )
            ),
        )
        return 1
    except Exception as e:
        logfire.error(f"Failed to delete points for document {document_id}: {e}")
        return 0


def drop_collection(collection: str) -> bool:
    """Drops an entire workspace collection. Returns True if it existed."""
    try:
        if client.collection_exists(collection):
            client.delete_collection(collection)
            logfire.info(f"Dropped Qdrant collection '{collection}'.")
            return True
    except Exception as e:
        logfire.error(f"Failed to drop collection {collection}: {e}")
    return False


def ensure_collection(collection: str, quantization_config=None) -> None:
    """Creates the collection with the runtime-resolved embedding dim if missing."""
    if not client.collection_exists(collection):
        dim = None
        try:
            from app.services.retrieval.embeddings import get_embedding_dim
            dim = get_embedding_dim()
        except Exception as e:
            logfire.warning(f"Dim probe failed ({e}); defaulting to 3072.")
            dim = 3072
        kwargs = dict(
            collection_name=collection,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )
        if quantization_config is not None:
            kwargs["quantization_config"] = quantization_config
        client.create_collection(**kwargs)
        logfire.info(f"Created collection '{collection}' ({dim}-dim, Cosine).")


# --- Optimization Lab helpers -------------------------------------------

# Preset name → Qdrant quantization config
def build_quantization_config(preset: str):
    """Maps a preset name to a Qdrant quantization config. None = plain."""
    presets = {
        "scalar_int8": models.ScalarQuantization(
            scalar=models.ScalarQuantizationConfig(type=models.ScalarType.INT8, quantile=0.99, always_ram=True)
        ),
        "turbo_b4": _turbo(models.TurboQuantBitSize.BITS4),
        "turbo_b2": _turbo(models.TurboQuantBitSize.BITS2),
        "turbo_b1_5": _turbo(models.TurboQuantBitSize.BITS1_5),
        "turbo_b1": _turbo(models.TurboQuantBitSize.BITS1),
    }
    if preset not in presets:
        raise ValueError(f"Unknown quantization preset: {preset}")
    return presets[preset]


def _turbo(bits):
    return models.TurboQuantization(
        turbo=models.TurboQuantQuantizationConfig(
            memory=models.Memory.PINNED, bits=bits
        )
    )


# bits-per-dimension per preset, used for memory-savings estimates (fp32 = 32)
PRESET_BITS = {"scalar_int8": 8, "turbo_b4": 4, "turbo_b2": 2, "turbo_b1_5": 1.5, "turbo_b1": 1}


def get_collection_quantization(collection: str) -> str | None:
    """Returns the applied preset name (best-effort) from collection info."""
    try:
        info = client.get_collection(collection)
        qc = info.config.quantization_config
        if qc is None:
            return None
        qc = qc.model_dump() if hasattr(qc, "model_dump") else qc
        if qc.get("turbo"):
            bits = qc["turbo"].get("bits")
            return {"bits4": "turbo_b4", "bits2": "turbo_b2", "bits1_5": "turbo_b1_5", "bits1": "turbo_b1"}.get(bits, "turbo")
        if qc.get("scalar"):
            return "scalar_int8"
        return "custom"
    except Exception as e:
        logfire.warning(f"Could not read quantization config for {collection}: {e}")
        return None


def apply_quantization(collection: str, preset: str) -> bool:
    """Applies a quantization preset to an existing collection (Qdrant re-indexes)."""
    config = build_quantization_config(preset)
    client.update_collection(collection_name=collection, quantization_config=config)
    logfire.info(f"Applied quantization preset '{preset}' to '{collection}'.")
    return True


def scroll_sample_vectors(collection: str, limit: int) -> list[list[float]]:
    """Samples real vectors (with payloads) from a collection for benchmarking."""
    if not client.collection_exists(collection):
        return []
    points, _ = client.scroll(
        collection_name=collection,
        limit=limit,
        with_payload=False,
        with_vectors=True,
    )
    return [p.vector for p in points]
