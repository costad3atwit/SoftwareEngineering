
from datetime import datetime
from typing import Dict, List
from enums import Color, GameStatus
from chess.board import Board
from player import Player
from cards.deck import Deck
from cards.discard_pile import DiscardPile
from chess.move import Move
from chess.coordinate import Coordinate


class GameState:
    def __init__(self):
        self.game_id: str
        self.status: GameStatus
        self.board: Board
        self.players: Dict[Color, Player]
        self.turn: Color
        self.halfmove_clock: int
        self.fullmove_number: int
        self.deck: Deck
        self.discard: DiscardPile
        self.move_history: List[Move]
        self.created_at: datetime
        self.last_update: datetime

    # --- Methods ---
    def legal_moves_for(self, coord: Coordinate) -> List[Move]:
        pass

    def apply_move(self, player_id: str, m: Move) -> None:
        pass

    def play_card(self, player_id: str, card_id: str, target) -> None:
        pass

    def draw_card(self, player_id: str) -> None:
        pass

    def is_legal(self, m: Move) -> bool:
        pass

    def check_end_conditions(self) -> GameStatus:
        pass

    def snapshot(self) -> dict:
        pass
