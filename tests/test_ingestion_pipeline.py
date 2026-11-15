"""Tests for ingestion orchestration without loading models or writing indexes."""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

import config
from ingestion import pipeline


@pytest.fixture
def ingestion_components(monkeypatch):
    pages = [object()]
    chunks = [SimpleNamespace(text="A habit starts with a cue.", chunk_id="abc")]
    vector_store = Mock()
    vector_store.count.return_value = 0
    embedding_engine = Mock()
    embedding_engine.embed_texts.return_value = [[0.1, 0.2]]
    bm25_index = Mock()

    for module_name, class_name, instance in (
        ("core.vector_store", "VectorStore", vector_store),
        ("core.embeddings", "EmbeddingEngine", embedding_engine),
        ("core.bm25_index", "BM25Index", bm25_index),
    ):
        module = ModuleType(module_name)
        setattr(module, class_name, Mock(return_value=instance))
        monkeypatch.setitem(sys.modules, module_name, module)

    extract_pages = Mock(return_value=pages)
    chunk_pages = Mock(return_value=chunks)
    save_chunks_json = Mock()
    monkeypatch.setattr(pipeline, "extract_pages", extract_pages)
    monkeypatch.setattr(pipeline, "chunk_pages", chunk_pages)
    monkeypatch.setattr(pipeline, "_save_chunks_json", save_chunks_json)

    return SimpleNamespace(
        pages=pages,
        chunks=chunks,
        vector_store=vector_store,
        embedding_engine=embedding_engine,
        bm25_index=bm25_index,
        extract_pages=extract_pages,
        chunk_pages=chunk_pages,
        save_chunks_json=save_chunks_json,
    )


def test_ingestion_wires_all_stages(ingestion_components):
    components = ingestion_components

    pipeline.run_ingestion()

    components.extract_pages.assert_called_once_with()
    components.chunk_pages.assert_called_once_with(components.pages)
    components.embedding_engine.embed_texts.assert_called_once_with(
        [components.chunks[0].text]
    )
    components.vector_store.add_chunks.assert_called_once_with(
        components.chunks, [[0.1, 0.2]]
    )
    components.bm25_index.build.assert_called_once_with(components.chunks)
    components.bm25_index.save.assert_called_once_with(config.BM25_INDEX_PATH)
    components.save_chunks_json.assert_called_once_with(components.chunks)
    components.vector_store.reset.assert_not_called()


def test_tiny_habits_uses_its_own_pdf_and_index(ingestion_components):
    components = ingestion_components

    pipeline.run_ingestion(book="tiny_habits")

    components.extract_pages.assert_called_once_with(config.TINY_HABITS_PDF_PATH)
    components.chunk_pages.assert_called_once_with(components.pages, book="tiny_habits")
    components.bm25_index.save.assert_called_once_with(config.book_bm25_path("tiny_habits"))
    components.save_chunks_json.assert_called_once_with(components.chunks, book="tiny_habits")


def test_power_of_habit_uses_prepared_book_and_separate_index(ingestion_components, monkeypatch):
    from ingestion import power_of_habit

    components = ingestion_components
    prepared = [object()]
    prepare = Mock(return_value=prepared)
    monkeypatch.setattr(power_of_habit, "prepare_power_of_habit", prepare)

    pipeline.run_ingestion(book="power_of_habit")

    components.extract_pages.assert_called_once_with(config.POWER_OF_HABIT_PDF_PATH)
    prepare.assert_called_once_with(components.pages)
    components.chunk_pages.assert_called_once_with(prepared, book="power_of_habit")
    components.bm25_index.save.assert_called_once_with(config.book_bm25_path("power_of_habit"))


def test_power_of_now_uses_prepared_book_and_separate_index(ingestion_components, monkeypatch):
    from ingestion import power_of_now

    components = ingestion_components
    prepared = [object()]
    prepare = Mock(return_value=prepared)
    monkeypatch.setattr(power_of_now, "prepare_power_of_now", prepare)

    pipeline.run_ingestion(book="power_of_now")

    components.extract_pages.assert_called_once_with(config.POWER_OF_NOW_PDF_PATH)
    prepare.assert_called_once_with(components.pages)
    components.chunk_pages.assert_called_once_with(prepared, book="power_of_now")
    components.bm25_index.save.assert_called_once_with(config.book_bm25_path("power_of_now"))


def test_stoicism_uses_prepared_book_and_separate_index(ingestion_components, monkeypatch):
    from ingestion import stoicism

    components = ingestion_components
    prepared = [object()]
    prepare = Mock(return_value=prepared)
    monkeypatch.setattr(stoicism, "prepare_stoicism", prepare)

    pipeline.run_ingestion(book="little_book_of_stoicism")

    components.extract_pages.assert_called_once_with(config.STOICISM_PDF_PATH)
    prepare.assert_called_once_with(components.pages)
    components.chunk_pages.assert_called_once_with(prepared, book="little_book_of_stoicism")
    components.bm25_index.save.assert_called_once_with(
        config.book_bm25_path("little_book_of_stoicism"))


def test_five_second_rule_uses_prepared_book_and_separate_index(ingestion_components, monkeypatch):
    from ingestion import five_second_rule

    components = ingestion_components
    prepared = [object()]
    prepare = Mock(return_value=prepared)
    monkeypatch.setattr(five_second_rule, "prepare_five_second_rule", prepare)

    pipeline.run_ingestion(book="five_second_rule")

    components.extract_pages.assert_called_once_with(config.FIVE_SECOND_RULE_PDF_PATH)
    prepare.assert_called_once_with(components.pages)
    components.chunk_pages.assert_called_once_with(prepared, book="five_second_rule")
    components.bm25_index.save.assert_called_once_with(config.book_bm25_path("five_second_rule"))


def test_emotional_intelligence_uses_prepared_book_and_separate_index(ingestion_components, monkeypatch):
    from ingestion import emotional_intelligence

    components = ingestion_components
    prepared = [object()]
    prepare = Mock(return_value=prepared)
    monkeypatch.setattr(emotional_intelligence, "prepare_emotional_intelligence", prepare)

    pipeline.run_ingestion(book="emotional_intelligence")

    components.extract_pages.assert_called_once_with(config.EMOTIONAL_INTELLIGENCE_PDF_PATH)
    prepare.assert_called_once_with(components.pages)
    components.chunk_pages.assert_called_once_with(prepared, book="emotional_intelligence")
    components.bm25_index.save.assert_called_once_with(config.book_bm25_path("emotional_intelligence"))


def test_art_of_thinking_clearly_uses_prepared_book_and_separate_index(ingestion_components, monkeypatch):
    from ingestion import art_of_thinking_clearly

    components = ingestion_components
    prepared = [object()]
    prepare = Mock(return_value=prepared)
    monkeypatch.setattr(art_of_thinking_clearly, "prepare_art_of_thinking_clearly", prepare)

    pipeline.run_ingestion(book="art_of_thinking_clearly")

    components.extract_pages.assert_called_once_with(config.ART_OF_THINKING_CLEARLY_PDF_PATH)
    prepare.assert_called_once_with(components.pages)
    components.chunk_pages.assert_called_once_with(prepared, book="art_of_thinking_clearly")
    components.bm25_index.save.assert_called_once_with(config.book_bm25_path("art_of_thinking_clearly"))


def test_positive_thinking_uses_prepared_book_and_separate_index(ingestion_components, monkeypatch):
    from ingestion import positive_thinking

    components = ingestion_components
    prepared = [object()]
    prepare = Mock(return_value=prepared)
    monkeypatch.setattr(positive_thinking, "prepare_positive_thinking", prepare)

    pipeline.run_ingestion(book="positive_thinking")

    components.extract_pages.assert_called_once_with(config.POSITIVE_THINKING_PDF_PATH)
    prepare.assert_called_once_with(components.pages)
    components.chunk_pages.assert_called_once_with(prepared, book="positive_thinking")
    components.bm25_index.save.assert_called_once_with(config.book_bm25_path("positive_thinking"))


def test_subconscious_mind_uses_prepared_book_and_separate_index(ingestion_components, monkeypatch):
    from ingestion import subconscious_mind

    components = ingestion_components
    prepared = [object()]
    prepare = Mock(return_value=prepared)
    monkeypatch.setattr(subconscious_mind, "prepare_subconscious_mind", prepare)

    pipeline.run_ingestion(book="subconscious_mind")

    components.extract_pages.assert_called_once_with(config.SUBCONSCIOUS_MIND_PDF_PATH)
    prepare.assert_called_once_with(components.pages)
    components.chunk_pages.assert_called_once_with(prepared, book="subconscious_mind")
    components.bm25_index.save.assert_called_once_with(config.book_bm25_path("subconscious_mind"))


def test_existing_index_skips_ingestion(ingestion_components):
    components = ingestion_components
    components.vector_store.count.return_value = 3

    pipeline.run_ingestion()

    components.extract_pages.assert_not_called()
    components.embedding_engine.embed_texts.assert_not_called()
    components.vector_store.add_chunks.assert_not_called()
    components.bm25_index.build.assert_not_called()


def test_legacy_vector_metric_requires_rebuild(ingestion_components):
    components = ingestion_components
    components.vector_store.count.return_value = 3
    components.vector_store.require_cosine.side_effect = RuntimeError(
        "Vector index uses an old metric. Rebuild with ingest --force."
    )

    with pytest.raises(RuntimeError, match="ingest --force"):
        pipeline.run_ingestion()

    components.extract_pages.assert_not_called()


def test_force_replaces_existing_index(ingestion_components):
    components = ingestion_components
    components.vector_store.count.return_value = 3

    pipeline.run_ingestion(force=True)

    components.vector_store.reset.assert_called_once_with()
    components.vector_store.add_chunks.assert_called_once_with(
        components.chunks, [[0.1, 0.2]]
    )


def test_missing_pdf_does_not_reset_existing_index(ingestion_components):
    components = ingestion_components
    components.extract_pages.side_effect = FileNotFoundError("missing PDF")

    with pytest.raises(FileNotFoundError, match="missing PDF"):
        pipeline.run_ingestion(force=True)

    components.vector_store.reset.assert_not_called()
    components.embedding_engine.embed_texts.assert_not_called()
    components.vector_store.add_chunks.assert_not_called()


def test_no_chunks_stops_before_embedding(ingestion_components):
    components = ingestion_components
    components.chunk_pages.return_value = []

    with pytest.raises(ValueError, match="No text chunks"):
        pipeline.run_ingestion(force=True)

    components.embedding_engine.embed_texts.assert_not_called()
    components.vector_store.reset.assert_not_called()
    components.vector_store.add_chunks.assert_not_called()


def test_embedding_failure_does_not_reset_existing_index(ingestion_components):
    components = ingestion_components
    components.embedding_engine.embed_texts.side_effect = RuntimeError("embedding failed")

    with pytest.raises(RuntimeError, match="embedding failed"):
        pipeline.run_ingestion(force=True)

    components.vector_store.reset.assert_not_called()
    components.vector_store.add_chunks.assert_not_called()
    components.bm25_index.build.assert_not_called()


def test_store_failure_stops_later_stages(ingestion_components):
    components = ingestion_components
    components.vector_store.add_chunks.side_effect = OSError("store failed")

    with pytest.raises(OSError, match="store failed"):
        pipeline.run_ingestion()

    components.bm25_index.build.assert_not_called()
    components.save_chunks_json.assert_not_called()


def test_bm25_save_failure_is_reported(ingestion_components):
    components = ingestion_components
    components.bm25_index.save.side_effect = OSError("index failed")

    with pytest.raises(OSError, match="index failed"):
        pipeline.run_ingestion()

    components.save_chunks_json.assert_not_called()
