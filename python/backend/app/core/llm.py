"""
Singleton Groq LLM clients — created once at import, reused everywhere.

Never instantiate ChatGroq per agent call. Import from here:
    from app.core.llm import primary_llm, fast_llm
"""
from langchain_groq import ChatGroq
from app.config import settings

# llama-3.3-70b — used by agents, synthesizer, complex reasoning
primary_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=settings.GROQ_API_KEY,
    temperature=0.3,
    max_retries=2,
)

# llama-3.1-8b — used by intent classifier (fast, cheap)
fast_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=settings.GROQ_API_KEY,
    temperature=0,
    max_retries=2,
)
