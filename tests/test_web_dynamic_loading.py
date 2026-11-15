"""Late book indexes are usable without restarting an already current server."""

from unittest.mock import Mock

import config
from web import app as web_app


def test_loads_an_index_created_after_startup(monkeypatch, tmp_path):
    index = tmp_path / "book_bm25_index.pkl"
    index.write_bytes(b"ready")
    vector_store = Mock()
    vector_store.collection_exists.return_value = True
    vector_store.count.return_value = 553
    engine = object()
    llm = object()

    monkeypatch.setattr(web_app, "_engines", {})
    monkeypatch.setattr(web_app, "_embedding_engine", object())
    monkeypatch.setattr(web_app, "_reranker", object())
    monkeypatch.setattr(web_app, "_llm_client", llm)
    monkeypatch.setattr(web_app, "VectorStore", Mock(return_value=vector_store))
    monkeypatch.setattr(web_app.BM25Index, "load", Mock(return_value=object()))
    monkeypatch.setattr(web_app, "HybridRetriever", Mock(return_value=object()))
    monkeypatch.setattr(web_app, "QueryExpander", Mock(return_value=object()))
    monkeypatch.setattr(web_app, "QueryEngine", Mock(return_value=engine))
    monkeypatch.setattr(config, "book_bm25_path", lambda book: index)

    loaded = web_app._ensure_engine("little_book_of_stoicism")

    assert loaded is engine
    assert web_app._engines["little_book_of_stoicism"] is engine
    assert web_app._ensure_engine("little_book_of_stoicism") is engine
    web_app.BM25Index.load.assert_called_once_with(index)


def test_new_book_request_is_valid():
    request = web_app.QueryRequest(question="How should I respond to insults?",
                                   book="little_book_of_stoicism")
    assert request.book == "little_book_of_stoicism"
