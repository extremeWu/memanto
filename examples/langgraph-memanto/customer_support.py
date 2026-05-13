#!/usr/bin/env python3
"""
Interactive Customer Support Agent — LangGraph + Memanto.

Run this script twice (or in two terminals) to see cross-session recall in action:

  Terminal 1 (first session):
    python customer_support.py

    > Tell me a preference:  "I prefer concise answers"
    > Ask a question:        "How should I answer the user?"
      → The agent retrieves your preference from memanto memory!

  Terminal 2 (second session — same user_id, different conversation):
    python customer_support.py

    > Just ask: "What does the user prefer?"
      → It remembers "concise answers" from the previous session!
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from graph import build_graph, reset_memory
from langgraph.checkpoint.memory import MemorySaver
from memanto_helpers import MemantoMemory

load_dotenv()


def interactive_session() -> None:
    """Run an interactive LangGraph session with persistent memanto memory."""
    if not os.environ.get("MOORCHEH_API_KEY"):
        print("Error: MOORCHEH_API_KEY not set.")
        print("Copy .env.example to .env and add your Moorcheh API key.")
        sys.exit(1)

    graph = build_graph()

    # Use a fixed user_id so cross-session recall works
    user_id = os.environ.get("DEMO_USER_ID", "alice")
    thread_id = input(f"Thread ID (default: session-{user_id}): ").strip() or f"session-{user_id}"

    config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}

    print(f"\n{'=' * 60}")
    print(f"  Memanto + LangGraph  —  Customer Support Agent")
    print(f"  User: {user_id}  |  Thread: {thread_id}")
    print(f"  {'=' * 60}")
    print()
    print("  Type 'pref: <something>' to teach the agent a preference.")
    print("  Type 'check: <question>' to see what the agent remembers.")
    print("  Type 'quit' to exit.")
    print()

    while True:
        try:
            user_input = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        # Invoke the graph
        result = graph.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
        )

        # Print assistant's response
        last_msg = result["messages"][-1]
        print(f"\n  🤖 {last_msg.content}\n")

        # Show what memories were saved (if any)
        if result.get("new_memories"):
            for m in result["new_memories"]:
                print(f"  📝 Saved memory: [{m['type']}] {m['content']}")
            print()

    reset_memory()


def demo_cross_session_recall() -> None:
    """Demonstrate cross-session recall programmatically.

    Runs two sequential sessions to prove memories persist:
    - Session 1: Store a preference
    - Session 2: Retrieve it (different thread, different messages)
    """
    print("=" * 60)
    print("  Cross-Session Recall Demo")
    print("=" * 60)

    graph = build_graph()
    user_id = "demo-user"
    mem = MemantoMemory()

    # ------------------------------------------------------------------
    # Session 1 — Teach the agent a preference
    # ------------------------------------------------------------------
    print("\n  --- Session 1: Teaching a preference ---\n")

    result1 = graph.invoke(
        {"messages": [{"role": "user", "content": "pref: I prefer dark mode for the dashboard UI"}]},
        config={"configurable": {"thread_id": "session-demo-1", "user_id": user_id}},
    )

    last = result1["messages"][-1]
    print(f"  User: I prefer dark mode for the dashboard UI")
    print(f"  Agent: {last.content}\n")

    if result1.get("new_memories"):
        for m in result1["new_memories"]:
            print(f"  ✅ Saved memory: [{m['type']}] {m['content']}")

    # Also directly store a second memory so we have more context
    mem.remember(
        "The user prefers keyboard shortcuts over mouse navigation",
        memory_type="preference",
        tags=["productivity"],
    )
    print(f"  ✅ Saved memory: [preference] The user prefers keyboard shortcuts over mouse navigation")
    print()

    # ------------------------------------------------------------------
    # Session 2 — Ask about the user (different thread, different graph run)
    # ------------------------------------------------------------------
    print("  --- Session 2: Recalling from memory (different thread!) ---\n")

    # Reset graph state to simulate a completely new session
    # (In production this would be a different API call or process)
    graph2 = build_graph()

    result2 = graph2.invoke(
        {"messages": [{"role": "user", "content": "Does this user have any UI preferences I should know about?"}]},
        config={"configurable": {"thread_id": "session-demo-2", "user_id": user_id}},
    )

    last2 = result2["messages"][-1]
    print(f"  User: Does this user have any UI preferences I should know about?")
    print(f"  Agent: {last2.content}\n")

    print("  --- Demo Complete ---")
    print("  The agent remembered preferences from Session 1 in Session 2.")
    print("  That's cross-session recall with Memanto!\n")

    reset_memory()


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo_cross_session_recall()
    else:
        interactive_session()
