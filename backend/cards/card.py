from __future__ import annotations
from abc import ABC, abstractmethod  # Abstract Base Class tools
from backend.enums import CardType, TargetType
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.chess.board import Board
    from backend.player import Player

class Card(ABC):
    """
    Abstract Base Class representing a general card in the game.
    Each card has an ID, name, description, and two image versions (big and small).
    Concrete subclasses (like SpellCard, CurseCard, etc.) must define their own card_type.
    """

    def __init__(self, id: str, name: str, description: str, big_img: str, small_img: str):
        self.id = id
        self.name = name
        self.description = description
        self.big_img = big_img
        self.small_img = small_img

    # --- Abstract property to be implemented by subclasses ---
    @property
    @abstractmethod
    def card_type(self) -> CardType:
        """
        Returns the specific type of card.
        Must be implemented by subclasses.
        Example: return CardType.CURSE
        """
        pass

    # --- Getters ---
    def get_desc(self) -> str:
        """Return the card's description."""
        return self.description

    def get_big_img(self) -> str:
        """Return the large image URL or file path of the card."""
        return self.big_img

    def get_small_img(self) -> str:
        """Return the small image URL or file path of the card."""
        return self.small_img

    def get_id(self) -> str:
        """Return the unique card ID."""
        return self.id

    def get_name(self) -> str:
        """Return the card name."""
        return self.name

    # --- Dictionary for frontend/UI ---
    def to_dict(self, include_target: bool = False) -> dict:
        """
        Convert the card into a frontend-friendly dictionary.
        Optionally include target type if relevant (for playable cards).
        """
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cardType": self.card_type.name if self.card_type else None,
            "images": {
                "big": self.big_img,
                "small": self.small_img,
            }
        }

        # If the subclass defines a target_type property (e.g., affects ally/enemy)
        if include_target and hasattr(self, "target_type"):
            data["targetType"] = self.target_type.name if isinstance(self.target_type, TargetType) else str(self.target_type)

        return data

# ============================================================================
# CONCRETE CARD IMPLEMENTATIONS
# ============================================================================

class Mine(Card):
    """
    Hidden: Mine - Places a mine on a random tile on the board.
    Any friendly piece within 1 tile reveals its location.
    Explodes when landed on, capturing all pieces within 1 tile (except king).
    Auto-detonates after 4 turns if not triggered.
    """
    
    def __init__(self):
        super().__init__(id="mine", name="Mine", description="Placeholder", big_img="static/example_big.png", small_img="static/example_small.png")
    
    @property
    def card_type(self) -> CardType:
        return CardType.HIDDEN
    
    def can_play(self, board: Board, player: Player) -> bool:
        # Can always play mine if you have it
        return True
    
    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        # TODO: Implement mine placement logic
        # - Find random tile > 1 tile away from all pieces
        # - Register mine in board state with 4-turn timer
        # - Set up proximity reveal logic
        return True, "Mine placed (effect not yet implemented)"


from backend.cards.card import Card
from backend.enums import CardType, Color
from backend.chess.coordinate import Coordinate
from backend.chess.piece import Pawn
import random


class ForbiddenLands(Card):
    """
    Hidden: Forbidden Lands – Expands the board by adding a 'forbidden ring' around it.
    Rules:
      - Activates DMZ (10x10 board).
      - Marks outermost squares as 'forbidden'.
      - Any piece inside Forbidden Lands cannot be captured.
      - Kings cannot enter Forbidden Lands.
      - Pieces leaving the zone cannot capture afterward.
      - Playing again while active spawns a Pawn in your back forbidden rank.
    """

    def __init__(self):
        super().__init__(
            id="forbidden_lands",
            name="Forbidden Lands",
            description=(
                "Creates a protected ring of tiles where pieces cannot be captured. "
                "Kings cannot enter, and playing again summons a pawn within your back rank."
            ),
            big_img="static/cards/forbidden_lands_big.png",
            small_img="static/cards/forbidden_lands_small.png"
        )

    @property
    def card_type(self) -> CardType:
        return CardType.HIDDEN

    def can_play(self, board, player) -> bool:
        """Card can always be played (no direct target required)."""
        return True

    def apply_effect(self, board, player, target_data: dict) -> tuple[bool, str]:
        """
        Applies Forbidden Lands effect to the board.
        If already active, summons a pawn in player's back forbidden rank.
        """
        # Case 1: First play → activate forbidden ring
        if not board.forbidden_active:
            board.activate_forbidden_lands()

            # Reset flags for pieces
            for piece in board.squares.values():
                piece.has_left_forbidden = False

            return True, "Forbidden Lands activated — the outer ring is now protected."

        # Case 2: Already active → summon pawn in player's back forbidden rank
        forbidden_back_rank = 0 if player.color == Color.WHITE else 9
        possible_tiles = [
            coord for coord in board.forbidden_positions
            if coord.rank == forbidden_back_rank and board.is_empty(coord)
        ]

        if not possible_tiles:
            return False, "No available space to summon a pawn in the Forbidden Lands."

        spawn_square = random.choice(possible_tiles)
        pawn_id = f"{player.color.name[0].lower()}F{len(board.squares)}"
        board.squares[spawn_square] = Pawn(pawn_id, player.color)

        return True, f"A pawn has been summoned in the Forbidden Lands at {spawn_square.to_algebraic()}."

class EyeForAnEye(Card):
    """
    Eye for an Eye - Marks a friendly and opposing piece for 5 turns.
    Capturing a marked piece allows for another turn immediately.
    """
    
    def __init__(self):
        super().__init__(id="eye_for_an_eye", name="Eye for an Eye", description="Placeholder", big_img="static/example_big.png", small_img="static/example_small.png")
    
    @property
    def card_type(self) -> CardType:
        return CardType.CURSE
    
    def can_play(self, board: Board, player: Player) -> bool:
        # Need at least one friendly and one enemy piece to mark
        return True  # Simplified for now
    
    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        # TODO: Implement marking logic
        # - Expect target_data to contain friendly_piece and enemy_piece coordinates
        # - Mark both pieces for 5 turns
        # - Set up capture trigger for extra turn
        return True, "Eye for an Eye marked pieces (effect not yet implemented)"


class SummonPeon(Card):
    """
    Summon Peon - Summons a friendly peon on a random square.
    Peons act like pawns but cannot promote.
    Upon reaching furthest rank, unlock backward movement/attacks.
    """
    
    def __init__(self):
        super().__init__(id="summon_peon", name="Summon Peon", description="Placeholder", big_img="static/example_big.png", small_img="static/example_small.png")
    
    @property
    def card_type(self) -> CardType:
        return CardType.SUMMON
    
    def can_play(self, board: Board, player: Player) -> bool:
        # Can play if there's room on the board
        return True
    
    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        # TODO: Implement peon summoning
        # - Find random safe square (bias for not attacking/being attacked)
        # - Cannot spawn on enemy back rank
        # - If under checkmate threat, try to block
        # - Create and place Peon piece
        return True, "Peon summoned (effect not yet implemented)"


class TransformToScout(Card):
    """
    Pawn: Scout - Select one pawn to transform into a scout.
    Scouts move like a queen but only 5 squares in each direction.
    Cannot capture; instead marks enemy pieces.
    Capturing marked piece grants extra turn.
    """
    
    def __init__(self):
        super().__init__(
            id="pawn_scout", 
            name="Pawn: Scout", 
            description="Transform a pawn into a scout. Scouts move 5 squares in any direction and can mark enemy pieces.",
            big_img="static/example_big.png", 
            small_img="static/example_small.png"
        )
        self.target_type = TargetType.PIECE
    
    @property
    def card_type(self) -> CardType:
        return CardType.TRANSFORM
    
    def can_play(self, board: Board, player: Player) -> bool:
        """Check if player has any pawns to transform"""
        from backend.enums import PieceType
        
        # Check if player has any pawns on the board
        for coord, piece in board.squares.items():
            if piece.color == player.color and piece.type == PieceType.PAWN:
                return True
        return False
    
    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        """Transform a pawn at target coordinate into a scout"""
        from backend.chess.coordinate import Coordinate
        from backend.chess.piece import Scout
        from backend.enums import PieceType
        
        # Parse target coordinate
        target_square = target_data.get("target")
        if not target_square:
            return False, "No target square provided"
        
        try:
            # Parse algebraic notation (e.g., "e3")
            target_coord = Coordinate.from_algebraic(target_square)
        except Exception as e:
            return False, f"Invalid coordinate: {target_square}"
        
        # Check if there's a piece at target
        piece = board.piece_at_coord(target_coord)
        if not piece:
            return False, f"No piece at {target_square}"
        
        # Verify it's the player's pawn
        if piece.color != player.color:
            return False, "That's not your piece"
        
        if piece.type != PieceType.PAWN:
            return False, "Can only transform pawns into scouts"
        
        # Create the scout with a unique ID
        scout_id = f"scout_{player.color.value}_{target_coord.to_algebraic()}"
        scout = Scout(scout_id, player.color)
        
        # Replace the pawn with the scout
        board.squares[target_coord] = scout
        
        return True, f"Pawn at {target_square} transformed into Scout!"

class TransformToHeadhunter(Card):
    """
    Knight: Headhunter - Select a knight to transform into a headhunter.
    Headhunters move like a king but can attack 3 squares in front of them.
    Value of 5.
    """
    
    def __init__(self):
        super().__init__(id="knight_headhunter", name="Knight: Headhunter", description="Placeholder", big_img="static/example_big.png", small_img="static/example_small.png")
    
    @property
    def card_type(self) -> CardType:
        return CardType.TRANSFORM
    
    def can_play(self, board: Board, player: Player) -> bool:
        # Need at least one knight to transform
        # TODO: Check if player has any knights
        return True
    
    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        # TODO: Implement knight -> headhunter transformation
        # - Expect target_data to contain knight coordinate
        # - Remove knight, create Headhunter piece at same location
        # - If no knight available, allow material sacrifice to summon
        return True, "Knight transformed to Headhunter (effect not yet implemented)"


class TransformToWarlock(Card):
    """
    Bishop: Warlock - Select any bishop to turn into a warlock.
    Warlocks can move to any same-colored tile in 3 tile radius with clear line.
    Can move 1 tile backward to change tile color.
    When effigy destroyed, gains knight + rook movement for 2 turns.
    Value of 5.
    """
    
    def __init__(self):
        super().__init__(id="bishop_warlock", name="Bishop: Warlock", description="Placeholder", big_img="static/example_big.png", small_img="static/example_small.png")
    
    @property
    def card_type(self) -> CardType:
        return CardType.TRANSFORM
    
    def can_play(self, board: Board, player: Player) -> bool:
        # Need at least one bishop to transform
        # TODO: Check if player has any bishops
        return True
    
    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        # TODO: Implement bishop -> warlock transformation
        # - Expect target_data to contain bishop coordinate
        # - Remove bishop, create Warlock piece at same location
        # - If no bishop available, allow material sacrifice to summon
        return True, "Bishop transformed to Warlock (effect not yet implemented)"


# ============================================================================
# CARD REGISTRY - Map card IDs to card classes
# ============================================================================

CARD_REGISTRY = {
    "mine": Mine,
    "eye_for_an_eye": EyeForAnEye,
    "summon_peon": SummonPeon,
    "pawn_scout": TransformToScout,
    "knight_headhunter": TransformToHeadhunter,
    "bishop_warlock": TransformToWarlock,
}


def create_card_by_id(card_id: str) -> Optional[Card]:
    """
    Factory function to create a card instance by its ID.
    Returns None if card_id is not found in registry.
    """
    card_class = CARD_REGISTRY.get(card_id)
    if card_class:
        return card_class()
    return None