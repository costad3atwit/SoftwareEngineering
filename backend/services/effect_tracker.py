"""
Effect Tracker - Centralized system for managing turn-based countdown effects

This module provides a unified way to track all timed effects in the game,
including:
- Piece empowerment (Warlock empowered for 2 turns)
- Card effects with durations (Mine auto-detonation after 4 turns)
- Piece marks (Eye for an Eye - 5 turns)
- Hidden effects (Pawn Bomb - 8 turns, reduced to 4)
- Tile effects (Glue - 2 turns immobilization)

Instead of each piece/card maintaining its own countdown, this tracker
uses the GameState's turn counter as the source of truth.
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from backend.enums import EffectType


@dataclass
class Effect:
    """Represents a single timed effect in the game"""
    
    effect_id: str  # Unique identifier for this effect instance
    effect_type: EffectType
    start_turn: int  # Turn number when effect was created
    duration: int  # How many turns the effect lasts
    target: Any  # What the effect applies to (piece_id, coordinate, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Extra info
    on_expire: Optional[Callable] = None  # Callback when effect ends
    on_tick: Optional[Callable] = None  # Callback each turn
    
    def is_expired(self, current_turn: int) -> bool:
        """Check if this effect has expired"""
        return current_turn >= self.start_turn + self.duration
    
    def turns_remaining(self, current_turn: int) -> int:
        """Calculate how many turns are left"""
        remaining = (self.start_turn + self.duration) - current_turn
        return max(0, remaining)


class EffectTracker:
    """
    Centralized tracker for all turn-based effects in the game.
    
    Usage:
        # In GameState.__init__:
        self.effect_tracker = EffectTracker()
        
        # When Warlock gets empowered:
        effect_tracker.add_effect(
            effect_type=EffectType.PIECE_EMPOWERMENT,
            start_turn=game_state.fullmove_number,
            duration=2,
            target=warlock.id
        )
        
        # At end of turn:
        expired = effect_tracker.process_turn(game_state.fullmove_number)
    """
    
    def __init__(self):
        self.effects: Dict[str, Effect] = {}
        self._next_id = 0
    
    def add_effect(
        self,
        effect_type: EffectType,
        start_turn: int,
        duration: int,
        target: Any,
        metadata: Optional[Dict[str, Any]] = None,
        on_expire: Optional[Callable] = None,
        on_tick: Optional[Callable] = None
    ) -> str:
        """
        Add a new effect to track.
        
        Args:
            effect_type: Type of effect
            start_turn: Turn number when effect starts
            duration: How many turns it lasts
            target: What it affects (piece_id, coordinate tuple, etc.)
            metadata: Optional extra data
            on_expire: Optional callback when effect expires
            on_tick: Optional callback each turn
            
        Returns:
            effect_id: Unique identifier for this effect
        """
        effect_id = f"{effect_type.value}_{self._next_id}"
        self._next_id += 1
        
        self.effects[effect_id] = Effect(
            effect_id=effect_id,
            effect_type=effect_type,
            start_turn=start_turn,
            duration=duration,
            target=target,
            metadata=metadata or {},
            on_expire=on_expire,
            on_tick=on_tick
        )
        
        return effect_id
    
    def remove_effect(self, effect_id: str) -> bool:
        """Remove an effect by ID. Returns True if found and removed."""
        if effect_id in self.effects:
            del self.effects[effect_id]
            return True
        return False
    
    def get_effect(self, effect_id: str) -> Optional[Effect]:
        """Get an effect by ID"""
        return self.effects.get(effect_id)
    
    def get_effects_by_type(self, effect_type: EffectType) -> List[Effect]:
        """Get all effects of a specific type"""
        return [e for e in self.effects.values() if e.effect_type == effect_type]
    
    def get_effects_by_target(self, target: Any) -> List[Effect]:
        """Get all effects affecting a specific target"""
        return [e for e in self.effects.values() if e.target == target]
    
    def has_effect(self, effect_type: EffectType, target: Any) -> bool:
        """Check if a specific target has an effect of this type"""
        return any(
            e.effect_type == effect_type and e.target == target
            for e in self.effects.values()
        )
    
    def process_turn(self, current_turn: int) -> List[Effect]:
        """
        Process all effects for the current turn.
        Calls on_tick callbacks and removes expired effects.
        
        Args:
            current_turn: Current turn number from GameState.fullmove_number
            
        Returns:
            List of effects that expired this turn
        """
        expired_effects = []
        
        for effect_id, effect in list(self.effects.items()):
            # Call tick callback if exists
            if effect.on_tick:
                effect.on_tick(effect, current_turn)
            
            # Check if expired
            if effect.is_expired(current_turn):
                expired_effects.append(effect)
                
                # Call expiration callback if exists
                if effect.on_expire:
                    effect.on_expire(effect)
                
                # Remove from tracker
                del self.effects[effect_id]
        
        return expired_effects
    
    def modify_duration(self, effect_id: str, new_duration: int) -> bool:
        """
        Modify the duration of an existing effect.
        Useful for effects like Pawn Bomb that shorten when moved.
        
        Returns True if effect found and modified.
        """
        if effect_id in self.effects:
            self.effects[effect_id].duration = new_duration
            return True
        return False
    
    def to_dict(self, current_turn: int) -> Dict:
        """Serialize all effects for transmission to frontend"""
        return {
            effect_id: {
                "type": effect.effect_type.value,
                "target": str(effect.target),
                "turns_remaining": effect.turns_remaining(current_turn),
                "metadata": effect.metadata
            }
            for effect_id, effect in self.effects.items()
        }
    
    def clear_all(self):
        """Remove all effects (useful for game end)"""
        self.effects.clear()


# ============================================================================
# HELPER FUNCTIONS for common effect patterns
# ============================================================================

# THIS IS DEAD CODE - DO NOT CONTINUE ADDING HELPERS. INSTEAD USE add_effect() 
# DIRECTLY WITHIN CARD/PIECE LOGIC TO ADD EFFECTS LIKE IS ALREADY BEING DONE.

# WILL DELETE AFTER DISCUSSING WITH TEAM.



# def create_empowerment_effect(
#     tracker: EffectTracker,
#     piece_id: str,
#     current_turn: int,
#     piece_ref: Any = None
# ) -> str:
#     """
#     Helper to create a Warlock empowerment effect.
    
#     Args:
#         tracker: The EffectTracker instance
#         piece_id: ID of the piece being empowered
#         current_turn: Current turn number
#         piece_ref: Optional reference to the actual piece object
        
#     Returns:
#         effect_id
#     """
#     def on_expire(effect):
#         # Set empowered flag to False when expired
#         if piece_ref:
#             piece_ref.empowered = False
    
#     return tracker.add_effect(
#         effect_type=EffectType.PIECE_EMPOWERMENT,
#         start_turn=current_turn,
#         duration=2,
#         target=piece_id,
#         metadata={"piece_id": piece_id},
#         on_expire=on_expire
#     )


# def create_mark_effect(
#     tracker: EffectTracker,
#     piece_id: str,
#     current_turn: int,
#     duration: int = 5
# ) -> str:
#     """
#     Helper to create a piece mark effect (Eye for an Eye).
    
#     Args:
#         tracker: The EffectTracker instance
#         piece_id: ID of the piece being marked
#         current_turn: Current turn number
#         duration: How many turns the mark lasts (default 5)
        
#     Returns:
#         effect_id
#     """
#     return tracker.add_effect(
#         effect_type=EffectType.PIECE_MARK,
#         start_turn=current_turn,
#         duration=duration,
#         target=piece_id,
#         metadata={"piece_id": piece_id}
#     )


# def create_mine_effect(
#     tracker: EffectTracker,
#     coordinate: tuple,
#     current_turn: int,
#     on_detonate: Optional[Callable] = None
# ) -> str:
#     """
#     Helper to create a mine effect (4-turn auto-detonation).
    
#     Args:
#         tracker: The EffectTracker instance
#         coordinate: (file, rank) tuple of mine location
#         current_turn: Current turn number
#         on_detonate: Callback to execute when mine detonates
        
#     Returns:
#         effect_id
#     """
#     return tracker.add_effect(
#         effect_type=EffectType.MINE,
#         start_turn=current_turn,
#         duration=4,
#         target=coordinate,
#         metadata={"coordinate": coordinate},
#         on_expire=on_detonate
#     )


# def create_pawn_bomb_effect(
#     tracker: EffectTracker,
#     piece_id: str,
#     current_turn: int,
#     on_detonate: Optional[Callable] = None
# ) -> str:
#     """
#     Helper to create a pawn bomb effect (8-turn fuse, shortened to 4 on move).
    
#     Args:
#         tracker: The EffectTracker instance
#         piece_id: ID of the pawn that is a bomb
#         current_turn: Current turn number
#         on_detonate: Callback when bomb explodes
        
#     Returns:
#         effect_id
#     """
#     return tracker.add_effect(
#         effect_type=EffectType.PAWN_BOMB,
#         start_turn=current_turn,
#         duration=8,
#         target=piece_id,
#         metadata={"piece_id": piece_id, "has_moved": False},
#         on_expire=on_detonate
#     )


# def create_glue_effect(
#     tracker: EffectTracker,
#     coordinate: tuple,
#     current_turn: int
# ) -> str:
#     """
#     Helper to create a glue trap effect (2 turns immobilization).
    
#     Args:
#         tracker: The EffectTracker instance
#         coordinate: (file, rank) tuple of glued tile
#         current_turn: Current turn number
        
#     Returns:
#         effect_id
#     """
#     return tracker.add_effect(
#         effect_type=EffectType.GLUE_TRAP,
#         start_turn=current_turn,
#         duration=2,
#         target=coordinate,
#         metadata={"coordinate": coordinate}
#     )

