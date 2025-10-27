# backend/tutorial/game_tutorial.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any


# ---------- Errors ----------
class TutorialError(Exception): ...
class TutorialCompleted(TutorialError): ...
class StepOutOfRange(TutorialError): ...
class InvalidAction(TutorialError): ...


# ---------- Models ----------
@dataclass(frozen=True)
class TutorialStep:
    """
    A single tutorial step. If required_action is set, the client must emit that
    action before this step can be marked complete and we can advance.
    """
    id: str
    text: str
    required_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "text": self.text, "requiredAction": self.required_action}


@dataclass
class TutorialProgress:
    """
    Per-user tutorial progress and event history.
    """
    user_id: str
    current_index: int = 0
    completed: bool = False
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    history: List[Dict[str, Any]] = field(default_factory=list)

    def mark_updated(self, event: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self.updated_at = datetime.now(timezone.utc)
        entry = {"ts": self.updated_at.isoformat(), "event": event}
        if extra:
            entry.update(extra)
        self.history.append(entry)

    def to_dict(self, steps: List[TutorialStep]) -> Dict[str, Any]:
        current_step = steps[self.current_index] if not self.completed and 0 <= self.current_index < len(steps) else None
        return {
            "userId": self.user_id,
            "currentIndex": self.current_index,
            "completed": self.completed,
            "startedAt": self.started_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "currentStep": current_step.to_dict() if current_step else None,
            "totalSteps": len(steps),
            "history": self.history[-50:],  # keep payload light; trim if needed
        }


# ---------- Defaults (replace with DB/config as needed) ----------
def default_steps() -> List[TutorialStep]:
    """
    Replace this with a DB/config fetch or feature-flagged set.
    Keep IDs stable for analytics and history joins.
    """
    return [
        TutorialStep(id="T-001", text="Welcome! This tutorial shows how to move pieces and use cards."),
        TutorialStep(id="T-002", text="Try moving any piece. One legal chess move per turn.", required_action="move_any_piece"),
        TutorialStep(id="T-003", text="Open your card hand to see available cards.", required_action="open_hand"),
        TutorialStep(id="T-004", text="Play a card that targets any piece.", required_action="play_card"),
        TutorialStep(id="T-005", text="Great! End your turn to proceed.", required_action="end_turn"),
        TutorialStep(id="T-006", text="You’re ready. Win by checkmating the enemy king!", required_action=None),
    ]


# ---------- Engine ----------
class TutorialEngine:
    """
    Stateless logic over (steps, progress). Persist progress externally.
    """

    def __init__(self, steps: Optional[List[TutorialStep]] = None):
        self._steps = steps or default_steps()
        if not self._steps:
            raise TutorialError("Tutorial steps cannot be empty.")

    # --- Read helpers ---
    @property
    def steps(self) -> List[TutorialStep]:
        return self._steps

    def step_at(self, index: int) -> TutorialStep:
        if index < 0 or index >= len(self._steps):
            raise StepOutOfRange(f"Index {index} is out of range.")
        return self._steps[index]

    def current_step(self, progress: TutorialProgress) -> Optional[TutorialStep]:
        if progress.completed:
            return None
        if 0 <= progress.current_index < len(self._steps):
            return self._steps[progress.current_index]
        return None

    # --- Core state transitions ---
    def record_client_action(self, progress: TutorialProgress, action: str, payload: Optional[Dict[str, Any]] = None) -> TutorialProgress:
        """
        Log a client action (e.g., 'open_hand', 'move_any_piece'), and advance if it satisfies the current step.
        """
        step = self.current_step(progress)
        progress.mark_updated("client_action", {"action": action, "payload": payload or {}, "stepId": step.id if step else None})

        if progress.completed:
            # Already finished; just log and return.
            return progress

        if not step:
            # Out of range or steps misaligned: finalize to avoid stuck states.
            return self._complete(progress, reason="no_current_step")

        if step.required_action is None:
            # This step doesn't gate on an action; allow manual advance or auto-advance.
            return progress

        if action == step.required_action:
            # Satisfies requirement: advance to next step
            return self._advance(progress)
        else:
            # Not the required action; keep state, still logged for analytics
            return progress

    def advance(self, progress: TutorialProgress) -> TutorialProgress:
        """Manually advance (e.g., 'Next' button) if step has no required_action."""
        step = self.current_step(progress)
        if progress.completed:
            raise TutorialCompleted("Tutorial already completed.")
        if not step:
            return self._complete(progress, reason="no_current_step_manual")
        if step.required_action:
            # Guard: can't skip gated steps with advance()
            raise InvalidAction(f"Step '{step.id}' requires action '{step.required_action}' before advancing.")
        return self._advance(progress)

    def skip(self, progress: TutorialProgress) -> TutorialProgress:
        """Skip the current step (admin/debug or user-allowed skip)."""
        if progress.completed:
            return progress
        return self._advance(progress, event="skip")

    def back(self, progress: TutorialProgress) -> TutorialProgress:
        """Go back one step (non-negative)."""
        if progress.completed:
            # If completed, back moves to last step
            progress.completed = False
            progress.current_index = max(0, len(self._steps) - 1)
            progress.mark_updated("back_from_completed")
            return progress

        new_index = max(0, progress.current_index - 1)
        progress.current_index = new_index
        progress.mark_updated("back")
        return progress

    def restart(self, progress: TutorialProgress) -> TutorialProgress:
        """Reset tutorial for the user."""
        progress.completed = False
        progress.current_index = 0
        progress.started_at = datetime.now(timezone.utc)
        progress.mark_updated("restart")
        return progress

    # --- Private helpers ---
    def _advance(self, progress: TutorialProgress, event: str = "advance") -> TutorialProgress:
        next_index = progress.current_index + 1
        if next_index >= len(self._steps):
            return self._complete(progress, reason=event)
        progress.current_index = next_index
        progress.mark_updated(event, {"toIndex": next_index, "toStepId": self._steps[next_index].id})
        return progress

    def _complete(self, progress: TutorialProgress, reason: str = "complete") -> TutorialProgress:
        progress.completed = True
        progress.current_index = len(self._steps)  # point past the end
        progress.mark_updated("complete", {"reason": reason})
        return progress

    # --- Serialization for API/FE ---
    def payload(self, progress: TutorialProgress) -> Dict[str, Any]:
        """
        Compact payload for frontend consumption.
        """
        return progress.to_dict(self._steps)

    # --- Persistence hooks (wire to your DB layer) ---
    @staticmethod
    def serialize(progress: TutorialProgress) -> Dict[str, Any]:
        """Convert progress to a DB-storable dict (JSON-safe)."""
        d = asdict(progress)
        # Ensure datetimes serialize cleanly (as ISO strings)
        d["started_at"] = progress.started_at.isoformat()
        d["updated_at"] = progress.updated_at.isoformat()
        return d

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> TutorialProgress:
        """Recreate progress from DB dict."""
        return TutorialProgress(
            user_id=data["user_id"],
            current_index=int(data.get("current_index", 0)),
            completed=bool(data.get("completed", False)),
            started_at=datetime.fromisoformat(data.get("started_at")).astimezone(timezone.utc)
                if data.get("started_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data.get("updated_at")).astimezone(timezone.utc)
                if data.get("updated_at") else datetime.now(timezone.utc),
            history=list(data.get("history", [])),
        )
