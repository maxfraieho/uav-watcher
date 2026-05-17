"""LangGraph StateGraph — retrieve_kb → generate, MemorySaver per session."""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .states import CrisisState
from .nodes import retrieve_kb, generate


def build_graph():
    g = StateGraph(CrisisState)
    g.add_node("retrieve_kb", retrieve_kb)
    g.add_node("generate", generate)
    g.set_entry_point("retrieve_kb")
    g.add_edge("retrieve_kb", "generate")
    g.add_edge("generate", END)
    return g.compile(checkpointer=MemorySaver())


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
