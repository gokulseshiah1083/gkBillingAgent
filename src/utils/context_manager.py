"""Context Manager

Minimal session context store for development.
"""

from __future__ import annotations

from typing import Any, Dict
import asyncio


class ContextManager:
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def update_context(self, session_id: str, query_id: str, parsed_query: Any, response: Any) -> None:
        async with self._lock:
            sess = self._sessions.setdefault(session_id, {"history": []})
            sess["history"].append(
                {
                    "query_id": query_id,
                    "parsed_query": parsed_query,
                    "response": response,
                }
            )
