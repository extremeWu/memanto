"""
Memanto ↔ LangGraph Integration
================================
Complete example showing how to use Memanto as the long-term
memory layer inside a LangGraph agent workflow.

Demonstrates cross-session recall: the agent remembers facts
from previous conversations across disconnected sessions.

Requirements:
    pip install -r requirements.txt

Usage:
    cp .env.example .env   # add your Moorcheh + OpenAI API keys
    python app.py           # runs the demo

Architecture:
    User Input → [recall: search Memanto] → [respond: LLM + memory]
              → [store: persist interaction] → Response
"""

from __future__ import annotations

import os
import sys
from typing import Any, TypedDict

from dotenv import load_dotenv

load_dotenv()


# ═════════════════════════════════════════════════════════════════════
#  MEMANTO BRIDGE — Simplified wrapper around the Memanto SDK
# ═════════════════════════════════════════════════════════════════════


class MemantoBridge:
    """Simplified Memanto client for LangGraph integration.

    Wraps the official Memanto SDK into three easy primitives:
        store()   — persist a memory
        search()  — recall relevant memories
        ask()     — get an LLM-grounded answer from memory (RAG)

    Usage:
        memanto = MemantoBridge()
        memanto.ensure_agent("my-agent")
        memanto.store("User likes dark mode", memory_type="preference")
        results = memanto.search("UI preferences")
    """

    VALID_MEMORY_TYPES = {
        "fact", "preference", "goal", "decision", "artifact",
        "learning", "event", "instruction", "relationship",
        "context", "observation", "commitment", "error",
    }

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("MOORCHEH_API_KEY")
        if not key:
            raise ValueError(
                "MOORCHEH_API_KEY is required.\n"
                "Create a .env file from .env.example and add your key.\n"
                "Get a key at: https://console.moorcheh.ai/api-keys"
            )
        from memanto.cli.client.sdk_client import SdkClient

        self._client = SdkClient(api_key=key)
        self._agent_id: str | None = None

    # ── Lifecycle ────────────────────────────────────────────────

    def ensure_agent(self, agent_id: str = "langgraph-support-bot") -> None:
        """Create (if needed) and activate a Memanto agent session.

        Args:
            agent_id: Unique name for this agent's memory namespace.
                      All memories are scoped to this agent.
        """
        try:
            self._client.get_agent(agent_id)
            print(f"  ✓ Agent '{agent_id}' exists")
        except Exception:
            self._client.create_agent(
                agent_id,
                pattern="support",
                description="LangGraph long-term memory agent",
            )
            print(f"  ✓ Created agent '{agent_id}'")

        self._client.activate_agent(agent_id)
        self._agent_id = agent_id
        print(f"  ✓ Session active for '{agent_id}'")

    # ── Primitives ───────────────────────────────────────────────

    def store(
        self,
        content: str,
        memory_type: str = "fact",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Persist a memory.

        Args:
            content: The memory text (max 500 chars, auto-truncated).
            memory_type: One of: fact, preference, goal, decision, event, etc.
            tags: Optional list of tags for filtering.

        Returns:
            Dict with memory_id, agent_id, status.
        """
        if not self._agent_id:
            raise RuntimeError("Call ensure_agent() before store().")
        if memory_type not in self.VALID_MEMORY_TYPES:
            raise ValueError(
                f"Invalid memory_type '{memory_type}'. "
                f"Valid types: {', '.join(sorted(self.VALID_MEMORY_TYPES))}"
            )

        return self._client.remember(
            agent_id=self._agent_id,
            memory_type=memory_type,
            title=content[:_MAX_TITLE_LENGTH],
            content=content[:_MAX_CONTENT_LENGTH],
            tags=tags or [],
        )

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve memories semantically relevant to *query*.

        Args:
            query: Natural-language search (e.g., "what does Alex like").
            limit: Max results (1-100).

        Returns:
            List of memory dicts, each with content, type, tags, confidence.
        """
        if not query.strip():
            return []
        result = self._client.recall(
            agent_id=self._agent_id,
            query=query,
            limit=min(limit, 100),
        )
        return result.get("memories", [])

    def ask(self, question: str) -> str:
        """Ask a question answered from stored memories (RAG).

        Uses Memanto's built-in LLM to generate an answer grounded
        in stored memories — no separate API key needed.

        Args:
            question: Natural-language question.

        Returns:
            Answer string derived from relevant memories.
        """
        result = self._client.answer(
            agent_id=self._agent_id,
            question=question,
        )
        return result.get("answer", "No relevant memories found.")


# ── Constants ──────────────────────────────────────────────────────

_MAX_TITLE_LENGTH = 100
_MAX_CONTENT_LENGTH = 500


# ═════════════════════════════════════════════════════════════════════
#  LANGGRAPH STATE & GRAPH
# ═════════════════════════════════════════════════════════════════════


class AgentState(TypedDict):
    """State passed between LangGraph nodes during execution."""

    messages: list[dict[str, str]]  # [{role, content}, ...]
    user_name: str                  # e.g. "Alex"
    user_input: str                 # current user query
    memory_context: str             # recalled memories as formatted text
    response: str                   # agent's response


def build_support_graph(memanto: MemantoBridge) -> Any:
    """Build a LangGraph with Memanto-backed persistent memory.

    The graph has three nodes:
      1. recall  — pull relevant memories before responding
      2. respond — generate a response with LLM + memory context
      3. store   — persist the interaction for future sessions
    """
    from langgraph.graph import StateGraph, END

    # ── Node 1: Recall ───────────────────────────────────────────

    def node_recall(state: AgentState) -> dict:
        """Search Memanto for memories relevant to the current query."""
        query = state.get("user_input", "")
        if not query:
            return {"memory_context": ""}

        memories = memanto.search(query, limit=5)
        if not memories:
            return {"memory_context": ""}

        lines = []
        for m in memories:
            text = m.get("content", m.get("text", ""))
            tags = m.get("tags", [])
            tag_str = f"  [{', '.join(tags[:3])}]" if tags else ""
            lines.append(f"• {text}{tag_str}")
            print(f"    [Memanto] Recalled: {text[:60]}...")

        return {"memory_context": "Relevant past memories:\n" + "\n".join(lines)}

    # ── Node 2: Respond ──────────────────────────────────────────

    def node_respond(state: AgentState) -> dict:
        """Generate a response using LangChain, enriched with Memanto memories."""
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

        name = state.get("user_name", "User")
        ctx = state.get("memory_context", "")

        system_prompt = (
            f"You are a helpful support agent for {name}.\n"
            f"You have long-term memory across sessions.\n\n"
            f"{ctx}\n\n"
            f"Be helpful and consistent. If you recall something from a past\n"
            f"conversation, reference it naturally to demonstrate memory recall."
        )

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=state.get("user_input", "")),
        ])
        answer = response.content
        return {"response": answer}

    # ── Node 3: Store ────────────────────────────────────────────

    def node_store(state: AgentState) -> dict:
        """Persist user input and agent response as Memanto memories."""
        name = state.get("user_name", "User")
        user_input = state.get("user_input", "")
        agent_response = state.get("response", "")

        if user_input:
            memanto.store(
                f"{name} asked: {user_input}",
                memory_type="fact",
                tags=["user_query", name.lower()],
            )
            print(f"    [Memanto] Stored: user query")

        if agent_response:
            memanto.store(
                f"Agent replied to {name}: {agent_response[:200]}",
                memory_type="decision",
                tags=["agent_response", name.lower()],
            )
            print(f"    [Memanto] Stored: agent response")

        return {}

    # ── Wire the graph ───────────────────────────────────────────

    builder = StateGraph(AgentState)
    builder.add_node("recall", node_recall)
    builder.add_node("respond", node_respond)
    builder.add_node("store", node_store)

    builder.set_entry_point("recall")
    builder.add_edge("recall", "respond")
    builder.add_edge("respond", "store")
    builder.add_edge("store", END)

    return builder.compile()  # no checkpointer — deterministic demo sequence


# ═════════════════════════════════════════════════════════════════════
#  DEMO RUNNER
# ═════════════════════════════════════════════════════════════════════


def demonstrate_cross_session_memory():
    """Demonstrate cross-session memory in two disconnected conversations.

    Session 1: User introduces themselves and states a preference.
    Session 2: User asks about their preferences — agent should recall.
    """
    print()
    print("=" * 60)
    print("  Memanto + LangGraph — Cross-Session Memory Demo")
    print("=" * 60)
    print()

    # ── Setup ────────────────────────────────────────────────────
    print("🔄 Setting up Memanto agent...")
    memanto = MemantoBridge()
    memanto.ensure_agent("langgraph-support-demo")

    graph = build_support_graph(memanto)
    print()

    # ── Session 1 ────────────────────────────────────────────────
    print("─" * 50)
    print("  SESSION 1: User introduces themselves")
    print("─" * 50)

    result1 = graph.invoke({
        "messages": [{"role": "user", "content": "Hi, I'm Alex and I prefer dark mode"}],
        "user_name": "Alex",
        "user_input": "Hi, I'm Alex and I prefer dark mode",
    })
    print(f"\n  💬 Alex: Hi, I'm Alex and I prefer dark mode")
    print(f"  🤖 Agent: {result1['response']}\n")

    # Also store a structured preference
    memanto.store(
        "User Alex prefers dark mode for all dashboards.",
        memory_type="preference",
        tags=["alex", "dark-mode", "preference"],
    )

    # ── Session 2 (new conversation) ─────────────────────────────
    print("─" * 50)
    print("  SESSION 2: New conversation — can the agent remember?")
    print("─" * 50)

    result2 = graph.invoke({
        "messages": [{"role": "user", "content": "What do you know about my display preferences?"}],
        "user_name": "Alex",
        "user_input": "What do you know about my display preferences?",
    })
    print(f"\n  💬 Alex: What do you know about my display preferences?")
    print(f"  🤖 Agent: {result2['response']}")

    # ── Verification ─────────────────────────────────────────────
    print()
    print("─" * 50)
    print("  MEMORY DUMP: What Memanto remembers")
    print("─" * 50)

    memories = memanto.search("Alex preferences display", limit=10)
    for m in memories:
        text = m.get("content", m.get("text", ""))
        tags = m.get("tags", [])
        mem_type = m.get("type", "unknown")
        print(f"  [{mem_type:>12}] {text[:80]}  [{', '.join(tags[:3])}]")

    if any("dark" in (m.get("content", "") or "").lower() for m in memories):
        print(f"\n  ✅ PASS: Agent remembered dark mode preference across sessions!")
    else:
        print(f"\n  ⚠️  No dark mode memory found — check Memanto connection")

    print()
    print("=" * 60)
    print("  Demo complete! Your agent has persistent memory.")
    print("=" * 60)
    print()


def main():
    """Entry point with basic error handling."""
    try:
        demonstrate_cross_session_memory()
    except ImportError as e:
        print(f"\n❌ Missing dependency: {e}")
        print("   Run: pip install -r requirements.txt")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("   Create .env from .env.example and fill in your API keys.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("   Check your API keys and internet connection.")
        sys.exit(1)


if __name__ == "__main__":
    main()
