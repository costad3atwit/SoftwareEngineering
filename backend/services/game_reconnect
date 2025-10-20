# backend/services/game_reconnect.py
from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4

# ---------- Session + State Models ----------

class GameSession:
    """Represents an active player session with snapshot + reconnect token."""

    def __init__(self, user_id: str, game_id: str) -> None:
        self.user_id = user_id
        self.game_id = game_id
        self.session_token: str = str(uuid4())
        self.last_action_at: datetime = datetime.utcnow()
        self.snapshot: Dict[str, Any] = {}  # Stores latest known board, hand, timers, etc.
        self.connected: bool = True

    def update_snapshot(self, state: Dict[str, Any]) -> None:
        """Store the latest authoritative game state for reconnect."""
        self.snapshot = state
        self.last_action_at = datetime.utcnow()

    def mark_disconnected(self) -> None:
        self.connected = False
        self.last_action_at = datetime.utcnow()

    def mark_reconnected(self) -> None:
        self.connected = True
        self.last_act_
