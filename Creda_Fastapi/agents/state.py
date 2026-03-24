"""
Shared state schema for the LangGraph financial agent graph.
All agents read/write to this typed dictionary.
"""

from typing import List, Optional, Any, Dict
from langgraph.graph import MessagesState


class FinancialState(MessagesState):
    """
    Extends LangGraph's built-in MessagesState (which provides `messages`).
    Each field is available to every node in the graph.
    """
    user_id: str
    session_id: str
    language: str
    user_profile: Dict[str, Any]
    portfolio_data: Dict[str, Any]
    intent: str
    agent_outputs: Dict[str, Any]
    final_response: str
    response_data: Dict[str, Any]
