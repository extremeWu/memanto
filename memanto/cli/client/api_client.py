"""
MEMANTO V2 API Client

Simplified wrapper around MEMANTO V2 REST API
"""

from datetime import datetime
from typing import Any, cast

import httpx


class MemantoAPIClient:
    """MEMANTO V2 API Client"""

    def __init__(self, base_url: str, api_key: str):
        """
        Initialize API client

        Args:
            base_url: MEMANTO server URL
            api_key: Moorcheh API key
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session_token: str | None = None
        self.agent_id: str | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get request headers"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.session_token:
            headers["X-Session-Token"] = self.session_token
        return headers

    def _json_dict(self, response: httpx.Response) -> dict[str, Any]:
        """Parse JSON object response into a typed dict."""
        return cast(dict[str, Any], response.json())

    # Agent Management

    def create_agent(
        self, agent_id: str, pattern: str = "tool", description: str | None = None
    ) -> dict[str, Any]:
        """Create new agent"""
        url = f"{self.base_url}/api/v2/agents"
        payload = {"agent_id": agent_id, "pattern": pattern}
        if description:
            payload["description"] = description

        response = httpx.post(url, json=payload, headers=self._get_headers())
        if response.status_code == 409:
            raise ValueError(f"Agent '{agent_id}' already exists.")
        response.raise_for_status()
        return self._json_dict(response)

    def list_agents(self) -> list[dict[str, Any]]:
        """List all agents"""
        url = f"{self.base_url}/api/v2/agents"
        response = httpx.get(url, headers=self._get_headers())
        response.raise_for_status()
        data = self._json_dict(response)
        agents = data.get("agents", [])
        if isinstance(agents, list):
            return [cast(dict[str, Any], a) for a in agents if isinstance(a, dict)]
        return []

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        """Get agent details"""
        url = f"{self.base_url}/api/v2/agents/{agent_id}"
        response = httpx.get(url, headers=self._get_headers())
        response.raise_for_status()
        return self._json_dict(response)

    def delete_agent(self, agent_id: str) -> dict[str, Any]:
        """Delete agent"""
        url = f"{self.base_url}/api/v2/agents/{agent_id}"
        response = httpx.delete(url, headers=self._get_headers())
        response.raise_for_status()
        return self._json_dict(response)

    # Session Management

    def activate_agent(self, agent_id: str, duration_hours: int = 6) -> dict[str, Any]:
        """Activate agent session"""
        url = f"{self.base_url}/api/v2/agents/{agent_id}/activate"
        params: dict[str, Any] = {"duration_hours": duration_hours}
        response = httpx.post(url, params=params, headers=self._get_headers())
        response.raise_for_status()

        data = self._json_dict(response)
        self.session_token = data.get("session_token")
        self.agent_id = agent_id
        return data

    def deactivate_agent(self, agent_id: str) -> dict[str, Any]:
        """Deactivate agent session"""
        url = f"{self.base_url}/api/v2/agents/{agent_id}/deactivate"
        response = httpx.post(url, headers=self._get_headers())
        response.raise_for_status()

        data = self._json_dict(response)
        self.session_token = None
        self.agent_id = None
        return data

    def get_session_info(self) -> dict[str, Any]:
        """Get current session info"""
        url = f"{self.base_url}/api/v2/session/current"
        response = httpx.get(url, headers=self._get_headers())
        response.raise_for_status()
        return self._json_dict(response)

    def extend_session(self, agent_id: str, hours: int = 6) -> dict[str, Any]:
        """Extend session expiration"""
        url = f"{self.base_url}/api/v2/agents/{agent_id}/session/extend"
        params: dict[str, Any] = {"hours": hours}

        response = httpx.post(url, params=params, headers=self._get_headers())
        response.raise_for_status()
        return self._json_dict(response)

    # Memory Operations

    def remember(
        self,
        agent_id: str,
        memory_type: str,
        title: str,
        content: str,
        confidence: float = 0.8,
        tags: list[str] | None = None,
        source: str = "user",
        provenance: str | None = None,
    ) -> dict[str, Any]:
        """Store a memory"""
        url = f"{self.base_url}/api/v2/agents/{agent_id}/remember"
        params: dict[str, Any] = {
            "memory_type": memory_type,
            "title": title,
            "content": content,
            "confidence": confidence,
            "source": source,
        }
        if provenance:
            params["provenance"] = provenance
        if tags:
            params["tags"] = ",".join(tags)

        response = httpx.post(
            url, params=params, headers=self._get_headers(), timeout=30.0
        )
        response.raise_for_status()
        return self._json_dict(response)

    def batch_remember(
        self, agent_id: str, memories: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Store multiple memories in batch (up to 100)"""
        url = f"{self.base_url}/api/v2/agents/{agent_id}/batch-remember"
        payload = {"memories": memories}
        response = httpx.post(
            url, json=payload, headers=self._get_headers(), timeout=60.0
        )
        response.raise_for_status()
        return self._json_dict(response)

    def recall(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
        tags: list[str] | None = None,
        min_confidence: float | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> dict[str, Any]:
        """Search memories"""
        url = f"{self.base_url}/api/v2/agents/{agent_id}/recall"
        params: dict[str, Any] = {"query": query, "limit": limit}
        if memory_types:
            params["memory_types"] = ",".join(memory_types)
        if tags:
            params["tags"] = ",".join(tags)
        if min_confidence is not None:
            params["min_confidence"] = min_confidence
        if created_after:
            params["created_after"] = created_after.isoformat()
        if created_before:
            params["created_before"] = created_before.isoformat()

        response = httpx.get(
            url, params=params, headers=self._get_headers(), timeout=30.0
        )
        response.raise_for_status()
        return self._json_dict(response)

    def answer(self, agent_id: str, question: str, limit: int = 5) -> dict[str, Any]:
        """Answer a question using RAG"""
        url = f"{self.base_url}/api/v2/agents/{agent_id}/answer"
        params: dict[str, Any] = {"question": question, "limit": limit}

        response = httpx.post(url, params=params, headers=self._get_headers())
        response.raise_for_status()
        return self._json_dict(response)

    def recall_as_of(
        self,
        agent_id: str,
        query: str,
        as_of: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Point-in-time recall: What was true at this point in time?"""
        url = f"{self.base_url}/api/v2/agents/{agent_id}/recall/as-of"
        params: dict[str, Any] = {"query": query, "as_of": as_of, "limit": limit}
        if memory_types:
            params["memory_types"] = ",".join(memory_types)

        response = httpx.get(url, params=params, headers=self._get_headers())
        response.raise_for_status()
        return self._json_dict(response)

    def recall_changed_since(
        self,
        agent_id: str,
        since: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Differential retrieval: What changed since this date?"""
        url = f"{self.base_url}/api/v2/agents/{agent_id}/recall/changed-since"
        params: dict[str, Any] = {"since": since, "limit": limit}
        if memory_types:
            params["memory_types"] = ",".join(memory_types)

        response = httpx.get(url, params=params, headers=self._get_headers())
        response.raise_for_status()
        return self._json_dict(response)

    def recall_current(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Current state recall: What's currently true? (supersession-aware)"""
        url = f"{self.base_url}/api/v2/agents/{agent_id}/recall/current"
        params: dict[str, Any] = {"query": query, "limit": limit}
        if memory_types:
            params["memory_types"] = ",".join(memory_types)

        response = httpx.get(url, params=params, headers=self._get_headers())
        response.raise_for_status()
        return self._json_dict(response)

    # Health Check

    def health_check(self) -> dict[str, Any]:
        """Check if server is reachable"""
        url = f"{self.base_url}/health"
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        return self._json_dict(response)
