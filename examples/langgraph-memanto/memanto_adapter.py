"""
Memanto ↔ LangGraph Adapter
---------------------------
Provides LangGraph-compatible tools and nodes that connect
to Memanto''s long-term memory layer.

Three primitives:
  - memorize() —— store a new memory
  - recall()   —— retrieve relevant memories
  - reflect()  —— get an LLM-grounded answer from memory
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class MemantoClient:
    """Thin wrapper around Memanto''s SDK for LangGraph integration."""

    def __init__(self, api_key: str | None = None):
        from memanto.cli.client.sdk_client import SdkClient

        key = api_key or os.getenv("MOORCHEH_API_KEY")
        if not key:
            raise ValueError(
                "MOORCHEH_API_KEY is required. "
                "Set it in .env or pass api_key= to MemantoClient."
            )
        self._client = SdkClient(api_key=key)
        self._agent_id: str | None = None
        self._session_token: str | None = None

    @property
    def agent_id(self) -> str:
        if self._agent_id is None:
            raise RuntimeError("No agent activated. Call activate() first.")
        return self._agent_id

    def activate(self, agent_id: str, create_if_missing: bool = True) -> dict[str, Any]:
        """Activate (or create + activate) a Memanto agent session."""
        try:
            self._client.get_agent(agent_id)
        except Exception:
            if not create_if_missing:
                raise
            self._client.create_agent(agent_id, pattern="support",
                                       description="LangGraph long-term memory agent")

        session = self._client.activate_agent(agent_id)
        self._agent_id = agent_id
        self._session_token = session["session_token"]
        return session

    def memorize(self, content: str, memory_type: str = "fact",
                 tags: list[str] | None = None) -> dict[str, Any]:
        """Store a memory.  Content is auto-truncated to 500 chars."""
        return self._client.remember(
            agent_id=self.agent_id,
            memory_type=memory_type,
            title=content[:_MAX_TITLE_LENGTH],
            content=content[:_MAX_CONTENT_LENGTH],
            tags=tags or [],
        )

    def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve memories relevant to *query*."""
        result = self._client.recall(
            agent_id=self.agent_id,
            query=query,
            limit=limit,
        )
        return result.get("memories", result.get("results", []))

    def reflect(self, query: str) -> str:
        """Ask Memanto to generate an answer grounded in stored memories."""
        result = self._client.answer(
            agent_id=self.agent_id,
            question=query,  # SdkClient.answer uses question=, not query=
        )
        return result.get("answer", result.get("response", ""))


_MAX_TITLE_LENGTH = 100
_MAX_CONTENT_LENGTH = 500


# ── LangGraph State & Nodes ──────────────────────────────────────────

from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver  # in-memory checkpointing
import operator


class AgentState(TypedDict):
    """State passed between LangGraph nodes."""
    messages: Annotated[Sequence[dict], operator.add]
    user_id: str
    session_id: str
    memanto_memories: list[dict]


def build_memory_graph(memanto: MemantoClient) -> StateGraph:
    """Build a LangGraph that uses Memanto for persistent memory."""

    # ── Nodes ──────────────────────────────────────────────────────

    def store_interaction(state: AgentState) -> dict:
        """Store the latest user message as a Memanto memory."""
        last_msg = state["messages"][-1]["content"] if state["messages"] else ""
        if last_msg:
            memanto.memorize(
                content=last_msg,
                memory_type="fact",
                tags=["user_query", state.get("user_id", "unknown")],
            )
        return {"memanto_memories": []}

    def recall_context(state: AgentState) -> dict:
        """Retrieve relevant past memories before responding."""
        query = state["messages"][-1]["content"] if state["messages"] else ""
        memories = memanto.recall(query=query, limit=5)
        return {"memanto_memories": memories}

    def generate_response(state: AgentState) -> dict:
        """Generate a response using LangChain, enriched with Memanto memories."""
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

        # Build system prompt with recalled memories
        memory_context = ""
        if state.get("memanto_memories"):
            memory_context = "\nRelevant past memories:\n"
            for m in state["memanto_memories"]:
                content = m.get("content", m.get("text", str(m)))
                memory_context += f"- {content}\n"

        system_prompt = f"""You are a helpful customer support agent.
You have persistent memory across sessions.
Use the context below to provide personalized, consistent responses.

{memory_context}
Remember to store important information about the user for future sessions."""

        from langchain_core.messages import SystemMessage, HumanMessage

        messages = [
            SystemMessage(content=system_prompt),
            *[HumanMessage(content=m["content"]) for m in state["messages"]],
        ]
        response = llm.invoke(messages)

        # Store the response in Memanto too
        memanto.memorize(
            content=f"Agent response: {response.content}",
            memory_type="decision",
            tags=["agent_response", state.get("user_id", "unknown")],
        )

        return {"messages": [{"role": "assistant", "content": response.content}]}

    # ── Wire graph ────────────────────────────────────────────────

    builder = StateGraph(AgentState)

    builder.add_node("recall_context", recall_context)
    builder.add_node("generate_response", generate_response)
    builder.add_node("store_interaction", store_interaction)

    builder.set_entry_point("recall_context")
    builder.add_edge("recall_context", "generate_response")
    builder.add_edge("generate_response", "store_interaction")
    builder.add_edge("store_interaction", END)

    return builder.compile(checkpointer=MemorySaver())
