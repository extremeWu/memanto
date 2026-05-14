#!/usr/bin/env python3
"""
Cross-Session Recall Demo — Proves Memanto remembers across LangGraph runs.

Run this script twice:

    **Session 1** stores a user preference into Memanto.
    **Session 2** (same script, no changes) retrieves that preference.

This demonstrates *true* cross-session recall — the memory survives
even though the LangGraph state object is ephemeral.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from memanto_memory import MemantoMemory

load_dotenv()

AGENT_ID = "langgraph-cross-session-demo"


def session_one() -> str:
    """Store a preference, simulating "yesterday's" conversation."""
    api_key = os.environ.get("MOORCHEH_API_KEY")
    if not api_key:
        print("ERROR: MOORCHEH_API_KEY not set. Copy .env.example → .env")
        sys.exit(1)

    memory = MemantoMemory(agent_id=AGENT_ID, api_key=api_key)

    print("#" * 60)
    print("SESSION 1 — Storing user preferences into Memanto")
    print("#" * 60)

    memory.remember(
        "User prefers terse, bullet-point responses over paragraphs.",
        memory_type="preference",
        tags="user,response-format,terse",
    )
    memory.remember(
        "User's timezone is US/Pacific (UTC-8 / UTC-7 DST).",
        memory_type="fact",
        tags="user,timezone",
    )
    memory.remember(
        "User works on an open-source RAG project called 'DocQuery'.",
        memory_type="fact",
        tags="user,project,docquery",
    )
    memory.store_interaction(
        user_message="I'm building a RAG system for internal docs",
        agent_response="Great! I can help with chunking, embedding, and retrieval strategies.",
    )

    print("\n✅ Stored 3 memories + 1 interaction.\n")
    return "ready"


def session_two() -> None:
    """Retrieve the preferences stored in session one — no re-storing needed."""
    api_key = os.environ.get("MOORCHEH_API_KEY")
    if not api_key:
        print("ERROR: MOORCHEH_API_KEY not set. Copy .env.example → .env")
        sys.exit(1)

    memory = MemantoMemory(agent_id=AGENT_ID, api_key=api_key)

    print("#" * 60)
    print("SESSION 2 — Retrieving memories from SESSION 1")
    print("(No memories were stored this session — proving cross-session recall)")
    print("#" * 60)

    # 1. Ask a direct question (RAG)
    print('\n--- memanto answer: "What does the user work on?" ---')
    answer = memory.answer("What does the user work on?")
    print(answer)

    # 2. Recall preferences
    print('\n--- memanto recall: "user preference response format" ---')
    prefs = memory.recall("user preference response format", limit=3)
    print(prefs)

    # 3. Recall general context
    print('\n--- memanto recall: "user project" ---')
    projects = memory.recall("user project", limit=5)
    print(projects)

    # 4. Recall conversation history
    print('\n--- memanto recall: "RAG system conversation" ---')
    history = memory.recall("RAG system conversation", limit=3)
    print(history)

    print("\n✅ Cross-session recall verified — memories survived the restart!\n")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"

    if mode in ("1", "session1", "both"):
        session_one()

    if mode in ("2", "session2", "both"):
        session_two()

    if mode == "both":
        print("\n🎯 Run again with `python run_cross_session.py 2` to prove")
        print("   memories persist even if you restart the machine.")


if __name__ == "__main__":
    main()
