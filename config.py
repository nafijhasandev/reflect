"""
Central configuration for the RAG system.

All tunable parameters live here. Each setting has a comment explaining what it
does and why the default was chosen. Override via environment variables where
noted, or edit the defaults directly for experimentation.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Root of the project
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

# Where the source PDF lives
PDF_PATH = PROJECT_ROOT / "Atomic Habits by James Clear.pdf.pdf"
TINY_HABITS_PDF_PATH = PROJECT_ROOT / "tiny-habits.pdf"
POWER_OF_HABIT_PDF_PATH = PROJECT_ROOT / "Charles-Duhigg.The-Power-of-Habit.pdf"
POWER_OF_NOW_PDF_PATH = PROJECT_ROOT / "The Power of Now.pdf"
STOICISM_PDF_PATH = PROJECT_ROOT / "[Jonas_Salzgeber]_The_Little_Book_of_Stoicism__Tim(z-lib.org).pdf"
FIVE_SECOND_RULE_PDF_PATH = PROJECT_ROOT / "[Mel_Robbins]_The_5_Second_Rule__Transform_your_Li(z-lib.org).pdf"
EMOTIONAL_INTELLIGENCE_PDF_PATH = PROJECT_ROOT / "Emotional Intelligence Why it Can Matter More Than IQ by Daniel Goleman.pdf"
ART_OF_THINKING_CLEARLY_PDF_PATH = PROJECT_ROOT / "Rolf Dobelli - The Art of Thinking Clearly _ Better thinking, Better decision-Sceptre (Hodder _ Stoughton Ltd) (2013).pdf"
POSITIVE_THINKING_PDF_PATH = PROJECT_ROOT / "The Power of Positive Thinking .pdf"
SUBCONSCIOUS_MIND_PDF_PATH = PROJECT_ROOT / "The Power of Your Subconscious Mind.pdf"
BOOKS = {
    "atomic_habits": {"title": "Atomic Habits", "author": "James Clear"},
    "tiny_habits": {"title": "Tiny Habits", "author": "BJ Fogg"},
    "power_of_habit": {"title": "The Power of Habit", "author": "Charles Duhigg"},
    "power_of_now": {"title": "The Power of Now", "author": "Eckhart Tolle"},
    "little_book_of_stoicism": {"title": "The Little Book of Stoicism", "author": "Jonas Salzgeber"},
    "five_second_rule": {"title": "The 5 Second Rule", "author": "Mel Robbins"},
    "emotional_intelligence": {"title": "Emotional Intelligence", "author": "Daniel Goleman"},
    "art_of_thinking_clearly": {"title": "The Art of Thinking Clearly", "author": "Rolf Dobelli"},
    "positive_thinking": {"title": "The Power of Positive Thinking", "author": "Norman Vincent Peale"},
    "subconscious_mind": {"title": "The Power of Your Subconscious Mind", "author": "Joseph Murphy"},
}


def book_pdf_path(book: str) -> Path:
    if book == "atomic_habits":
        return PDF_PATH
    if book == "tiny_habits":
        return TINY_HABITS_PDF_PATH
    if book == "power_of_habit":
        return POWER_OF_HABIT_PDF_PATH
    if book == "power_of_now":
        return POWER_OF_NOW_PDF_PATH
    if book == "little_book_of_stoicism":
        return STOICISM_PDF_PATH
    if book == "five_second_rule":
        return FIVE_SECOND_RULE_PDF_PATH
    if book == "emotional_intelligence":
        return EMOTIONAL_INTELLIGENCE_PDF_PATH
    if book == "art_of_thinking_clearly":
        return ART_OF_THINKING_CLEARLY_PDF_PATH
    if book == "positive_thinking":
        return POSITIVE_THINKING_PDF_PATH
    if book == "subconscious_mind":
        return SUBCONSCIOUS_MIND_PDF_PATH
    raise ValueError(f"Unknown book: {book}")


def book_bm25_path(book: str) -> Path:
    if book not in BOOKS:
        raise ValueError(f"Unknown book: {book}")
    return BM25_INDEX_PATH if book == "atomic_habits" else DATA_DIR / f"{book}_bm25_index.pkl"


def book_chunks_path(book: str) -> Path:
    if book not in BOOKS:
        raise ValueError(f"Unknown book: {book}")
    return CHUNKS_JSON_PATH if book == "atomic_habits" else DATA_DIR / f"{book}_chunks.json"

# Where generated data is stored (ChromaDB, BM25 index, etc.)
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"
BM25_INDEX_PATH = DATA_DIR / "bm25_index.pkl"
CHUNKS_JSON_PATH = DATA_DIR / "chunks.json"
MODEL_CACHE_DIR = DATA_DIR / "model_cache"

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

# Most passages from this PDF fit the embedding model's 256-token window at this size.
CHUNK_SIZE = 800

# Overlap between consecutive chunks in characters.
# Overlap ensures ideas that span a chunk boundary aren't lost.
CHUNK_OVERLAP = 100

# ---------------------------------------------------------------------------
# Embedding model
# ---------------------------------------------------------------------------

# sentence-transformers model name.
# all-MiniLM-L6-v2: 384 dimensions, fast, good quality, runs on CPU.
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------

# ChromaDB collection name for this book
CHROMA_COLLECTION = "atomic_habits"

# ---------------------------------------------------------------------------
# BM25
# ---------------------------------------------------------------------------

# Stopwords removed during BM25 tokenization.
# These are common English words that add noise to keyword search.
BM25_STOPWORDS = {
    "a", "an", "the", "is", "it", "of", "in", "to", "and", "or", "for",
    "on", "at", "by", "with", "from", "as", "be", "was", "were", "been",
    "are", "have", "has", "had", "do", "does", "did", "but", "not", "this",
    "that", "these", "those", "i", "you", "he", "she", "we", "they", "my",
    "your", "his", "her", "its", "our", "their", "me", "him", "us", "them",
    "what", "which", "who", "whom", "when", "where", "how", "will", "would",
    "can", "could", "should", "may", "might", "shall", "must", "about",
    "into", "than", "then", "so", "if", "just", "also", "more", "very",
}

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

# How many candidates each retriever (dense / sparse) returns before fusion
RETRIEVAL_TOP_K = 10

# Constant for Reciprocal Rank Fusion. Standard value is 60.
# Higher values reduce the impact of rank differences.
RRF_K = 60

# How many candidates go into the reranker after RRF fusion
RERANK_CANDIDATES = 15

# How many chunks survive reranking and are sent to the LLM
FINAL_TOP_K = 5

# Default final passages by question type, as described in the SRS.
QUERY_TOP_K = {"factual": 3, "analytical": 5, "comparison": 5, "summary": 8}

# ---------------------------------------------------------------------------
# Reranker
# ---------------------------------------------------------------------------

# Cross-encoder model for reranking.
# ms-marco-MiniLM-L-6-v2: trained on passage ranking, runs on CPU.
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# ---------------------------------------------------------------------------
# Hosted language models
# ---------------------------------------------------------------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
VERCEL_API_KEY = os.getenv("VERCEL_API_KEY", "").strip()

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
VERCEL_AI_MODEL = os.getenv("VERCEL_AI_MODEL", "nvidia/nemotron-3.5-lightning-free")

LLM_TIMEOUT = 60
WEB_SEARCH_ENABLED = os.getenv("WEB_SEARCH_ENABLED", "true").strip().lower() not in {"0", "false", "no"}

# Temperature for generation. Lower = more focused, higher = more creative.
LLM_TEMPERATURE = 0.3

# ---------------------------------------------------------------------------
# Query engine
# ---------------------------------------------------------------------------

# Maximum characters of context to include in the LLM prompt.
# This leaves room for the system prompt and the generated answer
# within the model's context window.
MAX_CONTEXT_LENGTH = 6000

# ---------------------------------------------------------------------------
# Web server
# ---------------------------------------------------------------------------

WEB_HOST = "127.0.0.1"
WEB_PORT = 8000
