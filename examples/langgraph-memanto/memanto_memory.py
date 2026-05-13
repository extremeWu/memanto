"""
Memanto Memory Wrapper for LangGraph Agents.

Provides a clean Python class that wraps the Memanto CLI
(``memanto remember``, ``memanto recall``, ``memanto answer``)
so LangGraph nodes can store and retrieve memories across sessions
without needing a running REST server.

Usage::

    memory = MemantoMemory(agent_id="support-agent")
    memory.remember("User prefers Markdown formatting", "preference")
    results = memory.recall("Markdown preference")
"""

from __future__ import annotations

import os
import subprocess
from typing import Any


class MemantoMemory:
    """Persistent long-term memory backed by Memanto CLI.

    Stores memories using ``memanto remember`` and retrieves them
    with ``memanto recall`` / ``memanto answer``.  All operations
    go through the CLI so no background server is required.

    Attributes:
        agent_id: Unique identifier for this agent's memory namespace.
        server_proc: Optional subprocess handle when running in server mode.
    """

    def __init__(
        self,
        agent_id: str,
        api_key: str | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.server_proc = None

        # Set API key so the Memanto CLI can authenticate
        if api_key:
            os.environ.setdefault("MOORCHEH_API_KEY", api_key)

        self._ensure_agent()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _ensure_agent(self) -> None:
        """Create or activate the Memanto agent."""
        try:
            self._run_cli(["memanto", "agent", "activate", self.agent_id])
        except subprocess.CalledProcessError:
            self._run_cli(["memanto", "agent", "create", self.agent_id])

    def start_server(self) -> None:
        """Start the Memanto REST API server in the background.

        Only needed if you want to hit the REST API directly.
        CLI commands work fine without it.
        """
        self.server_proc = subprocess.Popen(
            ["memanto", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop_server(self) -> None:
        """Shut down the Memanto REST API server."""
        if self.server_proc:
            self.server_proc.terminate()
            self.server_proc.wait(timeout=5)
            self.server_proc = None

    # ------------------------------------------------------------------
    # Core memory operations
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        memory_type: str = "fact",
        tags: str | None = None,
        confidence: float = 0.9,
        provenance: str = "explicit_statement",
        source: str | None = None,
    ) -> None:
        """Store a memory entry.

        Args:
            content: The memory content (text).
            memory_type: Category — ``fact``, ``preference``, ``event``, etc.
            tags: Comma-separated tags for searchability.
            confidence: Confidence score (0.0 – 1.0).
            provenance: Where the memory came from.
            source: Override source (defaults to ``agent_id``).
        """
        cmd = [
            "memanto",
            "remember",
            content,
            "--type",
            memory_type,
            "--confidence",
            str(confidence),
            "--provenance",
            provenance,
            "--source",
            source or self.agent_id,
        ]
        if tags:
            cmd.extend(["--tags", tags])
        self._run_cli(cmd)

    def recall(
        self,
        query: str,
        limit: int = 10,
        memory_type: str | None = None,
    ) -> str:
        """Search for relevant memories.

        Args:
            query: Natural-language search query.
            limit: Maximum number of results.
            memory_type: Optional filter by type (e.g. ``preference``).

        Returns:
            Raw CLI output (human-readable list of memories).
        """
        cmd = ["memanto", "recall", query, "--limit", str(limit)]
        if memory_type:
            cmd.extend(["--type", memory_type])
        result = self._run_cli(cmd, capture=True)
        return result.stdout or ""

    def answer(self, question: str) -> str:
        """Ask a question against stored memories (RAG-style).

        Args:
            question: Natural-language question.

        Returns:
            Answer synthesised from relevant memories.
        """
        result = self._run_cli(["memanto", "answer", question], capture=True)
        return result.stdout or ""

    # ------------------------------------------------------------------
    # Batch / convenience
    # ------------------------------------------------------------------

    def store_interaction(
        self,
        user_message: str,
        agent_response: str,
        tags: str = "conversation,interaction",
    ) -> None:
        """Convenience: store a conversation turn as an event."""
        self.remember(
            f"User: {user_message}\nAgent: {agent_response}",
            memory_type="event",
            tags=tags,
        )

    def recall_context(self, limit: int = 5) -> str:
        """Get recent context for prompt-building."""
        return self.recall("recent conversation interaction", limit=limit)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _run_cli(
        cmd: list[str],
        capture: bool = False,
    ) -> subprocess.CompletedProcess:
        """Run a Memanto CLI command with error handling."""
        kwargs: dict[str, Any] = {"check": True, "timeout": 15}
        if capture:
            kwargs["capture_output"] = True
            kwargs["text"] = True
        return subprocess.run(cmd, **kwargs)

    @staticmethod
    def _format_memories(raw: str) -> list[dict[str, str]]:
        """Parse CLI recall output into structured dicts.

        The CLI returns human-readable text; this is a best-effort parser.
        Falls back to the raw string if parsing fails.
        """
        lines = [line.strip() for line in raw.split("\n") if line.strip()]
        memories = []
        current: dict[str, str] = {}
        for line in lines:
            if line.startswith("Memory"):
                if current:
                    memories.append(current)
                    current = {}
                current["id"] = line
            elif ":" in line:
                key, _, val = line.partition(":")
                current[key.strip().lower()] = val.strip()
        if current:
            memories.append(current)
        return memories if memories else raw
