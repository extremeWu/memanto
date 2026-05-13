"""
LangGraph state definition and graph builder for the Customer Support Agent.

The graph has four nodes:
  1. ``load_memory`` — retrieves relevant user memories from memanto at startup
  2. ``call_model`` — calls the LLM with conversation history + memories
  3. ``save_memory`` — persists important facts/preferences back to memanto
  4. ``route_after_model`` — decides whether to continue or end

Cross-session recall is the key feature: when the graph starts, it queries
memanto for any relevant memories about the user, even if those memories
were created in a completely different LangGraph run (or by a different
tool/process entirely).
"""

from __future__ import annotations

import json
import os
from typing import Annotated, Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from memanto_helpers import MemantoMemory
from typing_extensions import TypedDict

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    """The state flowing through the LangGraph.

    Attributes:
        messages: Chat history (LangGraph-managed, current-session only).
        user_id: Optional identifier so memories are scoped per user.
        memory_context: Relevant memanto memories injected as context.
        new_memories: Accumulated facts/preferences to persist.
        memory_summary: Optional RAG-grounded answer from memanto.
    """

    messages: Annotated[list, add_messages]
    user_id: str
    memory_context: str
    new_memories: list[dict[str, Any]]
    memory_summary: str


# ---------------------------------------------------------------------------
# Shared memory instance
# ---------------------------------------------------------------------------

_memory_backend: MemantoMemory | None = None


def get_memory() -> MemantoMemory:
    global _memory_backend
    if _memory_backend is None:
        agent_id = os.environ.get("MEMANTO_AGENT_ID", "langgraph-support-agent")
        _memory_backend = MemantoMemory(agent_id=agent_id)
    return _memory_backend


def reset_memory() -> None:
    """Call this at the end of a run to clean up the session token."""
    global _memory_backend
    if _memory_backend:
        _memory_backend.close()
        _memory_backend = None


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def load_memory(state: AgentState) -> dict[str, Any]:
    """Query memanto for any relevant memories about this user.

    Uses the latest user message as a semantic search query so memanto
    returns past facts, preferences, or decisions that are relevant to
    the current conversation.
    """
    mem = get_memory()

    # Build a query from the recent user messages
    user_msgs = [m for m in state["messages"] if m.type == "human"]
    query = user_msgs[-1].content if user_msgs else "general context"

    # 1. Semantic recall — find relevant memories
    memories = mem.recall(
        query, limit=8, memory_type=["preference", "fact", "decision", "context"]
    )

    memory_context = ""
    if memories:
        lines = []
        for m in memories:
            content = m.get("content", "")
            mtype = m.get("type", "fact")
            created = m.get("created_at", "")[:10]
            lines.append(f"  - [{mtype}] ({created}) {content}")
        memory_context = (
            "The following memories exist about this user from past sessions:\n"
            + "\n".join(lines)
        )

    # 2. Also try an answer query for richer synthesis
    summary = ""
    try:
        summary = mem.answer(f"What do I know about this user? {query}")
    except Exception:
        pass

    return {
        "memory_context": memory_context,
        "memory_summary": summary,
    }


def call_model(state: AgentState) -> dict[str, Any]:
    """Call an LLM with the conversation history and any memory context.

    Uses a simple HTTP-based LLM call so no extra SDK is needed.
    You can swap this for ``langchain-openai``, ``anthropic``, or any
    other LangGraph-compatible chat model.
    """
    import httpx

    # --- Build the system prompt with memory context ---
    system_parts = [
        "You are a helpful customer support agent.",
        "You have access to a persistent long-term memory system (memanto).",
        "",
        "Below are memories retrieved from past sessions with this user.",
        "Use them to provide personalized, consistent support.",
    ]

    if state.get("memory_context"):
        system_parts.append("")
        system_parts.append(state["memory_context"])

    if state.get("memory_summary"):
        system_parts.append("")
        system_parts.append(f"Memory summary: {state['memory_summary']}")

    system_parts.append("")
    system_parts.append(
        "IMPORTANT — When you learn new facts or preferences about the user, "
        "output a JSON block at the end of your response with the key "
        "``__memories__`` containing a list of memory objects. "
        "Each memory object has ``content`` (string), ``type`` (string, "
        "one of: fact, preference, decision, instruction, goal, event), "
        "and optional ``tags`` (list of strings). "
        "Example:\n\n"
        '{"__memories__": [{"content": "User prefers dark mode", '
        '"type": "preference", "tags": ["theme"]}]}'
    )

    system_msg = {"role": "system", "content": "\n".join(system_parts)}

    # --- Build messages array for the LLM ---
    api_messages = [system_msg]
    for m in state["messages"]:
        role = "assistant" if m.type == "ai" else "user"
        api_messages.append({"role": role, "content": str(m.content)})

    # --- Call a free LLM endpoint ---
    # Uses OpenRouter's free tier as a default — users can override.
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("LLM_API_KEY")
    model = os.environ.get("LLM_MODEL", "openrouter/tencent/hunyuan-turbo:free")

    if not api_key:
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": (
                        "I need an LLM API key to work. "
                        "Please set OPENROUTER_API_KEY in your .env file "
                        "(get one free at https://openrouter.ai/keys)."
                    ),
                }
            ]
        }

    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": api_messages,
                "temperature": 0.7,
                "max_tokens": 1024,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
    except Exception as e:
        content = f"[Error calling LLM: {e}]"

    # --- Parse out any __memories__ JSON block ---
    new_memories: list[dict[str, Any]] = []
    cleaned_content = content

    try:
        # Try to find and extract JSON block
        if '"__memories__"' in content or "'__memories__'" in content:
            import re

            # Find the JSON block between the last ```json and ``` or between { and }
            json_match = re.search(
                r'\{\s*"__memories__"\s*:\s*\[.*?\]\s*\}', content, re.DOTALL
            )
            if json_match:
                payload = json.loads(json_match.group())
                new_memories = payload.get("__memories__", [])
                # Remove the JSON block from the response shown to the user
                cleaned_content = content.replace(json_match.group(), "").strip()
    except (json.JSONDecodeError, KeyError):
        pass

    return {
        "messages": [{"role": "assistant", "content": cleaned_content}],
        "new_memories": new_memories,
    }


def save_memory(state: AgentState) -> dict[str, Any]:
    """Persist any new memories extracted by the LLM back to memanto.

    This is what enables cross-session recall: memories saved here
    will be retrieved by ``load_memory`` on future runs.
    """
    mem = get_memory()
    saved_ids: list[str] = []

    for item in state.get("new_memories", []):
        try:
            result = mem.remember(
                content=item["content"],
                memory_type=item.get("type", "fact"),
                tags=item.get("tags"),
            )
            saved_ids.append(result.get("memory_id", "?"))
        except Exception as e:
            print(f"  [Warning] Failed to save memory: {e}")

    return {"new_memories": []}  # Clear the accumulation buffer


def route_after_model(state: AgentState) -> Literal["save_memory", "__end__"]:
    """Route to memory-save node if there are new memories, otherwise end."""
    if state.get("new_memories"):
        return "save_memory"
    return "__end__"


# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    """Build and compile the LangGraph state machine."""

    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("load_memory", load_memory)
    builder.add_node("call_model", call_model)
    builder.add_node("save_memory", save_memory)

    # Add edges
    builder.add_edge(START, "load_memory")
    builder.add_edge("load_memory", "call_model")
    builder.add_conditional_edges("call_model", route_after_model)
    builder.add_edge("save_memory", END)

    # Compile with checkpointing for conversation persistence
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
