#!/usr/bin/env python3
"""
Interactive LangGraph + Memanto Chat Demo.

Run this script to start an interactive chat session with a LangGraph
customer-support agent that remembers everything across turns AND
across separate runs (thanks to Memanto's persistent memory).

Usage:
    python run_interactive.py

Type ``quit`` or ``exit`` to stop.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from memanto_memory import MemantoMemory

load_dotenv()

AGENT_ID = "langgraph-interactive-demo"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class ChatState(TypedDict):
    message: str
    context: str
    response: str
    learned: list[str]


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def make_nodes(memory: MemantoMemory):
    llm = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )

    def retrieve(state: ChatState) -> dict:
        ctx = memory.recall(state["message"], limit=5)
        prefs = memory.recall("user preference", limit=3)
        combined = []
        if ctx:
            combined.append("=== Relevant Memories ===")
            combined.append(ctx)
        if prefs:
            combined.append("=== User Preferences ===")
            combined.append(prefs)
        return {"context": "\n".join(combined) if combined else "No prior context."}

    def respond(state: ChatState) -> dict:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful agent with permanent memory. "
                    f"Context from past: {state['context']}\n\n"
                    "If you learn something new, end with '## LEARNED: <items>'."
                ),
            },
            {"role": "user", "content": state["message"]},
        ]
        resp = llm.invoke(messages)
        content = resp.content if hasattr(resp, "content") else str(resp)

        learned = []
        if "## LEARNED:" in content:
            _, _, tail = content.partition("## LEARNED:")
            for line in tail.strip().split("\n"):
                line = line.strip().strip("-*").strip()
                if line:
                    learned.append(line)
        return {"response": content, "learned": learned}

    def store(state: ChatState) -> None:
        memory.store_interaction(state["message"], state["response"])
        for pref in state.get("learned", []):
            memory.remember(pref, memory_type="preference", tags="user,preference")

    return retrieve, respond, store


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    api_key = os.environ.get("MOORCHEH_API_KEY")
    if not api_key:
        print("ERROR: MOORCHEH_API_KEY not set. Copy .env.example → .env")
        sys.exit(1)

    memory = MemantoMemory(agent_id=AGENT_ID, api_key=api_key)
    retrieve, respond, store = make_nodes(memory)

    graph = StateGraph(ChatState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("respond", respond)
    graph.add_node("store", store)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "respond")
    graph.add_edge("respond", "store")
    graph.add_edge("store", END)
    app = graph.compile()

    print("=" * 60)
    print("  LangGraph + Memanto Interactive Chat")
    print("  (Memories persist across sessions)")
    print("=" * 60)
    print("Type 'quit' to exit.\n")

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if msg.lower() in ("quit", "exit", "bye"):
            break

        result = app.invoke(
            {
                "message": msg,
                "context": "",
                "response": "",
                "learned": [],
            }
        )
        print(f"Agent:\n{result['response']}\n")

    memory.stop_server()


if __name__ == "__main__":
    main()
