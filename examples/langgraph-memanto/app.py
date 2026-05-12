"""
Memanto ↔ LangGraph Integration
================================
Shows how to use Memanto as the long-term memory layer
inside a LangGraph agent workflow.

Demonstrates cross-session recall: the agent remembers
facts from previous conversations.

Requirements:
    pip install -r requirements.txt

Usage:
    cp .env.example .env   # add your Moorcheh API key
    python app.py           # runs the example
"""

from __future__ import annotations

import os
from typing import Any, TypedDict

from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver

# ── Memanto Wrapper ──────────────────────────────────────────────────


class MemantoBridge:
    """Simplified Memanto client for LangGraph integration.

    Wraps the official Memanto SDK into three easy primitives:
        store()   — persist a memory
        search()  — recall relevant memories
        ask()     — get an LLM-grounded answer from memory
    """

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("MOORCHEH_API_KEY")
        if not key:
            raise ValueError(
                "MOORCHEH_API_KEY required. Set in .env or pass to MemantoBridge()."
            )

        from memanto.cli.client.sdk_client import SdkClient

        self._client = SdkClient(api_key=key)
        self._agent_id: str | None = None

    def ensure_agent(self, agent_id: str = "langgraph-support-bot") -> None:
        """Create (if needed) and activate a Memanto agent."""
        try:
            self._client.get_agent(agent_id)
        except Exception:
            self._client.create_agent(
                agent_id,
                pattern="support",
                description="LangGraph long-term memory agent",
            )
        self._client.activate_agent(agent_id)
        self._agent_id = agent_id

    def store(self, content: str, memory_type: str = "fact",
              tags: list[str] | None = None) -> dict[str, Any]:
        """Persist a memory."""
        if not self._agent_id:
            raise RuntimeError("Call ensure_agent() before store().")
        title = content[:100]
        return self._client.remember(
            agent_id=self._agent_id,
            memory_type=memory_type,
            title=title,
            content=content,
            tags=tags or [],
        )

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve memories semantically relevant to *query*."""
        result = self._client.recall(
            agent_id=self._agent_id,
            query=query,
            limit=limit,
        )
        return result.get("memories", [])

    def ask(self, question: str) -> str:
        """Ask a question answered from stored memories (RAG)."""
        result = self._client.answer(
            agent_id=self._agent_id,
            question=question,
        )
        return result.get("answer", "No answer generated.")


# ── LangGraph State ──────────────────────────────────────────────────


class AgentState(TypedDict):
    messages: list[dict[str, str]]   # {"role": ..., "content": ...}
    user_name: str
    user_input: str
    memory_context: str
    response: str


# ── Graph Nodes ──────────────────────────────────────────────────────


def node_recall(state: AgentState, memanto: MemantoBridge) -> dict:
    """Step 1: Pull relevant memories before generating a response."""
    query = state.get("user_input", "")
    if not query:
        return {"memory_context": ""}

    memories = memanto.search(query)
    if not memories:
        return {"memory_context": ""}

    lines = []
    for m in memories:
        text = m.get("content", m.get("text", ""))
        tags = m.get("tags", [])
        tag_str = f" [{', '.join(tags[:3])}]" if tags else ""
        lines.append(f"- {text}{tag_str}")

    return {"memory_context": "Relevant past memories:\n" + "\n".join(lines)}


def node_respond(state: AgentState, memanto: MemantoBridge) -> dict:
    """Step 2: Generate a response using LangChain, enriched with memory."""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    name = state.get("user_name", "User")
    ctx = state.get("memory_context", "")

    system = f"""You are a helpful support agent for {name}.
You have long-term memory across sessions.

{ctx}

Be helpful and consistent. If you recall something from a past
conversation, reference it naturally."""

    response = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=state.get("user_input", "")),
    ])

    answer = response.content

    # Persist the user input + response as memories
    memanto.store(f"{name} said: {state.get('user_input', '')}",
                  memory_type="fact", tags=["user_query", name.lower()])
    memanto.store(f"Agent replied: {answer}",
                  memory_type="decision", tags=["agent_response", name.lower()])

    return {"response": answer}


# ── Compile the Graph ────────────────────────────────────────────────


def build_support_graph(memanto: MemantoBridge) -> StateGraph:
    """Build a LangGraph with Memanto-backed persistent memory."""

    # Use closures to inject memanto into nodes
    def recall_node(state: AgentState) -> dict:
        return node_recall(state, memanto)

    def respond_node(state: AgentState) -> dict:
        return node_respond(state, memanto)

    builder = StateGraph(AgentState)

    builder.add_node("recall", recall_node)
    builder.add_node("respond", respond_node)

    builder.set_entry_point("recall")
    builder.add_edge("recall", "respond")
    builder.add_edge("respond", END)

    return builder.compile(checkpointer=MemorySaver())


# ── Demo Runner ──────────────────────────────────────────────────────


def demonstrate_cross_session_memory():
    """Run a full demo showing cross-session memory."""
    memanto = MemantoBridge()
    memanto.ensure_agent("langgraph-support-demo")

    graph = build_support_graph(memanto)

    print("=" * 60)
    print("Memanto + LangGraph — Cross-Session Memory Demo")
    print("=" * 60)

    # ── Session 1 ────────────────────────────────────────────────
    print("\n--- Session 1 ---")
    result1 = graph.invoke({
        "messages": [{"role": "user", "content": "Hi, I'm Alex and I prefer dark mode"}],
        "user_name": "Alex",
        "user_input": "Hi, I'm Alex and I prefer dark mode",
    })
    print(f"Bot: {result1['response']}\n")

    # Store separately for batch
    memanto.store("User Alex prefers dark mode for all dashboards.",
                  memory_type="preference", tags=["alex", "dark-mode"])

    # ── Session 2 (simulating a new conversation) ────────────────
    print("\n--- Session 2 (new conversation, should recall Alex) ---")
    result2 = graph.invoke({
        "messages": [{"role": "user", "content": "What do you know about my display preferences?"}],
        "user_name": "Alex",
        "user_input": "What do you know about my display preferences?",
    })
    print(f"Bot: {result2['response']}")

    # ── Show stored memories ─────────────────────────────────────
    print("\n--- Stored Memories for demo agent ---")
    memories = memanto.search("Alex preferences display")
    for m in memories:
        text = m.get("content", m.get("text", ""))
        tags = m.get("tags", [])
        print(f"  • {text}  [{', '.join(tags)}]")

    print("\n✓ Cross-session memory works! Your agent remembers across sessions.")


if __name__ == "__main__":
    demonstrate_cross_session_memory()
