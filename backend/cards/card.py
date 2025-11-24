from __future__ import annotations
from abc import ABC, abstractmethod  # Abstract Base Class tools
from typing import List, Optional, Tuple, Dict, Any, TYPE_CHECKING
from backend.enums import CardType, Color, PieceType, EffectType, TargetType
from backend.services.effect_tracker import EffectType
from backend.chess.coordinate import Coordinate
from backend.chess.piece import Pawn, Scout, HeadHunter, Warlock, DarkLord, Queen, Cleric, King, Peon, Piece, Knight, Bishop, Rook, Witch, Effigy, Barricade
from backend.chess.board import Board
from backend.services.effect_tracker import EffectTracker
import random


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
    
    def handle_query(self, board: 'Board', player: 'Player', action: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle queries from the frontend about this card.
        Default implementation returns None. Cards that need pre-play queries
        should override this method.
        
        Args:
            board: Current board state
            player: The player making the query
            action: Type of query (e.g., "get_options", "validate_target")
            data: Query-specific data
        
        Returns:
            Query response, or None if not supported
        """
        return None

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
    Dismantles after 4 turns if not triggered.
    """
    
    def __init__(self):
        super().__init__(
            id="mine",
            name="Mine",
            description=(
                "Places a hidden mine on a random empty square. "
                "Explodes when any piece steps on it, capturing all nearby "
                "pieces except kings. Dismantles after 4 turns if untouched."
            ),
            big_img="static/cards/mine_big.png",
            small_img="static/cards/mine_small.png"
        )    
    @property
    def card_type(self) -> CardType:
        return CardType.HIDDEN
    
    def can_play(self, board: Board, player: Player) -> bool:
        """Can always be played if at least one empty square exists."""
        empty_tiles = [c for c in self._all_possible_coords(board) if board.is_empty(c)]
        return len(empty_tiles) > 0
    
    def _all_possible_coords(self, board: Board):
        """Helper to get all valid coordinates within bounds."""
        max_file = 9 if board.dmzActive else 8
        min_file = 0 if board.dmzActive else 1
        coords = []
        for f in range(min_file, max_file + 1):
            for r in range(min_file, max_file + 1):
                coord = Coordinate(f, r)
                if board.is_in_bounds(coord):
                    coords.append(coord)
        return coords
    
    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Places a mine on a random empty tile far enough from all pieces.
        Registers 4-turn auto-detonation with effect tracker.
        """

        # Gather all empty tiles that are at least 2 away from all pieces
        possible_tiles = []
        for coord in self._all_possible_coords(board):
            if not board.is_empty(coord):
                continue

            # Check that it's >1 tile away from all existing pieces
            too_close = any(
                abs(coord.file - c.file) <= 1 and abs(coord.rank - c.rank) <= 1
                for c in board.squares.keys()
            )
            if not too_close:
                possible_tiles.append(coord)

        if not possible_tiles:
            return False, "No suitable empty space to place a mine safely."

        chosen_tile = random.choice(possible_tiles)
        board.place_mine(chosen_tile, player.color)
        
        # Register auto-detonation effect with tracker
        if hasattr(board, 'game_state') and board.game_state:
            from backend.services.effect_tracker import EffectType
            def detonate_mine(effect):
                """Auto-detonation callback after 4 turns"""
                mine_coord = effect.metadata['coordinate']
                # Explode the mine - capture all pieces within 1 tile radius
                print(f"Mine at {mine_coord} auto-detonated after 4 turns!")
                board.detonate_mine(mine_coord)
            
            board.game_state.effect_tracker.add_effect(
                effect_type=EffectType.MINE,
                start_turn=board.game_state.fullmove_number,
                duration=4,
                target=chosen_tile,
                metadata={
                    'coordinate': chosen_tile,
                    'owner_color': player.color.name
                },
                on_expire=detonate_mine
            )

        return True, f"Mine placed on a hidden tile. It will auto-detonate after 4 turns if untouched."

class Glue(Card):
    """
    Hidden: Glue — Places a random glue tile.
    Multiple glue tiles can exist simultaneously.
    Any piece stepping on glue becomes immobilized for 2 turns.
    Capturing a glued piece glues the captor for 2 turns.
    Each glue tile lasts 4 turns if unused.
    """

    def __init__(self):
        super().__init__(
            id="glue",
            name="Glue",
            description=(
                "One random tile becomes glued. Any piece stepping on it becomes stuck for "
                "2 turns. Capturing a glued piece glues the captor for 2 turns. "
                "Glue tiles dry after 4 turns. Multiple glues may exist at once."
            ),
            big_img="static/cards/glue_big.png",
            small_img="static/cards/glue_small.png"
        )

    @property
    def card_type(self) -> CardType:
        return CardType.HIDDEN

    def can_play(self, board: Board, player: Player) -> bool:
        empty_tiles = [c for c in self._all_possible_coords(board) if board.is_empty(c)]
        return len(empty_tiles) > 0

    def _all_possible_coords(self, board: Board):
        max_file = 9 if board.dmzActive else 8
        min_file = 0 if board.dmzActive else 1
        coords = []
        for f in range(min_file, max_file + 1):
            for r in range(min_file, max_file + 1):
                c = Coordinate(f, r)
                if board.is_in_bounds(c):
                    coords.append(c)
        return coords

    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        candidates = []
        for coord in self._all_possible_coords(board):
            if not board.is_empty(coord):
                continue
            too_close = any(
                abs(coord.file - c.file) <= 1 and abs(coord.rank - c.rank) <= 1
                for c in board.squares.keys()
            )
            if not too_close:
                candidates.append(coord)

        if not candidates:
            return False, "No suitable space to place a glue tile."

        chosen = random.choice(candidates)
        board.place_glue(chosen, player.color)
        
        # Register glue tile expiration after 4 turns
        if hasattr(board, 'game_state') and board.game_state:
            from backend.services.effect_tracker import EffectType
            def dry_glue(effect):
                """Glue dries after 4 turns"""
                glue_coord = effect.metadata['coordinate']
                print(f"Glue at {glue_coord} has dried after 4 turns.")
                board.remove_glue(glue_coord)
            
            board.game_state.effect_tracker.add_effect(
                effect_type=EffectType.GLUE_TRAP,
                start_turn=board.game_state.fullmove_number,
                duration=4,
                target=chosen,
                metadata={
                    'coordinate': chosen,
                    'owner_color': player.color.name
                },
                on_expire=dry_glue
            )

        return True, "A glue trap has been placed. It will dry in 4 turns if unused."
    
    @staticmethod
    def immobilize_piece(board: Board, piece_id: str, game_state):
        """
        Called when a piece steps on glue - immobilizes for 2 turns.
        """
        def release_piece(effect):
            """Release piece after 2 turns"""
            print(f"Piece {effect.target} is no longer glued.")
        from backend.services.effect_tracker import EffectType

        game_state.effect_tracker.add_effect(
            effect_type=EffectType.PIECE_IMMOBILIZED,
            start_turn=game_state.fullmove_number,
            duration=2,
            target=piece_id,
            metadata={'piece_id': piece_id},
            on_expire=release_piece
        )

class Insurance(Card):
    """
    Hidden: Insurance
    -----------------
    Select a friendly piece valued > 1. When it is captured:
      • Spawn ceil(value/2) glued Peons on random empty squares.
      • Peons cannot spawn in a way that would place the enemy king in check once unglued.
      • Peons are glued for 3 turns.
    """

    def __init__(self):
        super().__init__(
            id="insurance",
            name="Insurance",
            description=(
                "Select a piece to insure. When it is captured, summon glued Peons "
                "equal to half its value (rounded up). Peons cannot spawn in positions "
                "that would check the enemy king once unglued."
            ),
            big_img="static/cards/insurance_big.png",
            small_img="static/cards/insurance_small.png"
        )
        self.target_type = TargetType.PIECE

    @property
    def card_type(self) -> CardType:
        return CardType.HIDDEN

    # ------------------------------------------------------------------
    # Player may only insure pieces worth > 1
    # ------------------------------------------------------------------
    def can_play(self, board: Board, player: Player) -> bool:
        for p in board.squares.values():
            if p.color == player.color and getattr(p, "value", 1) > 1:
                return True
        return False

    # ------------------------------------------------------------------
    # Helper: Find all empty tiles on the board
    # ------------------------------------------------------------------
    def _empty_tiles(self, board: Board) -> list[Coordinate]:
        return [
            coord for coord in board._all_board_coords()
            if board.is_empty(coord)
        ]

    # ------------------------------------------------------------------
    # Helper: ensure placing a Peon does NOT give check to enemy king
    # ------------------------------------------------------------------
    def _is_safe_spawn(self, board: Board, tile: Coordinate, color: Color) -> bool:
        enemy_color = Color.BLACK if color == Color.WHITE else Color.WHITE
        temp = board.clone()

        # place temporary peon
        temp.squares[tile] = Peon("TEMP_INSURANCE", color)

        # locate enemy king
        king_coord = None
        for c, p in temp.squares.items():
            if p.type == PieceType.KING and p.color == enemy_color:
                king_coord = c
                break

        if not king_coord:
            return False  # enemy king must exist

        # check if peon could capture king
        potential_caps = temp.squares[tile].get_legal_captures(temp, tile)
        return all(mv.to_sq != king_coord for mv in potential_caps)

    # ------------------------------------------------------------------
    # APPLY EFFECT
    # ------------------------------------------------------------------
    def apply_effect(
        self, board: Board, player: Player, target_data: Dict[str, Any]
    ) -> tuple[bool, str]:

        gs = board.game_state
        tracker = gs.effect_tracker
        color = player.color

        # ------------------------------------------
        # Validate selected target
        # ------------------------------------------
        algebraic = target_data.get("target")
        if not algebraic:
            return False, "You must select a piece to insure."

        try:
            chosen_coord = Coordinate.from_algebraic(algebraic)
        except:
            return False, "Invalid coordinate format."

        piece = board.piece_at_coord(chosen_coord)
        if not piece:
            return False, "No piece exists at the chosen square."

        if piece.color != color:
            return False, "You may only insure your own piece."

        if getattr(piece, "value", 1) <= 1:
            return False, "You may not insure pieces valued at 1."

        insured_id = piece.id
        spawn_count = (piece.value + 1) // 2  # half rounded up

        # ------------------------------------------
        # This function executes when insured piece is captured
        # ------------------------------------------
        def on_insured_captured(effect):
            empty_tiles = self._empty_tiles(board)
            random.shuffle(empty_tiles)

            spawned = 0

            for tile in empty_tiles:
                if spawned >= spawn_count:
                    break

                if not self._is_safe_spawn(board, tile, color):
                    continue

                # Create real Peon
                new_id = f"ins_{color.name.lower()}_{random.randint(10000,99999)}"
                peon = Peon(new_id, color)
                board.squares[tile] = peon

                # Give 3 turns of glue
                def _unglue(e):
                    # No need to handle anything special here
                    pass

                tracker.add_effect(
                    effect_type=EffectType.PIECE_IMMOBILIZED,
                    start_turn=gs.fullmove_number,
                    duration=3,
                    target=new_id,
                    metadata={"piece_id": new_id},
                    on_expire=_unglue
                )

                spawned += 1

            print(f"Insurance: spawned {spawned}/{spawn_count} glued Peons.")

        # ------------------------------------------
        # Monitor effect — triggers on piece death
        # ------------------------------------------
        def capture_monitor(effect, current_turn):
            # If insured piece is still alive, do nothing
            for p in board.squares.values():
                if p.id == insured_id:
                    return

            # The insured piece has been captured
            on_insured_captured(effect)
            tracker.remove_effect(effect.effect_id)

        # ------------------------------------------
        # Register the persistent insurance effect
        # ------------------------------------------
        effect_id = tracker.add_effect(
            effect_type=EffectType.CARD_ACTIVE,
            start_turn=gs.fullmove_number,
            duration=9999,        # persists until piece dies
            target=insured_id,
            metadata={"insured_piece": insured_id},
            on_tick=capture_monitor
        )

        return True, f"{piece.id} is now insured. {spawn_count} glued Peons will spawn if it is captured."

class AllSeeing(Card):
    """
    CURSE — All-Seeing
    --------------------------------------------------
    • Summons an Effigy on the farthest available NON-FORBIDDEN empty tile
      away from the enemy king.
    • While the Effigy exists, every 3 turns it marks ONE random enemy piece
      (non-effigy, non-king) for 1 turn.
    • When the Effigy is captured/removed, the effect ends immediately.
    • A player may only have ONE active All-Seeing effect.
    """

    def __init__(self):
        super().__init__(
            id="all_seeing",
            name="All-Seeing",
            description="Summons an Effigy far from the enemy king. Every 3 turns marks a random enemy piece for 1 turn.",
            big_img="static/cards/allseeing_big.png",
            small_img="static/cards/allseeing_small.png"
        )

    @property
    def card_type(self) -> CardType:
        return CardType.CURSE

    # =====================================================
    # --- CAN PLAY (Per-player restriction) --------------
    # =====================================================
    def can_play(self, board: Board, player: Player) -> bool:
        """
        A player may have ONE active All-Seeing effect.
        Opponent’s All-Seeing does NOT block this player.
        """

        # Check existing effigies
        for p in board.squares.values():
            if getattr(p, "is_effigy", False) and \
               p.effect_type == EffectType.ALL_SEEING and \
               p.color == player.color:
                return False

        # Check EffectTracker for this player's All-Seeing
        if hasattr(board, "game_state") and board.game_state:
            tracker = board.game_state.effect_tracker
            for eff in tracker.get_effects_by_type(EffectType.ALL_SEEING):
                if eff.metadata.get("owner") == player.color.name:
                    return False

        return True

    # =====================================================
    # --- Helper: find enemy king -------------------------
    # =====================================================
    def _find_enemy_king(self, board: Board, enemy_color: Color) -> Optional[Coordinate]:
        for coord, piece in board.squares.items():
            if piece.type == PieceType.KING and piece.color == enemy_color:
                return coord
        return None

    # =====================================================
    # --- Helper: find farthest legal placement tile ------
    # =====================================================
    def _find_farthest_tile(self, board: Board, king_coord: Coordinate) -> Optional[Coordinate]:
        farthest = None
        max_dist = -1

        for coord in board._all_board_coords():

            if not board.is_in_bounds(coord):
                continue
            if not board.is_empty(coord):
                continue
            if board.forbidden_active and board.is_forbidden(coord):
                continue

            dist = abs(coord.file - king_coord.file) + abs(coord.rank - king_coord.rank)
            if dist > max_dist:
                max_dist = dist
                farthest = coord

        return farthest

    # =====================================================
    # --- Helper: summon effigy ---------------------------
    # =====================================================
    def _summon_effigy(self, board: Board, coord: Coordinate, color: Color) -> Effigy:
        effigy_id = f"effigy_allseeing_{color.name.lower()}_{random.randint(10000,99999)}"
        effigy = Effigy(effigy_id, color, EffectType.ALL_SEEING)
        board.squares[coord] = effigy
        return effigy

    # =====================================================
    # --- Helper: mark enemy piece ------------------------
    # =====================================================
    def _mark_random_enemy(self, board: Board, enemy_color: Color, tracker: EffectTracker):
        # Filter real enemy pieces (skip effigies and kings)
        candidates = [
            p for p in board.squares.values()
            if p.color == enemy_color
            and not getattr(p, "is_effigy", False)
            and p.type != PieceType.KING
        ]

        if not candidates:
            return

        target = random.choice(candidates)
        target.marked = True

        # On expire (1 turn)
        def _unmark(effect):
            for piece in board.squares.values():
                if piece.id == effect.target:
                    piece.marked = False

        tracker.add_effect(
            effect_type=EffectType.PIECE_MARK,
            start_turn=board.game_state.fullmove_number,
            duration=1,
            target=target.id,
            metadata={"piece_id": target.id, "source": "all_seeing"},
            on_expire=_unmark
        )

    # =====================================================
    # ------------ APPLY EFFECT (MAIN) --------------------
    # =====================================================
    def apply_effect(
        self,
        board: Board,
        player: Player,
        target_data: Dict[str, Any]
    ) -> Tuple[bool, str]:

        if not hasattr(board, "game_state") or not board.game_state:
            return False, "No game state available."

        gs = board.game_state
        tracker = gs.effect_tracker
        color = player.color
        enemy_color = Color.BLACK if color == Color.WHITE else Color.WHITE

        # 1. Locate enemy king
        enemy_king_coord = self._find_enemy_king(board, enemy_color)
        if enemy_king_coord is None:
            return False, "Enemy king not found — cannot activate All-Seeing."

        # 2. Pick farthest tile
        effigy_coord = self._find_farthest_tile(board, enemy_king_coord)
        if effigy_coord is None:
            return False, "No available tile to place an All-Seeing effigy."

        # 3. Summon effigy
        effigy = self._summon_effigy(board, effigy_coord, color)

        # 4. Register effect logic
        start_turn = gs.fullmove_number

        def _tick(effect, current_turn):
            """
            Called each turn:
            • If effigy gone → end effect
            • Else every 3 turns → mark enemy piece
            """

            # Effigy no longer exists → end effect immediately
            if effigy.id not in [p.id for p in board.squares.values()]:
                tracker.remove_effect(effect.effect_id)
                if effect.on_expire:
                    effect.on_expire(effect)
                return

            turns_passed = current_turn - effect.start_turn

            # Mark enemy piece every 3 turns (excluding turn 0)
            if turns_passed > 0 and turns_passed % 3 == 0:
                self._mark_random_enemy(board, enemy_color, tracker)

        def _expire(effect):
            """
            When the All-Seeing effect ends,
            remove the effigy from the board if still present.
            """
            to_delete = None
            for coord, piece in board.squares.items():
                if piece.id == effigy.id:
                    to_delete = coord
                    break

            if to_delete:
                del board.squares[to_delete]

        # Register the ongoing effect
        eff_id = tracker.add_effect(
            effect_type=EffectType.ALL_SEEING,
            start_turn=start_turn,
            duration=9999,
            target=effigy.id,
            metadata={"owner": color.name},
            on_tick=_tick,
            on_expire=_expire
        )

        # Attach effect ID to the effigy (optional convenience)
        effigy.effect_tracker_id = eff_id

        return True, f"All-Seeing Effigy placed at {effigy_coord.to_algebraic()}."

class EyeOfRuin(Card):
    """
    Eye of Ruin – You look at the opponent's hand, choose one card to steal and immediately play it.
    Then you must select one of your own cards, which the opponent immediately plays.

    Notes:
    - Stealing removes the card from enemy hand and moves it to player's hand.
    - “Immediately play” means the card’s effect is executed right now.
    - Uses the updated Hand class, which removes cards by Card instance, NOT id.
    """

    def __init__(self):
        super().__init__(
            id="eye_of_ruin",
            name="Eye of Ruin",
            description=(
                "See your opponent's hand. Steal any one card from them and play it immediately. "
                "Then choose one of your own cards, which the opponent must immediately play."
            ),
            big_img="static/cards/eye_ruin_big.png",
            small_img="static/cards/eye_ruin_small.png"
        )
        self.target_type = TargetType.PIECE  # not strictly needed, but UI may use it

    @property
    def card_type(self) -> CardType:
        return CardType.FORCED


    def can_play(self, board: Board, player: Player) -> bool:
        """Player must have at least one card, and opponent must have at least one card."""
        opponent = board.game_state.get_opponent_player()
        return len(player.hand) > 0 and len(opponent.hand) > 0


    def apply_effect(
        self,
        board: Board,
        player: Player,
        target_data: Dict[str, Any]
    ) -> tuple[bool, str]:

        """
        target_data must contain:
            {
                "steal": "<card_id>",   # id of opponent's card to steal/play
                "sacrifice": "<card_id>" # id of player's card to force opponent to play
            }
        """

        gs = board.game_state
        opponent = gs.get_opponent_player()

        # ---------------------
        # 1. Validate target_data
        # ---------------------
        steal_id = target_data.get("steal")
        sacrifice_id = target_data.get("sacrifice")

        if not steal_id or not sacrifice_id:
            return False, "You must choose a card to steal and a card to sacrifice."

        # ---------------------
        # 2. Get actual Card instances
        # ---------------------
        steal_card_obj = next((c for c in opponent.hand.cards if c.id == steal_id), None)
        if not steal_card_obj:
            return False, f"Opponent does not have card {steal_id}"

        sacrifice_card_obj = next((c for c in player.hand.cards if c.id == sacrifice_id), None)
        if not sacrifice_card_obj:
            return False, f"You do not have card {sacrifice_id}"


        # ---------------------
        # 3. Steal card: remove from opponent, add to player, then DONT keep it — play immediately
        # ---------------------
        opponent.hand.remove(steal_card_obj)
        player.hand.add(steal_card_obj)

        success1, msg1 = steal_card_obj.apply_effect(board, player, {})
        # after applied, move to player's discard pile
        player.discard_pile.add(steal_card_obj)
        player.hand.remove(steal_card_obj)


        # ---------------------
        # 4. Force opponent to play player's sacrificed card
        # ---------------------
        player.hand.remove(sacrifice_card_obj)
        opponent.hand.add(sacrifice_card_obj)

        success2, msg2 = sacrifice_card_obj.apply_effect(board, opponent, {})
        # after applied, move to opponent discard pile
        opponent.discard_pile.add(sacrifice_card_obj)
        opponent.hand.remove(sacrifice_card_obj)


        return True, (
            f"You stole and played {steal_id}. "
            f"Opponent was forced to play your {sacrifice_id}."
        )

class ForbiddenLands(Card):
    """
    Hidden: Forbidden Lands – Expands the board by adding a 'forbidden ring' around it.

    Rules:
      - Activates DMZ (10x10 board).
      - Marks outermost squares as 'forbidden'.
      - Pieces inside Forbidden Lands cannot be captured.
      - Kings cannot enter Forbidden Lands.
      - Moves leaving Forbidden Lands cannot capture.
      - Playing again while active spawns a Pawn in your back forbidden rank.
    """

    def __init__(self):
        super().__init__(
            id="forbidden_lands",
            name="Forbidden Lands",
            description=(
                "Creates a protective ring of tiles (Forbidden Lands). "
                "Pieces inside cannot be captured; kings cannot enter; "
                "and pieces leaving the zone cannot perform a capture. "
                "Playing this card again while active summons a pawn "
                "in your back forbidden rank."
            ),
            big_img="static/cards/forbidden_lands_big.png",
            small_img="static/cards/forbidden_lands_small.png"
        )

    @property
    def card_type(self) -> CardType:
        return CardType.HIDDEN

    def can_play(self, board: Board, player: Player) -> bool:
        """Card can always be played (no direct target required)."""
        return True

    def apply_effect(self, board: Board, player: Player, target_data: dict) -> tuple[bool, str]:
        """
        Applies Forbidden Lands effect to the board.
        If already active, summons a pawn in player's back forbidden rank.
        """
        # Case 1: First play — activate Forbidden Lands
        if not board.forbidden_active:
            board.activate_forbidden_lands()
            return True, (
                "Forbidden Lands activated — the outer ring is now marked as forbidden. "
                "Pieces inside cannot be captured, and kings may not enter."
            )

        # Case 2: Already active — summon a pawn in the player's back forbidden rank
        forbidden_back_rank = 0 if player.color == Color.WHITE else 9
        possible_tiles = [
            coord for coord in board.forbidden_positions
            if coord.rank == forbidden_back_rank and board.is_empty(coord)
        ]

        if not possible_tiles:
            return False, "No available space to summon a pawn in your forbidden back rank."

        spawn_square = random.choice(possible_tiles)
        pawn_id = f"{player.color.name[0].lower()}P{len(board.squares)}"
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
        """
        Mark two pieces for 5 turns.
        Expects target_data with 'friendly_piece' and 'enemy_piece' coordinates.
        """
        
        # Parse target coordinates
        friendly_square = target_data.get("friendly_piece")
        enemy_square = target_data.get("enemy_piece")
        
        if not friendly_square or not enemy_square:
            return False, "Must specify both friendly and enemy pieces to mark"
        
        try:
            friendly_coord = Coordinate.from_algebraic(friendly_square)
            enemy_coord = Coordinate.from_algebraic(enemy_square)
        except Exception as e:
            return False, f"Invalid coordinates: {e}"
        
        # Validate pieces exist
        friendly_piece = board.piece_at_coord(friendly_coord)
        enemy_piece = board.piece_at_coord(enemy_coord)
        
        if not friendly_piece or friendly_piece.color != player.color:
            return False, "Invalid friendly piece selection"
        
        if not enemy_piece or enemy_piece.color == player.color:
            return False, "Invalid enemy piece selection"
        
        # Mark both pieces visually
        friendly_piece.marked = True
        enemy_piece.marked = True
        
        # Register mark effects with tracker
        if hasattr(board, 'game_state') and board.game_state:
            from backend.services.effect_tracker import EffectType
            def unmark_piece(effect):
                """Remove mark after 5 turns"""
                piece_id = effect.metadata['piece_id']
                # Find piece and unmark it
                for coord, piece in board.squares.items():
                    if piece.id == piece_id:
                        piece.marked = False
                        print(f"Mark expired on {piece_id}")
                        break
            
            # Mark friendly piece
            board.game_state.effect_tracker.add_effect(
                effect_type=EffectType.PIECE_MARK,
                start_turn=board.game_state.fullmove_number,
                duration=5,
                target=friendly_piece.id,
                metadata={'piece_id': friendly_piece.id, 'marked_by': 'eye_for_eye'},
                on_expire=unmark_piece
            )
            
            # Mark enemy piece
            board.game_state.effect_tracker.add_effect(
                effect_type=EffectType.PIECE_MARK,
                start_turn=board.game_state.fullmove_number,
                duration=5,
                target=enemy_piece.id,
                metadata={'piece_id': enemy_piece.id, 'marked_by': 'eye_for_eye'},
                on_expire=unmark_piece
            )
        
        return True, f"Marked {friendly_square} and {enemy_square} for 5 turns. Capturing a marked piece grants an extra turn!"


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
        
        # Check if player has any pawns on the board
        for coord, piece in board.squares.items():
            if piece.color == player.color and piece.type == PieceType.PAWN:
                return True
        return False
    
    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        """Transform a pawn at target coordinate into a scout"""

        
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
    Knight: Headhunter - Select one knight to transform into a headhunter.
    Headhunters move like a king and can attack up to 3 squares straight ahead.
    Value: 5.
    """

    def __init__(self):
        super().__init__(
            id="knight_headhunter",
            name="Knight: Headhunter",
            description="Transform a knight into a headhunter. Headhunters move like a king and project an attack 3 squares forward.",
            big_img="static/example_big.png",
            small_img="static/example_small.png"
        )
        self.target_type = TargetType.PIECE

    @property
    def card_type(self) -> CardType:
        return CardType.TRANSFORM

    def can_play(self, board: Board, player: Player) -> bool:
        """Check if player has any knights to transform"""

        for coord, piece in board.squares.items():
            if piece.color == player.color and piece.type == PieceType.KNIGHT:
                return True
        return False

    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Transform a knight at the target coordinate into a headhunter.
        Expects target_data['target'] as algebraic like 'e4'.
        """

        target_square = target_data.get("target")
        if not target_square:
            return False, "No target square provided"

        # Parse coordinate
        try:
            target_coord = Coordinate.from_algebraic(target_square)
        except Exception:
            return False, f"Invalid coordinate: {target_square}"

        # Validate piece existence & ownership
        piece = board.piece_at_coord(target_coord)
        if not piece:
            return False, f"No piece at {target_square}"
        if piece.color != player.color:
            return False, "That's not your piece"

        # Ensure it's a Knight
        if piece.type != PieceType.KNIGHT:
            return False, "Can only transform knights into headhunters"

        # Create Headhunter with a unique ID and same owner/color
        hh_id = f"headhunter_{player.color.value}_{target_coord.to_algebraic()}"
        headhunter = HeadHunter(hh_id, player.color)

        # Replace the Knight with the Headhunter in-place
        board.squares[target_coord] = headhunter

        return True, f"Knight at {target_square} transformed into Headhunter!"



class TransformToWarlock(Card):
    """
    Bishop: Warlock - Select any bishop to turn into a warlock.
    Warlocks can move to any same-colored tile within a 3-tile radius (clear line),
    may move 1 tile backward to change tile color, and when an effigy is destroyed
    they gain Knight + Rook movement for 2 turns. Value: 5.
    """

    def __init__(self):
        super().__init__(
            id="bishop_warlock",
            name="Bishop: Warlock",
            description="Transform a bishop into a warlock. Warlocks blink to same-colored tiles (r=3), can step back 1, and gain Knight+Rook for 2 turns when an effigy dies.",
            big_img="static/example_big.png",
            small_img="static/example_small.png"
        )
        self.target_type = TargetType.PIECE

    @property
    def card_type(self) -> CardType:
        return CardType.TRANSFORM

    def can_play(self, board: Board, player: Player) -> bool:
        """Check if player has any bishops to transform."""

        for _, piece in board.squares.items():
            if piece.color == player.color and piece.type == PieceType.BISHOP:
                return True
        return False

    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Transform a bishop at target coordinate into a warlock.
        Expects target_data['target'] as algebraic like 'e4'.
        """

        target_square = target_data.get("target")
        if not target_square:
            return False, "No target square provided"

        # Parse coordinate (e.g., "c3")
        try:
            target_coord = Coordinate.from_algebraic(target_square)
        except Exception:
            return False, f"Invalid coordinate: {target_square}"

        # Validate piece existence & ownership
        piece = board.piece_at_coord(target_coord)
        if not piece:
            return False, f"No piece at {target_square}"
        if piece.color != player.color:
            return False, "That's not your piece"

        # Ensure it's a Bishop
        if piece.type != PieceType.BISHOP:
            return False, "Can only transform bishops into warlocks"

        # Capture state you want to preserve across transform
        preserved = {}
        for attr in ("has_moved", "status", "damage", "effects"):
            if hasattr(piece, attr):
                preserved[attr] = getattr(piece, attr)

        # Create Warlock with unique id and same owner/color
        wl_id = f"warlock_{player.color.value}_{target_coord.to_algebraic()}"
        warlock = Warlock(wl_id, player.color)

        # Reapply preserved state if applicable
        for k, v in preserved.items():
            try:
                setattr(warlock, k, v)
            except Exception:
                pass  # ignore if Warlock doesn't support a field

        # Replace the Bishop with the Warlock in-place
        board.squares[target_coord] = warlock

        return True, f"Bishop at {target_square} transformed into Warlock!"



class TransformToDarkLord(Card):
    """
    Queen: Dark Lord — Select one of your Queens to transform into a Dark Lord.

    The Dark Lord:
      - Moves like a Queen, but every 2 turns (due to daylight) moves like a King for 2 turns.
      - After moving, may enthrall an adjacent (1-tile radius) enemy piece.
      - Enthralling lasts 2 turns: the target cannot move.
      - After 2 turns, the piece is converted to the Dark Lord’s color.
      - If the Dark Lord moves or is captured, enthralling is cancelled.
      - If total enemy piece value ≤ 10, the Dark Lord dies instantly.
      - Value: 9.
    """

    def __init__(self):
        super().__init__(
            id="queen_darklord",
            name="Queen: Dark Lord",
            description=(
                "Transform a Queen into a Dark Lord. The Dark Lord can enthrall nearby enemies (turning them into an ally) "
                "and suffers from daylight every 2 turns. Dies if enemy value ≤ 10."
            ),
            big_img="static/cards/queen_darklord_big.png",
            small_img="static/cards/queen_darklord_small.png"
        )
        self.target_type = TargetType.PIECE

    @property
    def card_type(self) -> CardType:
        return CardType.TRANSFORM

    def can_play(self, board: Board, player: Player) -> bool:
        """Check if player has at least one Queen to transform."""
        for _, piece in board.squares.items():
            if piece.color == player.color and piece.type == PieceType.QUEEN:
                return True
        return False

    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        """Transform a selected Queen into a Dark Lord."""

        # Parse and validate target coordinate
        target_square = target_data.get("target")
        if not target_square:
            return False, "No target square provided."

        try:
            target_coord = Coordinate.from_algebraic(target_square)
        except Exception:
            return False, f"Invalid coordinate: {target_square}"

        # Ensure the target is a Queen owned by the player
        piece = board.piece_at_coord(target_coord)
        if not piece:
            return False, f"No piece found at {target_square}."
        if piece.color != player.color:
            return False, "You can only transform your own Queen."
        if piece.type != PieceType.QUEEN:
            return False, "Target must be a Queen."

        # Perform transformation
        darklord_id = f"{player.color.value}{PieceType.DARKLORD.value}1"
        darklord = DarkLord(darklord_id, player.color)
        board.squares[target_coord] = darklord

        return True, f"Your Queen at {target_square} has been transformed into a Dark Lord!"


class PawnQueen(Card):
    """
    Pawn: Queen – The pawn furthest from the enemy king transforms into a queen for 2 turns.
    After the 2 turns, if the pawn is on any of the last 3 ranks (toward the enemy),
    it becomes a peon; otherwise it reverts to a normal pawn.
    """

    def __init__(self):
        super().__init__(
            id="pawn_queen",
            name="Pawn: Queen",
            description=(
                "The pawn furthest from the enemy king transforms into a queen for 2 turns. "
                "After 2 turns, if it is on any of the last 3 ranks toward the enemy, "
                "it becomes a peon; otherwise, it reverts to a pawn."
            ),
            big_img="static/cards/pawn_queen_big.png",
            small_img="static/cards/pawn_queen_small.png",
        )

    @property
    def card_type(self) -> CardType:
        # Adjust if you want it to be SPELL/TACTIC/etc.
        return CardType.HIDDEN

    def _is_in_last_three_ranks(self, color: Color, rank: int, max_rank: int) -> bool:  
        """
        Determine if a given rank is within the last three ranks
        toward the enemy for the specified color.
        """
        if color == Color.WHITE:
            return rank >= max_rank - 2  # e.g., ranks 6,7,8 on an 8-rank board
        else:
            return rank <= 3  # e.g., ranks 1,2,3 on an 8-rank board
    def can_play(self, board: Board, player: Player) -> bool:
        """
        Card can be played if the player has at least one pawn on the board.
        (We only consider actual Pawn pieces, not already-transformed queens.)
        """
        for piece in board.squares.values():
            if isinstance(piece, Pawn) and piece.color == player.color:
                return True
        return False

    def _get_furthest_pawn_from_enemy_king(self, board: Board, player_color: Color, enemy_king_coord: Coordinate) -> tuple[Optional[Coordinate], Optional[Pawn]]:
        """
        Find the pawn of `player_color` that is furthest (Chebyshev distance)
        from the enemy king located at `enemy_king_coord`.
        Returns a tuple of (Coordinate, Pawn) or (None, None) if no pawns found.
        """
        max_distance = -1
        target_coord = None
        target_pawn = None

        for coord, piece in board.squares.items():
            if isinstance(piece, Pawn) and piece.color == player_color:
                distance = max(abs(coord.file - enemy_king_coord.file), abs(coord.rank - enemy_king_coord.rank))
                if distance > max_distance:
                    max_distance = distance
                    target_coord = coord
                    target_pawn = piece

        return target_coord, target_pawn
    def apply_effect(self, board: Board, player: Player, target_data: dict) -> tuple[bool, str]:
        """
        - Find the pawn of `player` that is furthest (Chebyshev distance) from the enemy king.
        - Transform it into a Queen for 2 turns.
        - Use the effect tracker to revert it to Pawn/Peon afterward.
        """
        # Sanity: need game_state & effect_tracker
        if not hasattr(board, "game_state") or not hasattr(board.game_state, "effect_tracker"):
            return False, "Game state or effect tracker not available."

        game_state = board.game_state
        effect_tracker = game_state.effect_tracker

        # 1. Find enemy king and its coordinate
        enemy_color = Color.BLACK if player.color == Color.WHITE else Color.WHITE
        enemy_king_coord = None

        for coord, piece in board.squares.items():
            if isinstance(piece, King) and piece.color == enemy_color:
                enemy_king_coord = coord
                break

        if enemy_king_coord is None:
            return False, "Enemy king not found on the board."

        # 2. Find player's pawn furthest from that king
        target_coord, target_pawn = self._get_furthest_pawn_from_enemy_king(
            board, player.color, enemy_king_coord
        )

        if target_pawn is None:
            return False, "You have no pawns to target with this card."

        pawn_id = target_pawn.id
        pawn_color = target_pawn.color

        # 3. Transform that pawn into a Queen (replace piece on this square)
        transformed_queen = Queen(pawn_id, pawn_color)
        # Keep the piece_type consistent with the class
        transformed_queen.type = PieceType.QUEEN
        transformed_queen.piece_type = PieceType.QUEEN
        board.squares[target_coord] = transformed_queen

        # 4. Register an effect lasting 2 turns for this piece ID
        def on_expire(effect):
            """
            Called by effect tracker after 2 turns.
            We:
              - Find the current piece with this id on the board.
              - Replace it with a Pawn.
              - If it's on the last 3 ranks (toward enemy), flag it as PEON.
            """
            # Find piece by id on the current board
            found_coord = None
            found_piece: Piece | None = None

            for c, p in board.squares.items():
                if getattr(p, "id", None) == pawn_id:
                    found_coord = c
                    found_piece = p
                    break

            # If the piece isn't on the board anymore (captured, etc.), do nothing
            if found_coord is None or found_piece is None:
                return

            # Determine board height / max rank
            # Try to pull from board, otherwise assume 8 (classic)
            max_rank = getattr(board, "rows", getattr(board, "height", 8))

            rank = found_coord.rank
            # Create a fresh pawn with same id/color
            new_pawn = Pawn(pawn_id, pawn_color)

            # Default: normal pawn
            new_pawn.type = PieceType.PAWN
            new_pawn.piece_type = PieceType.PAWN

            # If it's in the "last 3 ranks" toward the enemy, it becomes a peon
            if self._is_in_last_three_ranks(pawn_color, rank, max_rank):
                # Use a distinct PieceType if you have PEON in your enum
                if hasattr(PieceType, "PEON"):
                    new_pawn.type = PieceType.PEON
                    new_pawn.piece_type = PieceType.PEON
                # You can also adjust its value here if you want it weaker, e.g.:
                # new_pawn.value = 0

            # Replace the queen with the new pawn/peon
            board.squares[found_coord] = new_pawn

        effect_tracker.add_effect(
            effect_type=EffectType.PAWN_QUEEN,      # define this in your EffectType enum
            start_turn=game_state.fullmove_number,
            duration=2,
            target=pawn_id,                         # tie effect to piece id
            on_expire=on_expire,
        )

        return True, (
            f"{pawn_id} has transformed into a Queen for 2 turns. "
            "After that, it will become a Peon if deeply advanced, "
            "or revert to a Pawn."
        ) 
    
class Shroud(Card):
    """
    Hidden: Shroud (3-turn duration)
    When played, switches the position and appearance of two random friendly pieces for 3 turns.
    If the player has fewer than two pieces, summons a peon on a safe tile and then swaps.
    Never swaps either king into check; if no safe swap exists, summons a peon instead.
    """
    def __init__(self):
        super().__init__(
            id="shroud",
            name="Shroud",
            description=(
                "Hidden: Shroud (3 turns) – Switches the position and appearance of two random "
                "friendly pieces. If you control fewer than two pieces, summons a peon on a safe "
                "tile first. Never swaps either king into check."
            ),
            big_img="static/cards/shroud_big.png",
            small_img="static/cards/shroud_small.png"
        )

    @property
    def card_type(self) -> CardType:
        return CardType.HIDDEN

    def _all_possible_coords(self, board: Board):
        max_file = 9 if board.dmzActive else 8
        min_file = 0 if board.dmzActive else 1
        coords = []
        for f in range(min_file, max_file + 1):
            for r in range(min_file, max_file + 1):
                c = Coordinate(f, r)
                if board.is_in_bounds(c):
                    coords.append(c)
        return coords

    def _get_player_pieces(self, board: Board, color: Color):
        """Returns list[(coord, piece)] for given color."""
        return [
            (coord, piece)
            for coord, piece in board.squares.items()
            if piece is not None and piece.color == color
        ]

    def _summon_peon_safe(self, board: Board, color: Color) -> Optional[Coordinate]:
        """Summon a peon on a random empty tile that does not leave own king in check."""
        safe_tiles = []
        for coord in self._all_possible_coords(board):
            if not board.is_empty(coord):
                continue

            temp_peon = Peon(id="temp_peon", color=color, piece_type=PieceType.PEON, value=1)
            board.place_piece(temp_peon, coord)
            safe = not board.is_in_check(color)
            board.remove_piece(coord)

            if safe:
                safe_tiles.append(coord)

        if not safe_tiles:
            return None

        chosen = random.choice(safe_tiles)
        real_peon = Peon(
            id=board.generate_piece_id(color),
            color=color,
            piece_type=PieceType.PEON,
            value=1
        )
        board.place_piece(real_peon, chosen)
        return chosen
    
    def can_play(self, board: Board, player: Player) -> bool:
        """
        Playable if:
        - player has at least 2 pieces, OR
        - player has at least 1 piece and there is an empty tile for a peon.
        """
        pieces = self._get_player_pieces(board, player.color)
        if len(pieces) >= 2:
            return True

        if len(pieces) == 1:
            empty_tiles = [c for c in self._all_possible_coords(board) if board.is_empty(c)]
            return len(empty_tiles) > 0

        return False
    
    def apply_effect(
        self,
        board: Board,
        player: Player,
        target_data: Dict[str, Any]
    ) -> tuple[bool, str]:

        color = player.color
        opponent_color = color.opponent()

        # Ensure at least 2 friendly pieces (summon peon if needed)
        pieces = self._get_player_pieces(board, color)
        if len(pieces) < 2:
            spawned = self._summon_peon_safe(board, color)
            if spawned is None:
                return False, "No safe tile to summon a peon for Shroud."
            pieces = self._get_player_pieces(board, color)
            if len(pieces) < 2:
                return False, "Still not enough pieces to activate Shroud."

        # Try to find a legal swap pair (no king in check after swap)
        random.shuffle(pieces)
        swap_pair = None

        for i in range(len(pieces)):
            for j in range(i + 1, len(pieces)):
                coord_a, piece_a = pieces[i]
                coord_b, piece_b = pieces[j]

                # temp swap
                board.remove_piece(coord_a)
                board.remove_piece(coord_b)
                board.place_piece(piece_a, coord_b)
                board.place_piece(piece_b, coord_a)

                illegal = board.is_in_check(color) or board.is_in_check(opponent_color)

                # revert
                board.remove_piece(coord_a)
                board.remove_piece(coord_b)
                board.place_piece(piece_a, coord_a)
                board.place_piece(piece_b, coord_b)

                if not illegal:
                    swap_pair = (coord_a, piece_a, coord_b, piece_b)
                    break
            if swap_pair:
                break

        # If no safe swap, just try to summon a peon and exit
        if not swap_pair:
            spawned = self._summon_peon_safe(board, color)
            if spawned is None:
                return False, "Shroud could not find a legal swap or safe spawn."
            return True, "No legal swap found; a peon was summoned instead."

        coord_a, piece_a, coord_b, piece_b = swap_pair

        # Perform real swap
        board.remove_piece(coord_a)
        board.remove_piece(coord_b)
        board.place_piece(piece_a, coord_b)
        board.place_piece(piece_b, coord_a)

        # Swap appearance (piece type)
        orig_a_type = piece_a.type
        orig_b_type = piece_b.type
        piece_a.type, piece_b.type = orig_b_type, orig_a_type

        # Register 3-turn effect to restore appearance
        if hasattr(board, "game_state") and board.game_state:
            from backend.services.effect_tracker import EffectType

            def revert_shroud(effect):
                meta = effect.metadata
                a_id = meta["piece_a_id"]
                b_id = meta["piece_b_id"]
                a_type = meta["orig_a_type"]
                b_type = meta["orig_b_type"]

                for p in board.squares.values():
                    if p is None or not hasattr(p, "id"):
                        continue
                    if p.id == a_id:
                        p.type = a_type
                    elif p.id == b_id:
                        p.type = b_type

            board.game_state.effect_tracker.add_effect(
                effect_type=EffectType.SHROUD,   # add SHROUD to your EffectType enum
                start_turn=board.game_state.fullmove_number,
                duration=3,
                target=None,
                metadata={
                    "piece_a_id": piece_a.id,
                    "piece_b_id": piece_b.id,
                    "orig_a_type": orig_a_type,
                    "orig_b_type": orig_b_type,
                },
                on_expire=revert_shroud
            )

        return True, "Shroud activated: two pieces swapped positions and appearance for 3 turns."
    
class PawnBomb(Card):
    """
    Hidden: Pawn Bomb (8-turn fuse, shortened to 4 after moving).
    A random friendly pawn becomes a hidden bomb. Upon capture, it explodes,
    capturing all pieces within 1 tile (friend or foe). If not captured within
    8 turns, it explodes automatically. On its first move after this card is
    played, remaining fuse is truncated to 4 turns and it is revealed to the
    friendly player as the bomb pawn.
    """

    def __init__(self):
        super().__init__(
            id="pawn_bomb",
            name="Pawn Bomb",
            description=(
                "A random friendly pawn becomes a hidden bomb for up to 8 turns. "
                "If captured or its fuse runs out, it explodes in a 1-tile radius, "
                "capturing all nearby pieces. On its first move after arming, the "
                "fuse shortens to 4 turns and it is revealed to you."
            ),
            big_img="static/cards/pawn_bomb_big.png",
            small_img="static/cards/pawn_bomb_small.png",
        )

    @property
    def card_type(self) -> CardType:
        return CardType.HIDDEN

    def _get_friendly_pawns(self, board: Board, color: Color) -> list[tuple[Coordinate, Any]]:
        """Return list of (coord, piece) for all friendly pawns."""
        pawns: list[tuple[Coordinate, Any]] = []
        for coord, piece in board.squares.items():
            if piece is None or piece.color != color:
                continue
            # Treat PAWN / PEON as valid pawn types
            if piece.type in (PieceType.PAWN, getattr(PieceType, "PEON", PieceType.PAWN)):
                pawns.append((coord, piece))
        return pawns

    def _find_piece_coord_by_id(self, board: Board, piece_id: str) -> Optional[Coordinate]:
        for coord, piece in board.squares.items():
            if piece is not None and getattr(piece, "id", None) == piece_id:
                return coord
        return None

    def _explode_pawn_bomb(self, board: Board, center: Coordinate) -> None:
        """
        Detonate the bomb at `center`.
        Here we just reuse the mine's explosion logic if available.
        """
        if hasattr(board, "detonate_mine"):
            board.detonate_mine(center)
        else:
            # Fallback: capture all pieces in 1-tile radius (including the pawn itself)
            for df in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    c = Coordinate(center.file + df, center.rank + dr)
                    if not board.is_in_bounds(c):
                        continue
                    if not board.is_empty(c):
                        board.remove_piece(c)

    def can_play(self, board: Board, player: Player) -> bool:
        """Can be played if the player controls at least one pawn."""
        pawns = self._get_friendly_pawns(board, player.color)
        return len(pawns) > 0

    def apply_effect(
        self,
        board: Board,
        player: Player,
        target_data: dict[str, Any],
    ) -> tuple[bool, str]:

        color = player.color
        pawns = self._get_friendly_pawns(board, color)
        if not pawns:
            return False, "You have no pawns to turn into a bomb."

        # Choose random friendly pawn to arm
        pawn_coord, pawn_piece = random.choice(pawns)
        bomb_pawn_id = pawn_piece.id

        # Register 8-turn fuse in effect tracker
        if hasattr(board, "game_state") and board.game_state:
            from backend.services.effect_tracker import EffectType

            def on_expire(effect):
                """
                Called when the fuse runs out.
                If pawn is still on the board, explode at its current location.
                """
                pid = effect.target
                coord = self._find_piece_coord_by_id(board, pid)
                if coord is not None:
                    self._explode_pawn_bomb(board, coord)

            board.game_state.effect_tracker.add_effect(
                effect_type=EffectType.PAWN_BOMB,          # define in EffectType enum
                start_turn=board.game_state.fullmove_number,
                duration=8,
                target=bomb_pawn_id,                       # tie effect to pawn id
                metadata={
                    "owner_color": color.name,
                    "revealed_to_owner": False,
                    "fuse_shortened": False,
                    # movement hook elsewhere can use these flags
                },
                on_expire=on_expire,
            )

        # NOTE: explosion on capture and fuse-shortening on first move
        # should be handled in your move/capture logic by:
        # - checking for an active EffectType.PAWN_BOMB on the moving/captured pawn
        # - if pawn moves for the first time: reduce remaining turns to 4,
        #   set metadata["fuse_shortened"] = True and metadata["revealed_to_owner"] = True
        # - if pawn is captured: immediately call _explode_pawn_bomb at its square.

        return True, "A random pawn has become a hidden bomb with an 8-turn fuse."

class Shroud(Card):
    """
    Hidden: Shroud (3-turn duration)
    Swaps two random friendly pieces' positions and appearance for 3 turns.
    If fewer than 2 pieces exist, summons a Peon safely first.
    Never swaps either king into check.
    """

    def __init__(self):
        super().__init__(
            id="shroud",
            name="Shroud",
            description=(
                "Hidden (3 turns): Swap two random friendly pieces' position and appearance. "
                "If you have fewer than 2 pieces, summon a Peon safely first. "
                "Never swaps a king into check."
            ),
            big_img="static/cards/shroud_big.png",
            small_img="static/cards/shroud_small.png"
        )

    @property
    def card_type(self) -> CardType:
        return CardType.HIDDEN

    # --------------------------------------------------------------
    # Helper: list all valid board squares
    # --------------------------------------------------------------
    def _all_board_coords(self, board: Board):
        min_f = 0 if board.dmzActive else 1
        max_f = 9 if board.dmzActive else 8
        coords = []

        for f in range(min_f, max_f + 1):
            for r in range(min_f, max_f + 1):
                c = Coordinate(f, r)
                if board.is_in_bounds(c):
                    coords.append(c)

        return coords

    # --------------------------------------------------------------
    # Helper: collect all friendly (coord, piece)
    # --------------------------------------------------------------
    def _get_player_pieces(self, board: Board, color: Color):
        return [(coord, p) for coord, p in board.squares.items() if p.color == color]

    # --------------------------------------------------------------
    # Helper: Test if placing a Peon here is safe
    # --------------------------------------------------------------
    def _is_safe_tile_for_peon(self, board: Board, coord: Coordinate, color: Color) -> bool:
        temp_board = board.clone()

        peon = Peon(id="TEMP_PEON", color=color)
        temp_board.squares[coord] = peon

        # safe means your king is NOT in check
        return not temp_board.in_check_for(color)

    # --------------------------------------------------------------
    # Helper: Summon peon safely
    # --------------------------------------------------------------
    def _summon_peon_safe(self, board: Board, color: Color) -> Optional[Coordinate]:
        safe_coords = [
            c for c in self._all_board_coords(board)
            if board.is_empty(c) and self._is_safe_tile_for_peon(board, c, color)
        ]

        if not safe_coords:
            return None

        chosen = random.choice(safe_coords)

        new_id = f"peon_{color.value}_{random.randint(10000,99999)}"
        peon = Peon(id=new_id, color=color)
        board.squares[chosen] = peon
        return chosen

    # --------------------------------------------------------------
    # Can play
    # --------------------------------------------------------------
    def can_play(self, board: Board, player: Player) -> bool:
        pieces = self._get_player_pieces(board, player.color)

        if len(pieces) >= 2:
            return True

        if len(pieces) == 1:
            # Check if a peon can be placed anywhere
            for c in self._all_board_coords(board):
                if board.is_empty(c):
                    return True

        return False

    # --------------------------------------------------------------
    # MAIN LOGIC
    # --------------------------------------------------------------
    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:

        color = player.color
        opp_color = Color.WHITE if color == Color.BLACK else Color.BLACK

        pieces = self._get_player_pieces(board, color)

        # ----------------------------------------------
        # 1. Ensure 2 friendly pieces (summon peon if needed)
        # ----------------------------------------------
        if len(pieces) < 2:
            spawned = self._summon_peon_safe(board, color)
            if not spawned:
                return False, "Shroud: No safe tile to summon a Peon."
            pieces = self._get_player_pieces(board, color)
            if len(pieces) < 2:
                return False, "Shroud: Still not enough pieces to perform swap."

        # ----------------------------------------------
        # 2. Try to find a safe swap pair (no king enters check)
        # ----------------------------------------------
        random.shuffle(pieces)
        swap_pair = None

        for i in range(len(pieces)):
            for j in range(i + 1, len(pieces)):
                coord_a, piece_a = pieces[i]
                coord_b, piece_b = pieces[j]

                test_board = board.clone()

                # perform temporary swap
                test_board.squares.pop(coord_a)
                test_board.squares.pop(coord_b)
                test_board.squares[coord_a] = piece_b
                test_board.squares[coord_b] = piece_a

                # must not leave either king in check
                if not test_board.in_check_for(color) and not test_board.in_check_for(opp_color):
                    swap_pair = (coord_a, piece_a, coord_b, piece_b)
                    break
            if swap_pair:
                break

        # ----------------------------------------------
        # 3. If no safe swap → summon a peon instead (fallback)
        # ----------------------------------------------
        if not swap_pair:
            spawned = self._summon_peon_safe(board, color)
            if not spawned:
                return False, "Shroud: No legal swap and no safe place to spawn a Peon."
            return True, "No safe swap found, so a Peon was summoned instead."

        coord_a, piece_a, coord_b, piece_b = swap_pair

        # ----------------------------------------------
        # 4. Execute REAL swap
        # ----------------------------------------------
        board.squares.pop(coord_a)
        board.squares.pop(coord_b)
        board.squares[coord_a] = piece_b
        board.squares[coord_b] = piece_a

        # ----------------------------------------------
        # 5. Swap appearance (their piece types)
        # ----------------------------------------------
        original_a = piece_a.piece_type
        original_b = piece_b.piece_type

        piece_a.piece_type = original_b
        piece_b.piece_type = original_a

        # ----------------------------------------------
        # 6. Register 3-turn restoration effect
        # ----------------------------------------------
        if board.game_state:
            tracker = board.game_state.effect_tracker

            def undo_swap(effect):
                meta = effect.metadata
                a_id = meta["piece_a"]
                b_id = meta["piece_b"]
                a_type = meta["a_type"]
                b_type = meta["b_type"]

                for p in board.squares.values():
                    if p.id == a_id:
                        p.piece_type = a_type
                    elif p.id == b_id:
                        p.piece_type = b_type

            tracker.add_effect(
                effect_type=EffectType.SHROUD,
                start_turn=board.game_state.fullmove_number,
                duration=3,
                target=None,
                metadata={
                    "piece_a": piece_a.id,
                    "piece_b": piece_b.id,
                    "a_type": original_a,
                    "b_type": original_b,
                },
                on_expire=undo_swap
            )

        return True, "Shroud activated: two pieces swapped positions and appearance for 3 turns."

class SummonBarricade(Card):
    """
    Summon: Barricade - Places an uncapturable barricade on a target square.
    Barricades block movement for both players and last for 5 turns.
    Cannot move through or capture barricades.
    """
    
    def __init__(self):
        super().__init__(
            id="summon_barricade",
            name="Summon Barricade",
            description=(
                "Place an uncapturable barricade on an empty square. "
                "Barricades block all movement and last for 5 turns."
            ),
            big_img="static/cards/summon_barricade_big.png",
            small_img="static/cards/summon_barricade_small.png"
        )
    
    @property
    def card_type(self) -> CardType:
        return CardType.SUMMON
    
    @property
    def target_type(self) -> TargetType:
        """Requires targeting an empty square"""
        return TargetType.EMPTY_SQUARE
    
    def can_play(self, board: Board, player: Player) -> bool:
        """Can play if at least one empty square exists on the board."""
        for coord in board.squares.keys():
            # If we find any piece, there must be empty squares (board isn't full)
            return True
        
        # If board.squares is empty, all squares are empty (can definitely play)
        return True
    
    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Places an uncapturable barricade on the target square for 5 turns.
        
        Args:
            board: The game board
            player: The player playing the card
            target_data: Dictionary containing 'file' and 'rank' of target square
        
        Returns:
            tuple[bool, str]: (Success boolean, message string)
        """
        # Extract target coordinate from target_data
        try:
            target_file = target_data['file']
            target_rank = target_data['rank']
            target_coord = Coordinate(target_file, target_rank)
        except (KeyError, TypeError):
            return False, "Invalid target coordinate provided."
        
        # Validate target is in bounds
        if not board.is_in_bounds(target_coord):
            return False, "Target square is out of bounds."
        
        # Validate target square is empty
        if not board.is_empty(target_coord):
            return False, "Target square must be empty to place a barricade."
        
        # Create unique barricade ID
        import time
        barricade_id = f"barricade_{int(time.time() * 1000)}"
        
        # Create and place barricade piece
        from backend.chess.piece import Barricade
        barricade = Barricade(barricade_id)
        board.squares[target_coord] = barricade
        
        print(f"Barricade placed at {target_coord.to_algebraic()} by {player.color.name}")
        
        # Track effect for automatic removal after 5 turns
        if hasattr(board, 'game_state') and board.game_state:
            from backend.services.effect_tracker import EffectType
            
            def remove_barricade(effect):
                """Callback to remove barricade when effect expires"""
                coord = Coordinate(target_coord.file, target_coord.rank)
                if coord in board.squares:
                    piece = board.squares[coord]
                    if piece.type == PieceType.BARRICADE:
                        del board.squares[coord]
                        print(f"Barricade at {coord.to_algebraic()} expired and removed")
            
            board.game_state.effect_tracker.add_effect(
                effect_type=EffectType.BARRICADE,
                start_turn=board.game_state.fullmove_number,
                duration=5,
                target=target_coord,
                metadata={
                    'coordinate': target_coord,
                    'placed_by': player.color.name
                },
                on_expire=remove_barricade
            )
        
        return True, f"Barricade placed at {target_coord.to_algebraic()} for 5 turns."

class Transmute(Card):
    """
    Transmute - Select a piece to convert it to any piece of equal value.
    Cannot transmute Kings, Effigies, or Barricades.
    Player must select which piece type to transform into.
    """

    def __init__(self):
        super().__init__(
            id="transmute",
            name="Transmute",
            description=(
                "Select one of your pieces to transform into any other piece of equal value. "
                "Cannot transmute Kings, Effigies, or Barricades."
            ),
            big_img="static/cards/transmute_big.png",
            small_img="static/cards/transmute_small.png"
        )
        self.target_type = TargetType.PIECE

    @property
    def card_type(self) -> CardType:
        return CardType.TRANSFORM

    def _get_piece_value(self, piece: Piece) -> int:
        """Get the value of a piece, handling special cases."""
        return getattr(piece, 'value', 0)

    def _is_transmutable(self, piece: Piece) -> bool:
        """
        Check if a piece can be transmuted.
        Excludes: Kings, Effigies, Barricades, and any piece with value 0.
        """
        # Explicit exclusions
        if piece.type == PieceType.KING:
            return False
        if piece.type == PieceType.EFFIGY:
            return False
        if piece.type == PieceType.BARRICADE:
            return False
        
        value = self._get_piece_value(piece)
        return value > 0

    def _get_available_transformations(self, value: int) -> List[PieceType]:
        """
        Get list of piece types that can be created with the given value.
        Excludes Kings, Effigies, and Barricades.
        """
        value_to_types = {
            1: [PieceType.PAWN, PieceType.PEON],
            3: [PieceType.BISHOP, PieceType.KNIGHT, PieceType.SCOUT, PieceType.CLERIC],
            5: [PieceType.ROOK, PieceType.HEADHUNTER, PieceType.WARLOCK, PieceType.WITCH],
            9: [PieceType.QUEEN],
            10: [PieceType.DARKLORD]
        }
        
        return value_to_types.get(value, [])

    def can_play(self, board: Board, player: Player) -> bool:
        """Check if player has any transmutable pieces."""
        for coord, piece in board.squares.items():
            if piece.color == player.color and self._is_transmutable(piece):
                return True
        return False

    def get_transmute_options(self, board: Board, player: Player, target_square: str) -> Optional[Dict[str, Any]]:
        """
        Get available transformation options for a piece at target square.
        This method is called by the frontend to display options to the player.
        
        Returns None if piece cannot be transmuted, otherwise returns:
        {
            "square": "d1",
            "current_type": "BISHOP",
            "value": 3,
            "options": ["BISHOP", "KNIGHT", "SCOUT", "CLERIC"]
        }
        """
        try:
            target_coord = Coordinate.from_algebraic(target_square)
        except Exception:
            return None

        piece = board.piece_at_coord(target_coord)
        if not piece or piece.color != player.color:
            return None

        if not self._is_transmutable(piece):
            return None

        value = self._get_piece_value(piece)
        available_types = self._get_available_transformations(value)

        if not available_types:
            return None

        return {
            "square": target_square,
            "current_type": piece.type.name,
            "value": value,
            "options": [pt.name for pt in available_types]
        }

    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Transform a piece at target coordinate into selected piece type.
        
        Expected target_data format:
        {
            "target": "e4",          # Square containing piece to transmute
            "transform_to": "ROOK"   # Desired piece type (uppercase string)
        }
        """
        # Parse target coordinate
        target_square = target_data.get("target")
        if not target_square:
            return False, "No target square provided"

        try:
            target_coord = Coordinate.from_algebraic(target_square)
        except Exception:
            return False, f"Invalid coordinate: {target_square}"

        # Validate piece exists and belongs to player
        piece = board.piece_at_coord(target_coord)
        if not piece:
            return False, f"No piece at {target_square}"
        if piece.color != player.color:
            return False, "That's not your piece"

        # Check if piece can be transmuted
        if not self._is_transmutable(piece):
            return False, f"Cannot transmute {piece.type.name}"

        # Get target transformation type
        transform_to_str = target_data.get("transform_to")
        if not transform_to_str:
            return False, "No transformation type specified"

        try:
            transform_to = PieceType[transform_to_str.upper()]
        except KeyError:
            return False, f"Invalid piece type: {transform_to_str}"

        # Verify transformation is valid for this value
        piece_value = self._get_piece_value(piece)
        available_types = self._get_available_transformations(piece_value)
        
        if transform_to not in available_types:
            return False, f"Cannot transform value {piece_value} piece into {transform_to.name}"

        # Perform the transformation
        new_piece = self._create_transformed_piece(piece, transform_to, target_coord, player.color)
        if not new_piece:
            return False, f"Cannot create piece of type {transform_to.name}"

        # Replace the piece on the board
        board.squares[target_coord] = new_piece

        return True, f"{piece.type.name} at {target_square} transmuted into {transform_to.name}!"

class Exhaustion(Card):
    """
    CURSE: Exhaustion
    -----------------
    When activated:
        • Summons an Effigy belonging to the caster.
        • While the Effigy is alive, ALL enemy pieces are restricted to
          Manhattan-distance ≤ 4 for ALL their moves.

    • If the Effigy is captured/removed → Exhaustion immediately ends.
    • Cannot stack per enemy color (only one Exhaustion affecting a player).
    """

    def __init__(self):
        super().__init__(
            id="exhaustion",
            name="Exhaustion",
            description=(
                "Summons an Effigy. While it lives, all enemy pieces are limited "
                "to moving within 4 tiles (Manhattan distance). Ends if the effigy dies."
            ),
            big_img="static/cards/exhaustion_big.png",
            small_img="static/cards/exhaustion_small.png"
        )

    @property
    def card_type(self) -> CardType:
        return CardType.CURSE

    # -------------------------------------------------------------
    # Helper: find enemy king
    # -------------------------------------------------------------
    def _find_enemy_king(self, board: Board, enemy_color: Color) -> Optional[Coordinate]:
        for coord, piece in board.squares.items():
            if piece.type == PieceType.KING and piece.color == enemy_color:
                return coord
        return None

    # -------------------------------------------------------------
    # Helper: find farthest legal tile
    # -------------------------------------------------------------
    def _farthest_tile_from(self, board: Board, origin: Coordinate) -> Optional[Coordinate]:
        farthest = None
        far_dist = -1

        for coord in board._all_board_coords():
            if not board.is_empty(coord):
                continue
            if board.forbidden_active and board.is_forbidden(coord):
                continue

            dist = abs(coord.file - origin.file) + abs(coord.rank - origin.rank)
            if dist > far_dist:
                far_dist = dist
                farthest = coord

        return farthest

    # -------------------------------------------------------------
    # Helper: summon an exhaustion effigy
    # -------------------------------------------------------------
    def _summon_effigy(self, board: Board, coord: Coordinate, color: Color) -> Tuple[Effigy, str]:
        effigy_id = f"effigy_exhaustion_{color.value}_{coord.file}{coord.rank}"
        effigy = Effigy(effigy_id, color, EffectType.EXHAUSTION)
        board.squares[coord] = effigy
        return effigy, effigy_id

    # -------------------------------------------------------------
    # Prevent stacking for same enemy
    # -------------------------------------------------------------
    def can_play(self, board: Board, player: Player) -> bool:
        if not board.game_state:
            return True

        enemy_color = Color.BLACK if player.color == Color.WHITE else Color.WHITE
        tracker = board.game_state.effect_tracker

        for eff in tracker.get_effects_by_type(EffectType.EXHAUSTION):
            if eff.target == enemy_color or eff.target == enemy_color.name:
                return False  # Already exhausting this opponent
        return True

    # -------------------------------------------------------------
    # Main effect
    # -------------------------------------------------------------
    def apply_effect(
        self,
        board: Board,
        player: Player,
        target_data: Dict[str, Any]
    ) -> Tuple[bool, str]:

        gs = board.game_state
        if not gs:
            return False, "GameState unavailable."

        tracker = gs.effect_tracker
        caster = player.color
        enemy_color = Color.BLACK if caster == Color.WHITE else Color.WHITE

        # Prevent stacking (double check)
        for eff in tracker.get_effects_by_type(EffectType.EXHAUSTION):
            if eff.target == enemy_color or eff.target == enemy_color.name:
                return False, "An Exhaustion curse already affects this player."

        # 1. Find enemy king
        enemy_king = self._find_enemy_king(board, enemy_color)
        if enemy_king is None:
            return False, "Enemy king not found — cannot cast Exhaustion."

        # 2. Pick farthest legal tile
        dest = self._farthest_tile_from(board, enemy_king)
        if not dest:
            return False, "No valid tile to place Exhaustion Effigy."

        # 3. Summon Effigy
        effigy, effigy_id = self._summon_effigy(board, dest, caster)

        # 4. Register exhaustion effect
        def _tick(effect, current_turn: int):
            # If effigy dead → remove effect immediately
            alive_ids = [p.id for p in board.squares.values()]
            if effigy_id not in alive_ids:
                tracker.remove_effect(effect.effect_id)
                if effect.on_expire:
                    effect.on_expire(effect)
                return

        def _expire(effect):
            # Cleanup effigy if still present
            for coord, piece in list(board.squares.items()):
                if piece.id == effigy_id:
                    del board.squares[coord]
                    break

        tracker.add_effect(
            effect_type=EffectType.EXHAUSTION,
            start_turn=gs.fullmove_number,
            duration=9999,  # lasts until effigy is removed
            target=enemy_color,
            metadata={"effigy_id": effigy_id},
            on_tick=_tick,
            on_expire=_expire
        )

        return True, f"Exhaustion cast — Effigy placed at {dest.to_algebraic()}. Enemy pieces now have limited movement."

class OfFleshAndBlood(Card):
    """
    Of Flesh and Blood – Select a piece.
    For the next 2 moves this piece makes, summon a Peon on the square it leaves.
    """

    def __init__(self):
        super().__init__(
            id="of_flesh_and_blood",
            name="Of Flesh and Blood",
            description=(
                "Select a piece. For its next 2 moves, a Peon is summoned on each "
                "square it leaves behind."
            ),
            big_img="static/cards/of_flesh_and_blood_big.png",
            small_img="static/cards/of_flesh_and_blood_small.png"
        )

    @property
    def card_type(self) -> CardType:
        return CardType.SUMMON   # summons Peons

    @property
    def target_type(self) -> TargetType:
        return TargetType.PIECE  # the card targets a piece

    def can_play(self, board: Board, player: Player) -> bool:
        """Can play if at least one piece exists on the board."""
        return any(piece is not None for piece in board.squares.values())

    def apply_effect(self, board: Board, player: Player, target_data: Dict[str, Any]):
        """
        Apply the Of Flesh and Blood effect to the selected piece.
        target_data must contain: {"piece_id": "..."}
        """
        try:
            piece_id = target_data["piece_id"]
        except (KeyError, TypeError):
            return False, "Invalid target: piece must be selected."

        # Find the piece on the board
        target_piece = None
        for coord, piece in board.squares.items():
            if piece and getattr(piece, "id", None) == piece_id:
                target_piece = piece
                break

        if not target_piece:
            return False, "Selected piece does not exist."

        # Register effect
        if hasattr(board, "game_state") and board.game_state:
            from backend.services.effect_tracker import EffectType

            metadata = {
                "piece_id": piece_id,
                "moves_remaining": 2,
                "owner_color": player.color.value
            }

            board.game_state.effect_tracker.add_effect(
                effect_type=EffectType.OF_FLESH_AND_BLOOD,
                start_turn=board.game_state.fullmove_number,
                duration=0,         # managed manually
                target=piece_id,    # piece this effect is attached to
                metadata=metadata
            )

        print(f"Of Flesh and Blood applied to piece {piece_id}")

        return True, (
            f"Of Flesh and Blood applied to piece {piece_id}. "
            "It will summon Peons on the next 2 squares it leaves."
        )
class ForcedMove(Card):
    """
    Forced: Move
    ------------
    User is able to play another card this turn.
    Opponent is forced to move on their next turn (cannot play a card first).

    """

    def __init__(self):
        super().__init__(
            id="forced_move",
            name="Forced: Move",
            description=(
                "Play this card without ending your card phase. You may play another "
                "card this turn, and on your opponent's next turn they must make a "
                "board move before playing any cards."
            ),
            big_img="static/cards/forced_move_big.png",
            small_img="static/cards/forced_move_small.png"
        )
        # No target required for this card
        self.target_type = TargetType.NONE

    @property
    def card_type(self) -> CardType:
        # Assumes you have CardType.FORCED defined.
        # If not, you can change this to CardType.ACTIVE or the appropriate enum.
        return CardType.FORCED

    # ------------------------------------------------------------------
    # Card can always be played (no board / piece precondition)
    # ------------------------------------------------------------------
    def can_play(self, board: Board, player: Player) -> bool:
        # If you have per-turn card limits or phase checks, you can add them here.
        return True

    # ------------------------------------------------------------------
    # APPLY EFFECT
    # ------------------------------------------------------------------
    def apply_effect(
        self, board: Board, player: Player, target_data: Dict[str, Any]
    ) -> tuple[bool, str]:

        gs = board.game_state
        color = player.color
        opponent_color = Color.BLACK if color == Color.WHITE else Color.WHITE

        # --------------------------------------------------------------
        # 1) Give current player an extra card play this turn
        # --------------------------------------------------------------
        if not hasattr(gs, "extra_card_play"):
            # maps Color -> int (remaining extra card plays this turn)
            gs.extra_card_play = {}

        gs.extra_card_play[color] = gs.extra_card_play.get(color, 0) + 1

        # --------------------------------------------------------------
        # 2) Mark that opponent is forced to move on their next turn
        # --------------------------------------------------------------
        if not hasattr(gs, "forced_move_next_turn"):
            # maps Color -> bool (whether color must move before playing a card)
            gs.forced_move_next_turn = {}

        gs.forced_move_next_turn[opponent_color] = True

        return (
            True,
            "You may immediately play another card. Your opponent will be forced to "
            "make a move before playing any cards on their next turn."
        )




    def _create_transformed_piece(self, old_piece: Piece, new_type: PieceType, 
                                   coord: Coordinate, color: Color) -> Optional[Piece]:
        """
        Create a new piece of the specified type, preserving relevant attributes.
        """
        # Generate unique ID
        new_piece_id = f"{color.value}_{new_type.name}_{coord.to_algebraic()}"
        
        # Map piece types to their classes
        piece_class_map = {
            PieceType.PAWN: Pawn,
            PieceType.PEON: Peon,
            PieceType.KNIGHT: Knight,
            PieceType.BISHOP: Bishop,
            PieceType.ROOK: Rook,
            PieceType.QUEEN: Queen,
            PieceType.SCOUT: Scout,
            PieceType.HEADHUNTER: HeadHunter,
            PieceType.WARLOCK: Warlock,
            PieceType.WITCH: Witch,
            PieceType.CLERIC: Cleric,
            PieceType.DARKLORD: DarkLord,
        }

        piece_class = piece_class_map.get(new_type)
        if not piece_class:
            return None

        # Create new piece
        new_piece = piece_class(new_piece_id, color)

        # Preserve has_moved status if both pieces support it
        # (Important for castling rights on Rooks)
        if hasattr(old_piece, 'has_moved') and hasattr(new_piece, 'has_moved'):
            new_piece.has_moved = old_piece.has_moved

        return new_piece
    
    def handle_query(self, board: 'Board', player: 'Player', action: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle frontend queries for Transmute card.
        
        Supported actions:
            - "get_options": Get available transformations for a target piece
                Required data: {"target_square": "e4"}
                Returns: {"square": "e4", "current_type": "BISHOP", "value": 3, "options": [...]}
            
            - "get_valid_targets": Get all pieces that can be transmuted
                Returns: {"valid_targets": ["e4", "d1", ...]}
        """
        if action == "get_options":
            target_square = data.get("target_square")
            if not target_square:
                return None
            return self.get_transmute_options(board, player, target_square)
        
        elif action == "get_valid_targets":
            # Return all squares with transmutable pieces
            valid_targets = []
            for coord, piece in board.squares.items():
                if piece.color == player.color and self._is_transmutable(piece):
                    valid_targets.append(coord.to_algebraic())
            return {"valid_targets": valid_targets}
        
        return None
    


# ============================================================================
# CARD REGISTRY - Map card IDs to card classes
# ============================================================================

CARD_REGISTRY = {
    "mine": Mine,
    "glue": Glue,
    "eye_for_an_eye": EyeForAnEye,
    "summon_peon": SummonPeon,
    "pawn_scout": TransformToScout,
    "knight_headhunter": TransformToHeadhunter,
    "bishop_warlock": TransformToWarlock,
    "queen_darklord": TransformToDarkLord,
    "forbidden_lands": ForbiddenLands,
    "pawn_queen": PawnQueen,
    "pawn_bomb": PawnBomb,
    "shroud": Shroud,
    "all_seeing": AllSeeing,
    "summon_barricade": SummonBarricade,
    "insurance": Insurance,
    "transmute": Transmute,
    "of_flesh_and_blood": OfFleshAndBlood,
    "exhaustion": Exhaustion,
    "forced_move": ForcedMove,
    "eye_of_ruin": EyeOfRuin

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

