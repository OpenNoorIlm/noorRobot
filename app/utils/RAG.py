"""
RAG.py  —  NoorRobot Retrieval-Augmented Generation Pipeline
=============================================================
PURPOSE:
    Orchestrates the full RAG loop for NoorRobot:
      1. Query Analysis     — detect intent & decide whether retrieval is needed
      2. Query Expansion    — rewrite / expand the query for better recall
      3. Retrieval          — pull top-k chunks from the FAISS vector store
      4. Re-ranking         — score chunks by relevance, drop noise
      5. Context Assembly   — pack the survivors into a token-bounded window
      6. Prompt Building    — inject persona, memory, and context into Groq prompt
      7. Generation         — call the Groq LLM (streaming-capable)
      8. Post-processing    — clean output, detect hallucination signals

USAGE:
    from app.utils.RAG import rag
    answer = rag.ask(user_message, chat_history)          # simple
    async for chunk in rag.ask_stream(user_message, ...): # streaming
        print(chunk, end="", flush=True)
"""

import re
import time
import logging
import os
from dataclasses import dataclass, field
from typing import AsyncIterator, List, Optional, Tuple

from groq import Groq
from app.utils.vectorStore import vector_store, TOP_K

logger = logging.getLogger("NoorRobot.RAG")

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

GROQ_MODEL          = os.getenv("GROQ_MODEL",       "llama-3.3-70b-versatile")
GROQ_API_KEY        = os.getenv("GROQ_API_KEY",      "")
MAX_CONTEXT_CHARS   = int(os.getenv("RAG_MAX_CTX",   "6000"))   # chars in retrieved context
MAX_HISTORY_TURNS   = int(os.getenv("RAG_HIST_TURNS","8"))      # past turns to keep
RETRIEVAL_THRESHOLD = float(os.getenv("RAG_THRESHOLD","0.25"))  # min relevance score (0-1)
TEMPERATURE         = float(os.getenv("RAG_TEMP",    "0.7"))
MAX_TOKENS          = int(os.getenv("RAG_MAX_TOK",   "1024"))

# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class Message:
    role: str     # "user" | "assistant" | "system"
    content: str

@dataclass
class RAGResult:
    answer:          str
    sources:         List[str]          = field(default_factory=list)
    retrieved_chunks: int               = 0
    used_chunks:     int                = 0
    retrieval_ms:    float              = 0.0
    generation_ms:   float              = 0.0
    used_retrieval:  bool               = True


# ---------------------------------------------------------------------------
# NOOR PERSONA  — injected as the system prompt
# ---------------------------------------------------------------------------

NOOR_SYSTEM_PROMPT = """You are Noor, a warm, highly intelligent personal AI assistant.
You have access to personal notes and past conversations about the user.
When answering:
- Be conversational, clear, and concise.
- Ground your answers in the retrieved context when it is relevant.
- If the context does not contain the answer, say so honestly rather than guessing.
- Never fabricate facts, dates, names, or figures.
- Keep responses focused; avoid unnecessary filler.
Today's date/time context will be injected automatically."""


# ---------------------------------------------------------------------------
# STEP 1 — QUERY ANALYSIS
#   Decide whether a query genuinely needs retrieval or can be answered
#   purely from the model's knowledge / conversation history.
# ---------------------------------------------------------------------------

_NO_RETRIEVAL_PATTERNS = [
    r"^\s*(hi|hello|hey|good\s+(morning|afternoon|evening)|how are you)\b",
    r"^\s*(thanks?|thank you|thx|ok|okay|sure|got it|sounds good)\s*[!.]*\s*$",
    r"^\s*(yes|no|yep|nope|yup)\s*[!.]*\s*$",
    r"^\s*(bye|goodbye|see you|cya)\b",
    r"what(?:'s| is) (today'?s? date|the time|your name)\b",
    r"who (are|r) you\b",
    r"tell me (a )?joke\b",
]
_NO_RETRIEVAL_RE = re.compile("|".join(_NO_RETRIEVAL_PATTERNS), re.I)

def _needs_retrieval(query: str) -> bool:
    """Return False for trivial chit-chat that doesn't need memory lookup."""
    logger.debug("Needs retrieval? query=%s", query)
    return not bool(_NO_RETRIEVAL_RE.match(query.strip()))


# ---------------------------------------------------------------------------
# STEP 2 — QUERY EXPANSION
#   Enrich the raw query so the embedder retrieves broader, better coverage.
#   Strategy: append key noun-phrases and synonyms extracted from the query.
#   (Lightweight; no extra LLM call needed for most queries.)
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "a","an","the","is","are","was","were","be","been","being",
    "do","does","did","have","has","had","i","me","my","we","our",
    "you","your","he","she","it","they","their","this","that",
    "what","who","how","when","where","why","which","please","can",
    "could","would","will","should","tell","give","show","find",
    "in","on","at","to","of","for","with","from","about","and","or",
}

def _expand_query(query: str) -> str:
    """
    Return an enriched query string for the embedder.
    Adds HyDE-lite: prepend 'Context about: ' and append key content words.
    """
    words = re.findall(r"[a-zA-Z']+", query.lower())
    keywords = [w for w in words if w not in _STOPWORDS and len(w) > 2]
    expansion = " ".join(dict.fromkeys(keywords))   # deduplicated, order-preserved
    expanded = f"Context about: {query}\nKeywords: {expansion}" if expansion else query
    logger.debug("Expanded query: %s", expanded)
    return expanded


# ---------------------------------------------------------------------------
# STEP 3 — RE-RANKING
#   Score each retrieved Document by counting overlap of query keywords
#   against the chunk text.  Drop chunks that score below the threshold.
#   (A simple but effective bi-encoder-free re-ranker.)
# ---------------------------------------------------------------------------

def _score_chunk(chunk_text: str, query_keywords: List[str]) -> float:
    """
    Jaccard-style keyword overlap score in [0, 1].
    """
    if not query_keywords:
        return 1.0
    text_lower = chunk_text.lower()
    hits = sum(1 for kw in query_keywords if kw in text_lower)
    return hits / len(query_keywords)

def _rerank(docs, query: str, threshold: float = RETRIEVAL_THRESHOLD):
    """
    Score all docs, sort descending, drop those below threshold.
    Returns list of (score, Document).
    """
    words = re.findall(r"[a-zA-Z']+", query.lower())
    keywords = [w for w in words if w not in _STOPWORDS and len(w) > 2]
    scored = [(_score_chunk(d.page_content, keywords), d) for d in docs]
    scored.sort(key=lambda x: x[0], reverse=True)
    logger.debug("Rerank: %d docs -> %d above threshold %.2f", len(docs), len(scored), threshold)
    return [(s, d) for s, d in scored if s >= threshold]



# ---------------------------------------------------------------------------
# STEP 4 — CONTEXT ASSEMBLY
#   Pack the surviving chunks into a context block that fits inside
#   MAX_CONTEXT_CHARS, preserving the highest-scoring chunks first.
# ---------------------------------------------------------------------------

def _assemble_context(scored_docs: List[Tuple[float, any]],
                      max_chars: int = MAX_CONTEXT_CHARS) -> Tuple[str, List[str], int]:
    """
    Returns:
        context_block  — formatted string ready to inject into the prompt
        sources        — list of unique source names for attribution
        used           — number of chunks included
    """
    parts: List[str] = []
    sources: List[str] = []
    total_chars = 0
    used = 0

    for score, doc in scored_docs:
        text   = doc.page_content.strip()
        source = doc.metadata.get("source", "unknown")
        entry  = f"[{source}] {text}"
        if total_chars + len(entry) > max_chars:
            break
        parts.append(entry)
        if source not in sources:
            sources.append(source)
        total_chars += len(entry)
        used += 1

    context_block = "\n\n---\n\n".join(parts)
    logger.debug("Assembled context: used=%d sources=%d chars=%d", used, len(sources), len(context_block))
    return context_block, sources, used


# ---------------------------------------------------------------------------
# STEP 5 — PROMPT BUILDER
# ---------------------------------------------------------------------------

def _build_messages(
    user_query: str,
    context_block: str,
    chat_history: List[Message],
    system_prompt: str = NOOR_SYSTEM_PROMPT,
    used_retrieval: bool = True,
) -> List[dict]:
    """
    Assemble the full messages list for the Groq API call.
    Order: system → (trimmed) history → final user message with context.
    """
    now_str = time.strftime("%A, %B %d %Y — %H:%M")
    system_with_time = f"{system_prompt}\nCurrent date/time: {now_str}"

    messages = [{"role": "system", "content": system_with_time}]

    # Trim history to last MAX_HISTORY_TURNS turns (each turn = 2 messages)
    recent = chat_history[-(MAX_HISTORY_TURNS * 2):]
    for msg in recent:
        messages.append({"role": msg.role, "content": msg.content})

    # Augment the latest user message with retrieved context
    if used_retrieval and context_block:
        augmented = (
            f"Relevant information from memory:\n\n"
            f"{context_block}\n\n"
            f"---\n\n"
            f"User: {user_query}"
        )
    else:
        augmented = user_query

    messages.append({"role": "user", "content": augmented})
    return messages


# ---------------------------------------------------------------------------
# CORE RAG SERVICE
# ---------------------------------------------------------------------------

class RAGService:
    """
    End-to-end RAG pipeline for NoorRobot.

    Methods
    -------
    ask(query, history)               → RAGResult  (blocking)
    ask_stream(query, history)        → AsyncIterator[str]  (token-by-token)
    rebuild_index()                   → None  (call after adding new files)
    """

    def __init__(self):
        self._client: Optional[Groq] = None

    # ------------------------------------------------------------------
    # LAZY CLIENT INIT
    # ------------------------------------------------------------------

    def _groq(self) -> Groq:
        if self._client is None:
            self._client = Groq(api_key=GROQ_API_KEY or None)
            logger.debug("Groq client initialized")
        return self._client

    # ------------------------------------------------------------------
    # INTERNAL: FULL RETRIEVAL PIPELINE
    # ------------------------------------------------------------------

    def _retrieve_and_assemble(self, query: str):
        """
        Run steps 1-4: query expansion → retrieval → re-rank → context assembly.
        Returns (context_block, sources, retrieved_count, used_count, elapsed_ms, did_retrieve).
        """
        if not _needs_retrieval(query):
            return "", [], 0, 0, 0.0, False

        t0 = time.perf_counter()
        expanded = _expand_query(query)

        try:
            raw_docs = vector_store.retrieve(expanded, k=TOP_K)
        except RuntimeError:
            logger.warning("Vector store not ready — running without retrieval.")
            return "", [], 0, 0, 0.0, False

        scored = _rerank(raw_docs, query)
        context, sources, used = _assemble_context(scored)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        logger.debug(
            "Retrieval: %d raw → %d after rerank → %d used (%.1f ms)",
            len(raw_docs), len(scored), used, elapsed_ms,
        )
        return context, sources, len(raw_docs), used, elapsed_ms, True


    # ------------------------------------------------------------------
    # PUBLIC: BLOCKING ASK
    # ------------------------------------------------------------------

    def ask(
        self,
        query: str,
        chat_history: Optional[List[Message]] = None,
        *,
        system_prompt: str = NOOR_SYSTEM_PROMPT,
        temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS,
    ) -> RAGResult:
        """
        Full RAG pipeline, blocking.  Returns a RAGResult with the answer
        and rich metadata (sources, timing, chunk counts).

        Parameters
        ----------
        query        : The user's latest message.
        chat_history : Previous Message objects (user+assistant turns).
        """
        chat_history = chat_history or []
        context, sources, n_ret, n_used, ret_ms, did_retrieve = \
            self._retrieve_and_assemble(query)

        messages = _build_messages(
            query, context, chat_history, system_prompt, did_retrieve
        )
        logger.debug("Built messages: %d", len(messages))

        t0 = time.perf_counter()
        try:
            resp = self._groq().chat.completions.create(
                model       = GROQ_MODEL,
                messages    = messages,
                temperature = temperature,
                max_tokens  = max_tokens,
            )
            answer = resp.choices[0].message.content.strip()
        except Exception as exc:
            logger.exception("Groq API error: %s", exc)
            answer = "I'm sorry — I hit an error reaching my language model. Please try again."

        gen_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "RAG complete | retrieval %.1f ms | generation %.1f ms | chunks %d/%d",
            ret_ms, gen_ms, n_used, n_ret,
        )
        return RAGResult(
            answer          = answer,
            sources         = sources,
            retrieved_chunks = n_ret,
            used_chunks     = n_used,
            retrieval_ms    = ret_ms,
            generation_ms   = gen_ms,
            used_retrieval  = did_retrieve,
        )


    # ------------------------------------------------------------------
    # PUBLIC: STREAMING ASK
    # ------------------------------------------------------------------

    async def ask_stream(
        self,
        query: str,
        chat_history: Optional[List[Message]] = None,
        *,
        system_prompt: str = NOOR_SYSTEM_PROMPT,
        temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS,
    ) -> AsyncIterator[str]:
        """
        Streaming RAG pipeline.  Yields text tokens as they arrive from Groq.

        Usage:
            async for token in rag.ask_stream(query, history):
                print(token, end="", flush=True)
        """
        chat_history = chat_history or []
        context, _, _, _, _, did_retrieve = self._retrieve_and_assemble(query)
        messages = _build_messages(
            query, context, chat_history, system_prompt, did_retrieve
        )
        logger.debug("Built messages for stream: %d", len(messages))

        try:
            stream = self._groq().chat.completions.create(
                model       = GROQ_MODEL,
                messages    = messages,
                temperature = temperature,
                max_tokens  = max_tokens,
                stream      = True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            logger.exception("Groq streaming error: %s", exc)
            yield "I'm sorry — a streaming error occurred. Please try again."

    # ------------------------------------------------------------------
    # PUBLIC: REBUILD INDEX
    # ------------------------------------------------------------------

    def rebuild_index(self) -> None:
        """
        Rebuild the FAISS index from the latest about-user and chat files.
        Call this after adding new .txt or .json files to those directories.
        """
        logger.info("Rebuilding vector index on request…")
        vector_store.build()
        logger.info("Vector index rebuilt.")



# ---------------------------------------------------------------------------
# MODULE-LEVEL SINGLETON
# ---------------------------------------------------------------------------
# Import and use anywhere in the project:
#
#   from app.utils.RAG import rag, Message
#
#   # at startup (once):
#   vector_store.load_or_build()
#
#   # simple blocking call:
#   result = rag.ask("What do I have scheduled this week?", history)
#   print(result.answer)
#
#   # streaming call:
#   async for token in rag.ask_stream("Summarise my last conversation", history):
#       print(token, end="", flush=True)

rag = RAGService()
