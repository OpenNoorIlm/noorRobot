"""
vectorStore.py  —  NoorRobot Memory & Retrieval
================================================
PURPOSE:
    Gives NoorRobot semantic memory by combining two sources of knowledge:
      1. about-user/   — plain .txt files describing the user (name, prefs, etc.)
      2. database/chats/ — past conversation JSON files (saved by the chat layer)

    Both sources are chunked, embedded with a local HuggingFace model, and stored
    in a FAISS index on disk.  At query time only the top-k most relevant chunks
    are retrieved and injected into the prompt, keeping token usage bounded.

FLOW:
    build()  →  load docs  →  split into chunks  →  embed  →  FAISS index  →  save
    retrieve(query) →  load FAISS index  →  similarity search  →  return chunks
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# ---------------------------------------------------------------------------
# PATHS  (relative to this file:  app/utils/vectorStore.py)
# ---------------------------------------------------------------------------
_APP_DIR      = Path(__file__).parent.parent          # app/
ABOUT_USER_DIR = _APP_DIR / "about-user"              # app/about-user/
CHATS_DIR      = _APP_DIR / "database" / "chats"      # app/database/chats/
VECTOR_DIR     = _APP_DIR / "database" / "vector"     # app/database/vector/

# Create directories so the app can run on a fresh clone with no manual setup.
for _d in (ABOUT_USER_DIR, CHATS_DIR, VECTOR_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"   # runs fully locally
CHUNK_SIZE      = 1000   # characters per chunk
CHUNK_OVERLAP   = 200    # overlap between adjacent chunks
TOP_K           = 10     # how many chunks to retrieve per query

logger = logging.getLogger("NoorRobot")


# ---------------------------------------------------------------------------
# DOCUMENT LOADERS
# ---------------------------------------------------------------------------

def _load_about_user() -> List[Document]:
    """
    Read every .txt file in app/about-user/ and return one Document per file.
    These are hand-written facts about the user (name, preferences, schedule, etc.).
    """
    docs: List[Document] = []
    for path in sorted(ABOUT_USER_DIR.glob("*.txt")):
        try:
            logger.debug("Reading about-user file: %s", path)
            text = path.read_text(encoding="utf-8").strip()
            if text:
                docs.append(Document(
                    page_content=text,
                    metadata={"source": path.name, "type": "about-user"},
                ))
        except Exception as exc:
            logger.warning("Could not read about-user file %s: %s", path.name, exc)
    return docs


def _load_chat_history() -> List[Document]:
    """
    Read every .json file in app/database/chats/ and return one Document per file.
    Each file is expected to have the shape:
        { "session_id": "...", "messages": [{"role": "user"|"assistant", "content": "..."}, ...] }
    The messages are flattened into a single string so the embedder can understand context.
    """
    docs: List[Document] = []
    for path in sorted(CHATS_DIR.glob("*.json")):
        try:
            logger.debug("Reading chat history file: %s", path)
            data = json.loads(path.read_text(encoding="utf-8"))
            messages = data.get("messages", [])
            lines = []
            for msg in messages:
                role    = msg.get("role", "unknown").capitalize()
                content = msg.get("content", "").strip()
                if content:
                    lines.append(f"{role}: {content}")
            text = "\n".join(lines).strip()
            if text:
                docs.append(Document(
                    page_content=text,
                    metadata={"source": path.stem, "type": "chat-history"},
                ))
        except Exception as exc:
            logger.warning("Could not read chat file %s: %s", path.name, exc)
    return docs


# ---------------------------------------------------------------------------
# VECTOR STORE SERVICE
# ---------------------------------------------------------------------------

class VectorStoreService:
    """
    Wraps a FAISS vector store with:
      - build()    : (re)build the index from about-user + chat history files
      - retrieve() : return the top-k most relevant chunks for a query string
    The embedder runs locally on CPU — no API key needed.
    """

    def __init__(self):
        self._embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        self._store: Optional[FAISS] = None

    # ------------------------------------------------------------------
    # BUILD
    # ------------------------------------------------------------------

    def build(self) -> None:
        """
        Load all source documents, chunk them, embed, and save a FAISS index to disk.
        Call this once at startup (and again whenever new data is added).
        """
        about_docs = _load_about_user()
        chat_docs  = _load_chat_history()
        all_docs   = about_docs + chat_docs

        logger.info(
            "Building vector store: %d about-user docs, %d chat docs.",
            len(about_docs), len(chat_docs),
        )

        if not all_docs:
            # Nothing to embed yet — create a minimal placeholder so retrieve() never crashes.
            self._store = FAISS.from_texts(
                ["No user data available yet."],
                self._embeddings,
            )
        else:
            chunks = self._splitter.split_documents(all_docs)
            logger.info("Embedding %d chunks...", len(chunks))
            self._store = FAISS.from_documents(chunks, self._embeddings)

        self._store.save_local(str(VECTOR_DIR))
        logger.info("Vector store saved to %s", VECTOR_DIR)


    # ------------------------------------------------------------------
    # LOAD FROM DISK
    # ------------------------------------------------------------------

    def load(self) -> bool:
        """
        Load an existing FAISS index from disk (faster than rebuilding).
        Returns True on success, False if no index exists yet.
        Call build() first if this returns False.
        """
        index_file = VECTOR_DIR / "index.faiss"
        if not index_file.exists():
            logger.info("No saved vector store found at %s. Run build() first.", VECTOR_DIR)
            return False
        try:
            logger.debug("Loading FAISS index from %s", VECTOR_DIR)
            self._store = FAISS.load_local(
                str(VECTOR_DIR),
                self._embeddings,
                allow_dangerous_deserialization=True,
            )
            logger.info("Vector store loaded from %s", VECTOR_DIR)
            return True
        except Exception as exc:
            logger.error("Failed to load vector store: %s", exc)
            return False

    # ------------------------------------------------------------------
    # LOAD OR BUILD  (convenience method for startup)
    # ------------------------------------------------------------------

    def load_or_build(self) -> None:
        """
        Try to load a saved index; if none exists, build from scratch.
        This is the recommended call at application startup.
        """
        if not self.load():
            logger.info("No existing index — building from scratch.")
            self.build()

    # ------------------------------------------------------------------
    # RETRIEVE
    # ------------------------------------------------------------------

    def retrieve(self, query: str, k: int = TOP_K) -> List[Document]:
        """
        Return the top-k Document chunks most semantically similar to `query`.
        Raises RuntimeError if the store has not been built/loaded yet.
        """
        if self._store is None:
            raise RuntimeError(
                "Vector store is not initialised. Call load_or_build() at startup."
            )
        return self._store.similarity_search(query, k=k)

    def retrieve_text(self, query: str, k: int = TOP_K) -> str:
        """
        Convenience wrapper — returns retrieved chunks as a single joined string,
        ready to paste directly into a prompt.
        """
        docs = self.retrieve(query, k=k)
        return "\n\n".join(doc.page_content for doc in docs)

    # ------------------------------------------------------------------
    # RETRIEVER (LangChain-compatible)
    # ------------------------------------------------------------------

    def as_retriever(self, k: int = TOP_K):
        """
        Return a LangChain BaseRetriever so this store can be dropped into
        any LangChain RAG chain (e.g. RetrievalQA, ConversationalRetrievalChain).
        """
        if self._store is None:
            raise RuntimeError(
                "Vector store is not initialised. Call load_or_build() at startup."
            )
        return self._store.as_retriever(search_kwargs={"k": k})


# ---------------------------------------------------------------------------
# MODULE-LEVEL SINGLETON  (import and use directly)
# ---------------------------------------------------------------------------
# Usage anywhere in the project:
#   from app.utils.vectorStore import vector_store
#   vector_store.load_or_build()          # once at startup
#   context = vector_store.retrieve_text(user_query)

vector_store = VectorStoreService()

#===============================================================================================================================================================================================================

"""
================================================
NOTES:
- The vector store is designed to be simple and self-contained, with no external dependencies beyond the local filesystem and HuggingFace models.
- The build() method can be called whenever new about-user or chat files are added, allowing the index to stay up-to-date.
- The retrieve() method returns the most relevant chunks for a given query, which can then be injected into prompts to give NoorRobot access to its semantic memory without exceeding token limits.
- The as_retriever() method allows seamless integration with LangChain's RAG chains, enabling more complex retrieval-augmented generation workflows if desired.
- Error handling is included to ensure that missing or malformed files do not crash the application, and to provide clear logging for debugging.
"""
#===============================================================================================================================================================================================================

"""
HOW TO USE:
1. At application startup, call:
    from app.utils.vectorStore import vector_store
    vector_store.load_or_build()
    2. Whenever you want to retrieve relevant context for a user query, call:
    context = vector_store.retrieve_text(user_query)
    3. Inject `context` into your prompt template as needed.
    4. Whenever you add new .txt files to about-user/ or new .json chat files to database/chats/, call vector_store.build() again to update the index."""

#===============================================================================================================================================================================================================

"""code

from app.utils.vectorStore import vector_store

vector_store.load_or_build()          # once at startup
context = vector_store.retrieve_text(user_message)
# inject `context` into your Groq prompt as needed
# call vector_store.build() again whenever you add new about-user or chat files to update the index"""


"""
=====================================================================
__________________
|                                /\              /         |                                                 
|                               /  \            /          |                                                  
|                              /    \          /           |                                                  
|-----------------            /      \        /            |                                                    
|                            /        \      /             |                                                    
|                           /          \    /              |                                                      
|                          /            \  /               |                                                      
___________________       /              \/                |                                                                  
                                                                          
"""
