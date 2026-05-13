"""
Memanto Tools — LangGraph-compatible wrappers for Memanto's three primitives.

These tools wrap the Memanto `remember`, `recall`, and `answer` primitives
as LangGraph tools that can be bound to any LLM node.

Usage:
    tools = [memanto_remember, memanto_recall, memanto_answer]
    llm_with_tools = llm.bind_tools(tools)
"""

import os
import json
import logging
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _get_memanto_client():
    """Lazy-import and return a Memanto client.

    Returns None if MOORCHEH_API_KEY is not set, so the agent
    can degrade gracefully with a clear error message.
    """
    api_key = os.environ.get("MOORCHEH_API_KEY")
    if not api_key:
        return None
    try:
        from memanto.cli.client.sdk_client import SdkClient

        client = SdkClient(api_key=api_key)
        return client
    except ImportError:
        logger.warning("memanto package not installed")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize Memanto client: {e}")
        return None


# ─── Tool: remember ───────────────────────────────────────────────────────────


@tool
def memanto_remember(
    content: str,
    memory_type: str = "observation",
    agent_id: Optional[str] = None,
) -> str:
    """Store a memory into Memanto's long-term memory store.

    Call this whenever the agent learns something important about the user
    or the environment that should be remembered across sessions.

    Args:
        content: The factual content to remember (e.g., "User prefers dark mode")
        memory_type: One of: instruction, fact, decision, goal, commitment,
                     preference, relationship, context, event, learning,
                     observation, artifact, error
        agent_id: Optional agent namespace. Defaults to the active agent.

    Returns:
        A JSON string with the stored memory details, or an error message.
    """
    client = _get_memanto_client()
    if client is None:
        return (
            "ERROR: Memanto client not available. "
            "Set MOORCHEH_API_KEY environment variable."
        )

    try:
        if agent_id:
            client.agent_id = agent_id

        result = client.remember(content, type=memory_type)
        return json.dumps(
            {
                "status": "stored",
                "memory_type": memory_type,
                "content_preview": content[:100],
                "result": str(result),
            },
            indent=2,
        )
    except Exception as e:
        return f"ERROR storing memory: {e}"


# ─── Tool: recall ─────────────────────────────────────────────────────────────


@tool
def memanto_recall(
    query: str,
    memory_type: Optional[str] = None,
    limit: int = 5,
) -> str:
    """Search Memanto's long-term memory for relevant past information.

    Call this at the start of a conversation or when the user asks
    about past interactions. This is the key tool for cross-session recall.

    Args:
        query: Natural language search query (e.g., "What does the user like?")
        memory_type: Optional filter — restrict search to one memory type
        limit: Maximum number of results to return (default: 5)

    Returns:
        A list of matching memories with their content, type, and timestamps.
    """
    client = _get_memanto_client()
    if client is None:
        return (
            "ERROR: Memanto client not available. "
            "Set MOORCHEH_API_KEY environment variable."
        )

    try:
        kwargs = {"limit": limit}
        if memory_type:
            kwargs["type"] = memory_type

        results = client.recall(query, **kwargs)
        if not results:
            return "No relevant memories found."

        formatted = []
        for i, mem in enumerate(results, 1):
            formatted.append(
                f"{i}. [{mem.get('type', 'unknown')}] "
                f"{mem.get('content', '')[:200]} "
                f"(confidence: {mem.get('confidence', 'N/A')})"
            )
        return "\n".join(formatted)
    except Exception as e:
        return f"ERROR recalling memories: {e}"


# ─── Tool: answer (RAG) ──────────────────────────────────────────────────────


@tool
def memanto_answer(query: str) -> str:
    """Get a grounded AI answer generated directly from Memanto's memory store.

    Unlike `recall` which returns raw memory entries, `answer` runs
    retrieval-augmented generation (RAG) over the entire memory store
    to produce a natural-language answer.

    Use this when the user asks a question that requires synthesis
    across multiple memories.

    Args:
        query: The question to answer using stored memories

    Returns:
        A natural language answer grounded in Memanto's memory store.
    """
    client = _get_memanto_client()
    if client is None:
        return (
            "ERROR: Memanto client not available. "
            "Set MOORCHEH_API_KEY environment variable."
        )

    try:
        answer = client.answer(query)
        return str(answer)
    except Exception as e:
        return f"ERROR generating answer from memories: {e}"


# ─── Tool Listing ─────────────────────────────────────────────────────────────


MEMANTO_TOOLS = [memanto_remember, memanto_recall, memanto_answer]
"""List of all Memanto tools for easy binding to LangGraph nodes."""


def format_memory_context(memories: list[dict]) -> str:
    """Format a list of memory dicts into a context string for the LLM.

    Args:
        memories: List of memory dicts from recall()

    Returns:
        Formatted context string.
    """
    if not memories:
        return "No past memories retrieved."

    lines = ["\n📚 **Past Memories (from Memanto):**\n"]
    for i, mem in enumerate(memories, 1):
        content = mem.get("content", "").strip()
        mtype = mem.get("type", "unknown")
        timestamp = mem.get("timestamp", "")
        lines.append(f"  {i}. [{mtype}] \"{content}\" ({timestamp})")
    lines.append("")
    return "\n".join(lines)
