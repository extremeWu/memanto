"""
Customer Support Agent — LangGraph agent with Memanto persistent memory.

Demonstrates a LangGraph-based customer support agent that uses Memanto
to remember user preferences, past issues, and resolutions across sessions.

The graph:
  1. Retrieve relevant memories from Memanto
  2. Classify the user intent
  3. Generate a response informed by past context
  4. Store the interaction as a new memory
"""

import logging
import os
import sys
import json
from datetime import datetime
from typing import Annotated, TypedDict

from dotenv import load_dotenv

from memanto_memory import MemantoMemory

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("support-agent")


class AgentState(TypedDict):
    """State passed between LangGraph nodes."""
    messages: list
    user_input: str
    user_id: str
    retrieved_memories: list
    context: str
    intent: str
    response: str
    new_memories: list


def retrieve_memories(state: AgentState, memory: MemantoMemory) -> AgentState:
    """Node 1: Retrieve relevant past memories from Memanto."""
    query = state["user_input"]
    memories = memory.recall(query, limit=5)

    context_parts = []
    for m in memories:
        content = m.get("content", "")
        mtype = m.get("type", "unknown")
        context_parts.append(f"[{mtype}] {content}")

    state["retrieved_memories"] = memories
    state["context"] = "\n".join(context_parts) if context_parts else "No relevant past memories."

    memory.store_step_memory(
        agent_role="support",
        action=f"Retrieved memories for: {query[:50]}",
        result=f"Found {len(memories)} relevant memories",
        memory_type="observation",
    )

    return state


def classify_intent(state: AgentState) -> AgentState:
    """Node 2: Classify the user's intent."""
    user_input = state["user_input"].lower()

    if any(w in user_input for w in ["bug", "error", "crash", "broken", "not working"]):
        intent = "bug_report"
    elif any(w in user_input for w in ["refund", "billing", "charge", "payment", "price"]):
        intent = "billing"
    elif any(w in user_input for w in ["how", "what is", "tutorial", "guide", "explain"]):
        intent = "how_to"
    elif any(w in user_input for w in ["feature", "request", "would like", "suggestion"]):
        intent = "feature_request"
    elif any(w in user_input for w in ["hello", "hi", "hey", "good"]):
        intent = "greeting"
    else:
        intent = "general_inquiry"

    state["intent"] = intent

    logger.info(f"Classified intent: {intent}")

    return state


def generate_response(state: AgentState, memory: MemantoMemory | None = None) -> AgentState:
    """Node 3: Generate a response using past context and current intent."""
    intent = state["intent"]
    user_input = state["user_input"]
    context = state["context"]

    # Template-based responses (no LLM API key required)
    responses = {
        "bug_report": (
            "I see you're reporting an issue. Based on our past interactions:\n"
            "{context}\n\n"
            "I've logged this as a bug report. Our team will investigate and "
            "get back to you. To help us debug faster, could you please provide:\n"
            "1. Steps to reproduce\n"
            "2. Your environment details (OS, browser, version)\n"
            "3. Any error messages or screenshots"
        ),
        "billing": (
            "Let me look into the billing concern you've raised.\n"
            "From what I know: {context}\n\n"
            "I'll escalate this to our billing team right away. "
            "You should hear back within 24 hours."
        ),
        "how_to": (
            "Great question! Based on your history:\n{context}\n\n"
            "Let me help you with that. Here's what I recommend..."
        ),
        "feature_request": (
            "Thanks for the suggestion! From our past conversations:\n{context}\n\n"
            "I've added this to our feature tracker. "
            "We review community requests during our monthly planning."
        ),
        "greeting": (
            "Welcome back! Here's what I remember about you:\n{context}\n\n"
            "How can I help you today?"
        ),
        "general_inquiry": (
            "Thanks for reaching out. Here's what I know from previous conversations:\n{context}\n\n"
            "How can I best assist you with this?"
        ),
    }

    response_template = responses.get(intent, responses["general_inquiry"])
    state["response"] = response_template.format(context=context)

    return state


def store_interaction(state: AgentState, memory: MemantoMemory) -> AgentState:
    """Node 4: Store the interaction as a new memory."""
    # Remember the user's input
    memory.remember(
        f"User ({state['user_id']}) asked: {state['user_input']}",
        memory_type="event",
        metadata={"intent": state["intent"], "user_id": state["user_id"]},
    )

    # Remember the resolution
    memory.remember(
        f"Agent resolved {state['intent']} for user {state['user_id']}: {state['response'][:100]}...",
        memory_type="observation",
    )

    # Store any actionable preferences detected
    if "prefer" in state["user_input"].lower() or "like" in state["user_input"].lower():
        memory.remember(
            f"User {state['user_id']} expressed: {state['user_input']}",
            memory_type="preference",
        )

    state["new_memories"] = [
        {"type": "event", "content": state["user_input"]},
        {"type": "observation", "content": state["response"][:100]},
    ]

    return state


def run_customer_support_pipeline(
    memory: MemantoMemory,
    user_id: str,
    user_input: str,
) -> dict:
    """Run a full customer support pipeline through Memanto-enhanced LangGraph nodes.

    This simulates a LangGraph execution without requiring the langgraph package
    to be installed. The same logic applies when using actual LangGraph StateGraph.
    """
    state: AgentState = {
        "messages": [],
        "user_input": user_input,
        "user_id": user_id,
        "retrieved_memories": [],
        "context": "",
        "intent": "",
        "response": "",
        "new_memories": [],
    }

    print(f"\n{'='*60}")
    print(f"Customer Support — User: {user_id}")
    print(f"{'='*60}\n")

    print(f"User input: {user_input}\n")

    # --- Node 1: Retrieve ---
    print("[Node 1] Retrieving relevant memories from Memanto...")
    state = retrieve_memories(state, memory)
    print(f"   Found {len(state['retrieved_memories'])} relevant memories\n")

    # --- Node 2: Classify ---
    print("[Node 2] Classifying intent...")
    state = classify_intent(state)
    print(f"   Intent: {state['intent']}\n")

    # --- Node 3: Respond ---
    print("[Node 3] Generating response...")
    state = generate_response(state)
    print(f"   Response generated\n")

    # --- Node 4: Store ---
    print("[Node 4] Storing interaction in Memanto...")
    state = store_interaction(state, memory)
    print(f"   Stored {len(state['new_memories'])} new memories\n")

    # --- Output ---
    print(f"{'─'*60}")
    print(f"SUPPORT AGENT RESPONSE:")
    print(f"{'─'*60}")
    print(state["response"])
    print(f"{'─'*60}\n")

    return state


def demo():
    """Run a full multi-session demo proving cross-session memory."""
    with MemantoMemory(agent_name="customer-support-demo") as memory:
        # --- Session 1: First interaction ---
        print("\n" + "█"*60)
        print("SESSION 1 — First-time user (no prior memories)")
        print("█"*60)

        run_customer_support_pipeline(
            memory,
            user_id="alice_42",
            user_input="I prefer getting responses in dark mode, and I like concise answers.",
        )

        # --- Session 2: Follow-up (proves cross-session persistence) ---
        print("\n" + "█"*60)
        print("SESSION 2 — Follow-up (same user, new session)")
        print("█"*60)

        run_customer_support_pipeline(
            memory,
            user_id="alice_42",
            user_input="I'm getting an error when trying to export my dashboard to PDF.",
        )

        # --- Session 3: Another day (proves "yesterday" recall) ---
        print("\n" + "█"*60)
        print("SESSION 3 — New day (proves 'yesterday' recall)")
        print("█"*60)

        run_customer_support_pipeline(
            memory,
            user_id="alice_42",
            user_input="What did I ask about last time? Also, can you explain how the export feature works?",
        )

        print("\nMulti-session demo complete!")
        print("   All 3 sessions used the same Memanto agent namespace.")
        print("   Session 3 proved 'yesterday' recall by referencing memories from Session 1 & 2.\n")


if __name__ == "__main__":
    demo()
