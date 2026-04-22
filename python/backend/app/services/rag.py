"""
RAG service — re-export load_knowledge_base for main.py startup.
The actual RAG logic lives in app/agents/rag_agent.py.
"""
from app.agents.rag_agent import load_knowledge_base

__all__ = ["load_knowledge_base"]
