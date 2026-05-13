"""
Memanto helpers for LangGraph agents.

Provides a clean Pythonic wrapper around the memanto SDK client
that LangGraph nodes can call to persist and retrieve memories
across sessions.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class MemantoMemory:
    """Wraps the memanto client for use inside LangGraph nodes.

    Each MemantoMemory instance is bound to a single agent namespace.
    All memories written here are visible from any other process or
    session that uses the same ``agent_id``.
    """

    def __init__(self, agent_id: str | None = None):
        api_key = os.environ.get("MOORCHEH_API_KEY")
        if not api_key:
            raise RuntimeError(
                "MOORCHEH_API_KEY not set. "
                "Create one at https://console.moorcheh.ai/api-keys "
                "and add it to your .env file."
            )

        self.agent_id = agent_id or os.environ.get(
            "MEMANTO_AGENT_ID", "langgraph-support-agent"
        )
        self._api_key = api_key
        self._client: Any = None  # lazy-init
        self._session_active = False

    # ------------------------------------------------------------------
    # Lazy client + session
    # ------------------------------------------------------------------

    def _ensure_session(self) -> Any:
        """Return an authenticated SDK client with an active session."""
        if self._client is None:
            from memanto.cli.client.sdk_client import SdkClient

            self._client = SdkClient(api_key=self._api_key)

        if not self._session_active:
            try:
                self._client.get_agent(self.agent_id)
            except Exception:
                # Agent doesn't exist yet — create it
                self._client.create_agent(
                    agent_id=self.agent_id,
                    pattern="support",
                    description="LangGraph customer-support agent memory",
                )

            self._client.activate_agent(self.agent_id)
            self._session_active = True

        return self._client

    # ------------------------------------------------------------------
    # Public API for LangGraph nodes
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        *,
        memory_type: str = "fact",
        title: str | None = None,
        tags: list[str] | None = None,
        confidence: float = 0.9,
    ) -> dict[str, Any]:
        """Store a memory in the agent's persistent namespace.

        Args:
            content: The memory text (max 500 chars).
            memory_type: One of ``fact``, ``preference``, ``decision``,
                ``instruction``, ``goal``, ``commitment``, ``event``,
                ``observation``, ``context``, etc.
            title: Short label (max 100 chars). Auto-derived if omitted.
            tags: Optional tags for filtering.
            confidence: 0.0 – 1.0.

        Returns:
            Dict with ``memory_id``, ``agent_id``, ``status``.
        """
        client = self._ensure_session()

        if title is None:
            title = content[:47] + "..." if len(content) > 50 else content

        return client.remember(
            agent_id=self.agent_id,
            memory_type=memory_type,
            title=title,
            content=content,
            tags=tags or [],
            confidence=confidence,
        )

    def recall(
        self,
        query: str,
        *,
        limit: int = 10,
        memory_type: list[str] | None = None,
        min_confidence: float | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search across the agent's memory namespace.

        Args:
            query: Natural-language search phrase.
            limit: Max results.
            memory_type: Optional filter (e.g. ``["preference"]``).
            min_confidence: Minimum confidence threshold.

        Returns:
            List of memory dicts, each with ``content``, ``type``,
            ``confidence``, ``created_at``, etc.
        """
        client = self._ensure_session()
        result = client.recall(
            agent_id=self.agent_id,
            query=query,
            limit=limit,
            type=memory_type,
            min_confidence=min_confidence,
        )
        return result.get("memories", [])

    def answer(
        self,
        question: str,
        *,
        limit: int = 5,
    ) -> str:
        """Ask a question grounded in the agent's memory (RAG).

        The memanto service retrieves relevant memories and generates
        a concise answer using its built-in LLM — no separate API key
        needed for this step.

        Args:
            question: Natural-language question.
            limit: How many memories to use as context.

        Returns:
            Answer string grounded in stored memories.
        """
        client = self._ensure_session()
        result = client.answer(
            agent_id=self.agent_id,
            question=question,
            limit=limit,
        )
        return result.get("answer", "")

    def close(self) -> None:
        """Deactivate the session gracefully."""
        if self._client and self._session_active:
            try:
                self._client.deactivate_agent(self.agent_id)
            except Exception:
                pass
            self._session_active = False
