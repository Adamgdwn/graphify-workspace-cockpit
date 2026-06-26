from __future__ import annotations

from collections import OrderedDict

import pytest

from backend import main


@pytest.fixture(autouse=True)
def _isolate_embed_cache(monkeypatch):
    """Give each test a fresh, small embedding cache so eviction is testable."""
    monkeypatch.setattr(main, "_EMBED_CACHE", OrderedDict())
    monkeypatch.setattr(main, "_EMBED_CACHE_MAX", 4)


def _counting_embedder(monkeypatch):
    """Replace the Ollama embed call with a deterministic, call-counting stub."""
    calls: list[list[str]] = []

    def fake_embed(model: str, texts: list[str], ollama_base: str) -> list[list[float]]:
        calls.append(list(texts))
        return [[float(len(t))] for t in texts]

    monkeypatch.setattr(main, "_embed_text_batch_ollama", fake_embed)
    return calls


def test_repeated_texts_reuse_cache_and_skip_ollama(monkeypatch):
    calls = _counting_embedder(monkeypatch)

    vectors, misses = main._embed_texts_cached("nomic", ["a", "bb", "ccc"], "")
    assert vectors == [[1.0], [2.0], [3.0]]
    assert misses == 3
    assert calls == [["a", "bb", "ccc"]]

    # Same texts again: every vector served from cache, no further Ollama calls.
    vectors2, misses2 = main._embed_texts_cached("nomic", ["a", "bb", "ccc"], "")
    assert vectors2 == [[1.0], [2.0], [3.0]]
    assert misses2 == 0
    assert len(calls) == 1


def test_only_cache_misses_are_embedded(monkeypatch):
    calls = _counting_embedder(monkeypatch)

    main._embed_texts_cached("nomic", ["a", "bb"], "")
    vectors, misses = main._embed_texts_cached("nomic", ["a", "dddd"], "")

    assert vectors == [[1.0], [4.0]]
    assert misses == 1
    assert calls[-1] == ["dddd"]  # "a" reused, only the new text embedded


def test_cache_is_keyed_by_model(monkeypatch):
    _counting_embedder(monkeypatch)

    main._embed_texts_cached("nomic", ["a"], "")
    _vectors, misses = main._embed_texts_cached("other-model", ["a"], "")

    assert misses == 1  # same text, different model => recomputed


def test_empty_vectors_are_not_cached(monkeypatch):
    def fake_embed(model, texts, ollama_base):
        return [[] for _ in texts]  # Ollama failed for every text

    monkeypatch.setattr(main, "_embed_text_batch_ollama", fake_embed)

    main._embed_texts_cached("nomic", ["a"], "")
    assert main._embed_cache_key("nomic", "a") not in main._EMBED_CACHE


def test_cache_respects_size_cap(monkeypatch):
    _counting_embedder(monkeypatch)

    main._embed_texts_cached("nomic", [str(i) for i in range(10)], "")
    assert len(main._EMBED_CACHE) <= main._EMBED_CACHE_MAX


def test_cache_persists_to_disk_and_reloads(tmp_path, monkeypatch):
    cache_file = tmp_path / "embedding-cache.json"
    monkeypatch.setattr(main, "EMBED_CACHE_FILE", cache_file)

    main._embed_cache_store("nomic", "hello", [1.0, 2.0])
    main._embed_cache_save()
    assert cache_file.exists()

    # A fresh process starts with an empty cache, then warms from disk.
    monkeypatch.setattr(main, "_EMBED_CACHE", OrderedDict())
    main._embed_cache_load()
    assert main._EMBED_CACHE.get(main._embed_cache_key("nomic", "hello")) == [1.0, 2.0]


def test_cache_load_tolerates_missing_or_corrupt_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "EMBED_CACHE_FILE", tmp_path / "does-not-exist.json")
    main._embed_cache_load()  # missing file is a silent no-op

    corrupt = tmp_path / "embedding-cache.json"
    corrupt.write_text("{ not valid json")
    monkeypatch.setattr(main, "EMBED_CACHE_FILE", corrupt)
    main._embed_cache_load()  # corrupt file must not raise
    assert len(main._EMBED_CACHE) == 0


def test_disk_warm_start_skips_ollama(tmp_path, monkeypatch):
    """A warmed cache means the first pass after restart makes no Ollama calls."""
    cache_file = tmp_path / "embedding-cache.json"
    monkeypatch.setattr(main, "EMBED_CACHE_FILE", cache_file)

    calls = _counting_embedder(monkeypatch)
    main._embed_texts_cached("nomic", ["a", "bb"], "")
    main._embed_cache_save()
    assert len(calls) == 1

    # Simulate a restart: empty in-memory cache, reload from disk, re-embed.
    monkeypatch.setattr(main, "_EMBED_CACHE", OrderedDict())
    main._embed_cache_load()
    _vectors, misses = main._embed_texts_cached("nomic", ["a", "bb"], "")
    assert misses == 0
    assert len(calls) == 1  # no new Ollama call after the warm start
