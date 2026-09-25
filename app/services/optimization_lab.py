"""
Optimization Lab: benchmarks vector quantization presets (Qdrant TurboQuant /
scalar int8) against exact search on a sample of a workspace's real vectors.

For each preset a temporary collection is seeded, queried, measured, and
dropped. Ground truth comes from exact search on an unquantized copy.
"""
import json
import time
import uuid

import logfire
from qdrant_client.http import models as qmodels

from app.config import settings
from app.db.database import SessionLocal
from app.db.models import Experiment, Workspace
from app.services.retrieval.qdrant_service import (
    PRESET_BITS,
    build_quantization_config,
    client as qdrant_client,
    scroll_sample_vectors,
)

DEFAULT_PRESETS = ["scalar_int8", "turbo_b4", "turbo_b2", "turbo_b1_5", "turbo_b1"]
K = 5  # recall@k


def _bench_queries(vectors: list[list[float]]) -> list[list[float]]:
    """
    Benchmark queries: a few vectors from the corpus itself act as queries
    (self-retrieval — the closest thing to real user queries without an LLM).
    Deterministically spread over the sample.
    """
    if not vectors:
        return []
    count = min(settings.BENCH_QUERY_COUNT, len(vectors))
    step = max(1, len(vectors) // count)
    return vectors[::step][:count]


def _exact_top_k(collection: str, query: list[float], k: int) -> set[str]:
    res = qdrant_client.query_points(
        collection_name=collection,
        query=query,
        limit=k,
        search_params=qmodels.SearchParams(exact=True),
    )
    return {p.id for p in res.points}


def _approx_top_k(collection: str, query: list[float], k: int) -> tuple[set[str], float]:
    start = time.perf_counter()
    res = qdrant_client.query_points(
        collection_name=collection,
        query=query,
        limit=k,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {p.id for p in res.points}, elapsed_ms


def _estimate_memory_saved(preset: str) -> float:
    """Theoretical vector-memory saving vs fp32 (32 bits/dim)."""
    return round((1 - PRESET_BITS[preset] / 32) * 100, 1)


def run_experiment(experiment_id: str, presets: list[str]) -> None:
    """Background task: benchmarks quantization presets and stores results."""
    db = SessionLocal()
    try:
        exp = db.get(Experiment, experiment_id)
        if exp is None:
            return
        ws = db.get(Workspace, exp.workspace_id)
        if ws is None:
            exp.status = "failed"
            exp.error = "Workspace no longer exists."
            db.commit()
            return

        try:
            results = _benchmark(ws, presets)
            exp.results_json = json.dumps(results, ensure_ascii=False)
            exp.status = "done"
        except Exception as e:
            logfire.error(f"Optimization experiment failed: {e}")
            exp.status = "failed"
            exp.error = str(e)[:1000]
        db.commit()
    finally:
        db.close()


def _benchmark(ws: Workspace, presets: list[str]) -> dict:
    vectors = scroll_sample_vectors(ws.qdrant_collection, settings.BENCH_SAMPLE_SIZE)
    if len(vectors) < 20:
        raise RuntimeError(
            f"Not enough vectors in the workspace ({len(vectors)}). Upload more documents first."
        )

    dim = len(vectors[0])
    queries = _bench_queries(vectors)
    bench_id = uuid.uuid4().hex[:8]

    def temp_name(preset: str) -> str:
        return f"bench_{ws.id[:8]}_{preset}_{bench_id}"

    # Ground-truth collection (no quantization)
    plain = temp_name("plain")
    _seed_collection(plain, vectors, None)

    try:
        ground_truth = [_exact_top_k(plain, q, K) for q in queries]
        results = []
        for preset in presets:
            results.append(
                _bench_preset(temp_name(preset), vectors, preset, queries, ground_truth)
            )
    finally:
        _drop(plain)
        for preset in presets:  # clean up any preset collection that errored mid-run
            _drop(temp_name(preset))

    return {
        "bench": {"vectors": len(vectors), "queries": len(queries), "dim": dim, "k": K},
        "results": results,
    }


def _seed_collection(name: str, vectors: list[list[float]], quantization_config) -> None:
    if qdrant_client.collection_exists(name):
        qdrant_client.delete_collection(name)
    qdrant_client.create_collection(
        collection_name=name,
        vectors_config=qmodels.VectorParams(
            size=len(vectors[0]), distance=qmodels.Distance.COSINE
        ),
        quantization_config=quantization_config,
    )
    points = [
        # Deterministic ids: the same vector must carry the same id in every
        # seeded collection, otherwise approximate sets can never match the
        # exact-search ground truth
        qmodels.PointStruct(id=f"pt_{i}", vector=v, payload={})
        for i, v in enumerate(vectors)
    ]
    qdrant_client.upsert(collection_name=name, points=points)
    # Wait until indexing finishes so benchmarks measure the real thing
    for _ in range(60):
        status = qdrant_client.get_collection(name).status
        if status == qmodels.CollectionStatus.GREEN:
            break
        time.sleep(1)


def _bench_preset(name: str, vectors: list[list[float]], preset: str, queries, ground_truth) -> dict:
    result = {
        "preset": preset,
        "recall_at_5": None,
        "latency_p50_ms": None,
        "latency_p95_ms": None,
        "memory_saved_pct": _estimate_memory_saved(preset),
        "status": "ok",
        "note": "",
    }
    try:
        config = build_quantization_config(preset)
        _seed_collection(name, vectors, config)
    except Exception as e:
        result["status"] = "unsupported"
        result["note"] = f"Cluster rejected this preset: {str(e)[:200]}"
        return result

    try:
        recalls, latencies = [], []
        for query, truth in zip(queries, ground_truth):
            approx, elapsed_ms = _approx_top_k(name, query, K)
            recalls.append(len(approx & truth) / K)
            latencies.append(elapsed_ms)
        recalls.sort()
        latencies.sort()

        def pct(values, p):
            idx = min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))
            return values[idx]

        result["recall_at_5"] = round(sum(recalls) / len(recalls), 4)
        result["latency_p50_ms"] = round(pct(latencies, 50), 2)
        result["latency_p95_ms"] = round(pct(latencies, 95), 2)
    except Exception as e:
        result["status"] = "failed"
        result["note"] = str(e)[:200]
    finally:
        _drop(name)
    return result


def _drop(name: str) -> None:
    try:
        if qdrant_client.collection_exists(name):
            qdrant_client.delete_collection(name)
    except Exception as e:
        logfire.warning(f"Benchmark cleanup failed for {name}: {e}")
