"""
MemantoMemory - LangGraph Integration Layer

Provides a clean integration between LangGraph agents and Memanto's persistent
semantic memory. Enables cross-session, cross-agent memory with typed semantics.

Key Features:
  - Cross-session persistence: memories survive across LangGraph runs
  - Typed semantic memory: 13 categories (fact, preference, decision, etc.)
  - Automatic memory consolidation after each agent step
  - Retroactive memory retrieval for context injection
"""

import os
import json
import logging
from datetime import datetime
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("memanto-langgraph")


class MemantoMemory:
    """LangGraph-compatible wrapper around Memanto's semantic memory API.

    Usage:
        memory = MemantoMemory(agent_name="my-agent")
        memory.remember("User prefers concise answers", memory_type="preference")
        results = memory.recall("What does the user like?")
        answer = memory.answer("Based on memories, what theme should I use?")
    """

    def __init__(
        self,
        agent_name: str = "langgraph-agent",
        server_url: str | None = None,
        api_key: str | None = None,
    ):
        self.server_url = server_url or os.getenv(
            "MEMANTO_SERVER_URL", "http://127.0.0.1:8000"
        )
        self.api_key = api_key or os.getenv("MOORCHEH_API_KEY", "")
        self.agent_name = agent_name
        self._session_token: str | None = None
        self._agent_id: str | None = None

        if not self.api_key:
            logger.warning(
                "MOORCHEH_API_KEY not set. Set it in .env or pass api_key."
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def ensure_agent(self) -> str:
        """Create or verify the agent namespace exists, start a session."""
        if self._session_token and self._agent_id:
            return self._agent_id

        # Create agent if needed
        resp = requests.post(
            f"{self.server_url}/api/v2/agents",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"name": self.agent_name},
            timeout=10,
        )
        if resp.status_code == 409:  # already exists
            pass
        elif not resp.ok:
            logger.warning(
                f"Agent creation failed ({resp.status_code}): {resp.text[:200]}"
            )
        agent_data = resp.json() if resp.ok else {}
        self._agent_id = agent_data.get("id", self.agent_name)

        # Activate session
        session_resp = requests.post(
            f"{self.server_url}/api/v2/agents/{self._agent_id}/activate",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10,
        )
        if session_resp.ok:
            data = session_resp.json()
            self._session_token = data.get("session_token")

        return self._agent_id

    def close(self) -> None:
        """End the session gracefully."""
        if self._session_token and self._agent_id:
            try:
                requests.post(
                    f"{self.server_url}/api/v2/agents/{self._agent_id}/deactivate",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "X-Session-Token": self._session_token,
                    },
                    timeout=5,
                )
            except Exception:
                pass
            self._session_token = None

    def __enter__(self):
        self.ensure_agent()
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        h = {"Authorization": f"Bearer {self.api_key}"}
        if self._session_token:
            h["X-Session-Token"] = self._session_token
        return h

    def _agent_url(self, path: str = "") -> str:
        aid = self.ensure_agent()
        base = f"{self.server_url}/api/v2/agents/{aid}"
        return f"{base}{path}"

    # ------------------------------------------------------------------
    # Core Memory Operations
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        memory_type: str = "observation",
        metadata: dict | None = None,
    ) -> dict:
        """Store a memory into the semantic database.

        Args:
            content: The memory text to store.
            memory_type: One of: instruction, fact, decision, goal, commitment,
                        preference, relationship, context, event, learning,
                        observation, artifact, error.
            metadata: Optional dict with extra context (e.g. {"confidence": 0.9}).
        """
        payload = {
            "content": content,
            "type": memory_type,
            "metadata": metadata or {},
        }
        resp = requests.post(
            self._agent_url("/remember"),
            headers=self._headers(),
            json=payload,
            timeout=10,
        )
        if resp.ok:
            return resp.json()
        logger.warning(f"remember failed ({resp.status_code}): {resp.text[:200]}")
        return {"status": "error", "message": resp.text[:200], "content": content}

    def recall(
        self,
        query: str,
        memory_type: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """Semantic search over stored memories.

        Args:
            query: Natural language query.
            memory_type: Optional type filter (e.g. "fact", "preference").
            limit: Max results to return.

        Returns:
            List of memory dicts with keys: content, type, confidence, created_at.
        """
        payload = {"query": query, "limit": limit}
        if memory_type:
            payload["type"] = memory_type

        resp = requests.post(
            self._agent_url("/recall"),
            headers=self._headers(),
            json=payload,
            timeout=10,
        )
        if resp.ok:
            return resp.json().get("results", resp.json().get("memories", []))
        logger.warning(f"recall failed ({resp.status_code}): {resp.text[:200]}")
        return []

    def answer(
        self, question: str, memory_type: str | None = None
    ) -> str:
        """Get an LLM-grounded answer generated from memory context."""
        payload = {"question": question}
        if memory_type:
            payload["type"] = memory_type

        resp = requests.post(
            self._agent_url("/answer"),
            headers=self._headers(),
            json=payload,
            timeout=15,
        )
        if resp.ok:
            data = resp.json()
            return data.get("answer", data.get("response", ""))
        logger.warning(f"answer failed ({resp.status_code}): {resp.text[:200]}")
        return ""

    # ------------------------------------------------------------------
    # LangGraph Integration Helpers
    # ------------------------------------------------------------------

    def format_memories_for_context(self, query: str, limit: int = 5) -> str:
        """Format recalled memories as a system prompt snippet.

        Use this to inject relevant memories into a LangGraph node's context.
        """
        memories = self.recall(query, limit=limit)
        if not memories:
            return ""

        lines = ["## Relevant Past Memories (from Memanto)"]
        for i, m in enumerate(memories, 1):
            content = m.get("content", "")
            mtype = m.get("type", "unknown")
            confidence = m.get("confidence", m.get("score", ""))
            ts = m.get("created_at", "")
            line = f"  {i}. [{mtype}] {content}"
            if confidence:
                line += f" (confidence: {confidence})"
            if ts:
                line += f" [{ts}]"
            lines.append(line)
        return "\n".join(lines)

    def store_step_memory(
        self,
        agent_role: str,
        action: str,
        result: str,
        memory_type: str = "observation",
    ) -> dict:
        """Store a structured memory of an agent step.

        Args:
            agent_role: The role of the agent (e.g. "researcher", "support").
            action: What the agent did (e.g. "searched for X").
            result: Key finding or outcome.
            memory_type: Semantic memory category.
        """
        content = f"[{agent_role}] {action}: {result}"
        return self.remember(content, memory_type=memory_type)
