"""
app/RAG.py — Public RAG service export
======================================
Convenience re-export so other modules can import:
    from app.RAG import rag, Message, RAGResult, RAGService
"""

from app.utils.RAG import rag, Message, RAGResult, RAGService

__all__ = ["rag", "Message", "RAGResult", "RAGService"]
