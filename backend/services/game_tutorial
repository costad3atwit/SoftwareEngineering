# backend/tutorial/game_tutorial.py
from __future__ import annotations

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


# ---------- Models ----------
@dataclass(frozen=True)
class TutorialStep:
    id: str
    text: str
    # Optional: gate the step behind a required client action (move_pawn, open_hand, play_card, etc.)
    required_action: Optional[str] = None


@dataclass
class TutorialProgress:
    user_id: str
    current_index: int = 0
    completed: bool = False
    started_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    # Optional: record per-step timestamps / events
    history: List[Dict[str, Any]] = field(default_factory=list)


# ---------- Defaults (replace/load from DB/config later) ----------
def default_steps() -> List[TutorialStep]:
    # TODO: fetch from DB or feature-flag config
    return [
        TutorialStep(id="T-001", text="Welcome! This tutorial shows moves & cards."),
        TutorialStep(id="T-002", text="Move pieces: one legal chess move per turn.", required_action="move_any_piece"),
        TutorialStep(id="T-003", text="Open you
