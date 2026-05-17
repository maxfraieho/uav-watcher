from typing import TypedDict, Annotated
from langgraph.graph import add_messages


class CrisisState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    kb_context: str
    web_context: str
    reply: str
    session_id: str
