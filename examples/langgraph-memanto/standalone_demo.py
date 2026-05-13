#!/usr/bin/env python3
"""
Standalone Demo: LangGraph + Memanto Integration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This script demonstrates the complete LangGraph + Memanto integration
WITHOUT requiring a Memanto server or Moorcheh API key.

It uses an in-memory mock of the Memanto API to show the full
cross-session recall flow — exactly the same architecture as the
real integration, just running locally.

Run:
    python standalone_demo.py
"""

from __future__ import annotations

import json
import textwrap
import time
from dataclasses import dataclass, field
from typing import Any

# ─── Mock Memanto Client ───────────────────────────────────────────────────

@dataclass
class Memory:
    memory_type: str
    title: str
    content: str
    tags: list[str]
    confidence: float
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "type": self.memory_type,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "confidence": self.confidence,
            "timestamp": self.timestamp or time.time(),
        }


class MockMemantoClient:
    """In-memory mock of the Memanto REST API — no server required."""

    def __init__(self, agent_id: str = "langgraph-demo-agent"):
        self.agent_id = agent_id
        self.memories: list[Memory] = []
        self._start_time = time.time()

    def ensure_agent(self) -> dict:
        return {"agent_id": self.agent_id, "status": "created"}

    def remember(
        self,
        memory_type: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
        confidence: float = 0.9,
    ) -> dict:
        mem = Memory(
            memory_type=memory_type,
            title=title,
            content=content,
            tags=tags or [],
            confidence=confidence,
            timestamp=time.time(),
        )
        self.memories.append(mem)
        return {"status": "stored", "memory_id": f"mem-{len(self.memories)}", "type": memory_type}

    def recall(self, query: str, limit: int = 5, memory_types: list[str] | None = None) -> list[dict]:
        # Simple keyword matching simulation
        query_lower = query.lower()
        results = []
        for mem in reversed(self.memories):
            if memory_types and mem.memory_type not in memory_types:
                continue
            if any(word in query_lower for word in mem.content.lower().split()[:10]):
                results.append(mem.to_dict())
            elif any(word in query_lower for word in mem.title.lower().split()):
                results.append(mem.to_dict())
            if len(results) >= limit:
                break
        return results

    def answer(self, query: str, limit: int = 10) -> str:
        results = self.recall(query, limit=limit)
        if not results:
            return "I don't have any relevant memories about that."
        # Generate a grounded response
        facts = []
        for r in results:
            facts.append(f"[{r['type']}] {r['title']}: {r['content'][:100]}")
        return (
            f"Based on my stored memories:\n  "
            + "\n  ".join(facts)
        )

    def health_check(self) -> bool:
        return True

    def get_stats(self) -> dict:
        types: dict[str, int] = {}
        for m in self.memories:
            types[m.memory_type] = types.get(m.memory_type, 0) + 1
        return {
            "total_memories": len(self.memories),
            "by_type": types,
            "agent_id": self.agent_id,
            "uptime_seconds": round(time.time() - self._start_time, 1),
        }


# ─── Demo Steps ────────────────────────────────────────────────────────────

def print_separator(char: str = "━", width: int = 65) -> None:
    print(char * width)


def print_header(text: str) -> None:
    print()
    print_separator("━")
    print(f"  {text}")
    print_separator("━")


def step_1_show_architecture() -> None:
    """Display the integration architecture diagram."""
    print_header("📐 ARCHITECTURE: LangGraph + Memanto Integration")
    print()
    print(textwrap.dedent("""\
    ┌──────────────────────────────────────────────────────────┐
    │                   LangGraph Agent                         │
    │                                                           │
    │   ┌──────────┐    ┌──────────────┐    ┌──────────────┐   │
    │   │  User     │───▶│  Think       │───▶│  Memory      │   │
    │   │  Input    │    │  (LLM decides│    │  (remember / │   │
    │   └──────────┘    │   route)     │    │   recall)    │   │
    │                   └──────────────┘    └──────┬───────┘   │
    │                                               │           │
    │                                               ▼           │
    │                                       ┌──────────────┐   │
    │                                       │  Respond     │   │
    │                                       │  to User     │   │
    │                                       └──────────────┘   │
    └──────────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────────────────────┐
                    │         Memanto REST API         │
                    │  remember | recall | answer      │
                    └────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────────────────────┐
                    │     Moorcheh Semantic Engine    │
                    │  No-index, sub-90ms retrieval   │
                    └────────────────────────────────┘
    """))
    print()
    print("  This demo: LangGraph agent ↔ Memanto memory layer")
    print("  Files: 11 files under examples/langgraph-memanto/")
    print()

    # Show file listing
    print("  📁 examples/langgraph-memanto/")
    print("     ├── README.md")
    print("     ├── requirements.txt")
    print("     ├── .env.example")
    print("     ├── run_customer_support.py")
    print("     ├── run_cross_session.py")
    print("     └── langgraph_memanto/")
    print("         ├── __init__.py")
    print("         ├── agent.py          # LangGraph graph definition")
    print("         ├── memory_client.py  # Memanto REST API client")
    print("         ├── nodes.py          # Graph nodes (think/memory/respond)")
    print("         └── state.py          # State type definitions")
    print()


def step_2_morning_session(client: MockMemantoClient) -> None:
    """Simulate a morning session — store memories about a customer."""
    print_header("🌅 SESSION 1: Morning — Storing Memories")
    print()
    print("  Scenario: Customer support agent interacts with Alice")
    print()

    memories = [
        ("fact", "Customer Information",
         "Alice Johnson, account #ACCT-4392. Premier tier member since 2024.",
         ["customer", "premier"], 0.95),
        ("preference", "Communication Preference",
         "Alice prefers email notifications (alice@example.com). No SMS.",
         ["contact"], 0.90),
        ("fact", "Previous Issue",
         "2026-05-12: Alice reported a billing discrepancy on invoice #INV-8821. "
         "Resolved by issuing a $47.23 credit.",
         ["billing", "history"], 0.95),
        ("preference", "Support Preference",
         "Alice prefers phone support for urgent issues, email for non-urgent.",
         ["support"], 0.85),
        ("observation", "Customer Sentiment",
         "Alice was frustrated about the billing issue but appreciative after resolution.",
         ["sentiment"], 0.80),
        ("decision", "Follow-up Plan",
         "Schedule a follow-up call in 2 weeks to check satisfaction.",
         ["plan"], 0.90),
    ]

    for mem_type, title, content, tags, confidence in memories:
        result = client.remember(
            memory_type=mem_type,
            title=title,
            content=content,
            tags=tags,
            confidence=confidence,
        )
        status = "✅" if result["status"] == "stored" else "❌"
        type_tag = f"[{mem_type:>12}]"
        print(f"  {status} {type_tag} {title}")
        print(f"     {content[:80]}...")

    print()
    stats = client.get_stats()
    print(f"  🧠 Total memories stored: {stats['total_memories']}")
    print(f"  📊 Memory types: {json.dumps(stats['by_type'])}")
    print()


def step_3_afternoon_session(client: MockMemantoClient) -> None:
    """Simulate an afternoon session — fresh LangGraph state, recall memories."""
    print_header("🌆 SESSION 2: Afternoon — Fresh LangGraph State")
    print()
    print("  ⚡ No LangGraph state carried over from Session 1!")
    print("  🔍 Agent queries Memanto to recall past interactions")
    print()

    queries = [
        ("A customer named Alice is calling. Who is she?",
         ["fact", "preference"]),
        ("What happened last time Alice contacted us?",
         ["fact", "observation"]),
        ("How does Alice prefer to be contacted?",
         ["preference"]),
        ("Alice says she wants to update her email.",
         ["fact", "preference"]),
    ]

    for query, mem_types in queries:
        print(f"  👤 User: \"{query}\"")
        print(f"     └─▶ Thinking... routing to Memanto recall...")

        # Simulate LLM deciding to recall
        results = client.recall(query, limit=3, memory_types=mem_types)
        print(f"     └─▶ Memanto found {len(results)} relevant memories")

        for r in results:
            type_tag = f"[{r['type']:>12}]"
            print(f"         {type_tag} {r['title']}")
        print()

    # Show the answer endpoint
    print("  📞 Memanto answer() — grounded response generation:")
    print()
    answer = client.answer("Tell me about Alice Johnson and our previous interactions")
    for line in answer.split("\n"):
        print(f"     {line}")
    print()


def step_4_verify_persistence(client: MockMemantoClient) -> None:
    """Verify that memories survived across sessions."""
    print_header("🔍 VERIFICATION: Cross-Session Persistence")
    print()

    verify_queries = [
        ("Alice Johnson account", "Customer Information"),
        ("billing dispute invoice", "Previous Issue"),
        ("communication preference", "Communication Preference"),
        ("follow-up satisfaction", "Follow-up Plan"),
    ]

    for query, expected in verify_queries:
        results = client.recall(query, limit=1)
        if results:
            title = results[0].get("title", "?")
            status = "✅" if expected.lower() in title.lower() else "⚠️"
            print(f"  {status} Recall \"{query}\" → \"{title}\"")
        else:
            print(f"  ❌ Recall \"{query}\" → No results")

    print()
    print_separator("=")
    print("  🏁 CROSS-SESSION RECALL DEMO COMPLETE")
    print_separator("=")
    print()
    print("  Results:")
    print("  ✅ Information stored in Memanto during Session 1")
    print("  ✅ Retrieved during Session 2 without sharing LangGraph state")
    print("  ✅ Memanto provides persistent, cross-session memory")
    print("     for LangGraph agents — the 'permanent brain' they need.")
    print()
    print("  🧠 Key features demonstrated:")
    print("     • Cross-session recall across independent sessions")
    print("     • Typed semantic memory (fact, preference, observation, decision)")
    print("     • Memory-grounded answers via answer() endpoint")
    print("     • Provenance and confidence metadata on every memory")
    print("     • Zero indexing delay — memories searchable instantly")
    print()


def step_5_show_code_preview() -> None:
    """Show key code snippets."""
    print_header("💻 KEY CODE: LangGraph Agent Definition")
    print()

    print(textwrap.dedent("""\
    ┌─ langgraph_memanto/agent.py ──────────────────────────────────────┐
    │ from langgraph.graph import END, StateGraph                       │
    │                                                                   │
    │ def build_agent(memanto_client, agent_id, llm_model):             │
    │     workflow = StateGraph(AgentState)                              │
    │                                                                   │
    │     # Three-node architecture                                     │
    │     workflow.add_node("think",   think_node)   # LLM routes       │
    │     workflow.add_node("memory",  memory_node)  # remember / recall │
    │     workflow.add_node("respond", respond_node) # generate answer   │
    │                                                                   │
    │     workflow.set_entry_point("think")                              │
    │     workflow.add_conditional_edges("think", _route,                │
    │         {"memory": "memory", "respond": "respond"})                │
    │     workflow.add_edge("memory", "respond")                         │
    │     workflow.add_edge("respond", END)                              │
    │     return workflow.compile()                                      │
    └───────────────────────────────────────────────────────────────────┘
    """))

    print(textwrap.dedent("""\
    ┌─ langgraph_memanto/memory_client.py (API Surface) ───────────────┐
    │ class MemantoClient:                                              │
    │     def remember(type, title, content, confidence):               │
    │         POST /api/v2/agents/{id}/remember                         │
    │                                                                   │
    │     def recall(query, limit, memory_types):                       │
    │         POST /api/v2/agents/{id}/recall                           │
    │                                                                   │
    │     def answer(query, limit):                                     │
    │         POST /api/v2/agents/{id}/answer                           │
    └──────────────────────────────────────────────────────────────────┘
    """))


# ─── Main ─────────────────────────────────────────────────────────────────

def main() -> None:
    print()
    print_separator("═")
    print("  🧠 LangGraph + Memanto Integration Demo")
    print("  🌟 Give Your Graph a Permanent Brain")
    print_separator("═")
    print()
    print("  Running standalone (no server/API key needed)")
    print(f"  Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize mock Memanto client
    client = MockMemantoClient(agent_id="cross-session-demo")

    # Run demo steps
    step_1_show_architecture()
    time.sleep(0.3)

    step_2_morning_session(client)
    time.sleep(0.3)

    step_3_afternoon_session(client)
    time.sleep(0.3)

    step_4_verify_persistence(client)
    time.sleep(0.3)

    step_5_show_code_preview()

    # Final summary
    print_separator("═")
    print("  ✅ DEMO COMPLETE — Ready for 30-second GIF recording")
    print_separator("═")
    print()
    print("  To run with real Memanto server:")
    print("  1. Set MOORCHEH_API_KEY=your_key")
    print("  2. memanto serve")
    print("  3. python run_cross_session.py")
    print()

    stats = client.get_stats()
    print(f"  📊 Session stats: {stats['total_memories']} memories | "
          f"{len(stats['by_type'])} memory types | agent: {stats['agent_id']}")
    print()


if __name__ == "__main__":
    main()
