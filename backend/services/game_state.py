from datetime import datetime
from typing import Dict, List, Optional
from backend.enums import Color, GameStatus, PieceType
from backend.chess.board import Board
from backend.player import Player
from backend.cards.deck import Deck
from backend.chess.move import Move
from backend.chess.coordinate import Coordinate


class GameState:
    def __init__(self, game_id: str, white_player: Player, black_player: Player):
        # Game identification
        self.game_id: str = game_id
        self.status: GameStatus = GameStatus.IN_PROGRESS
        
        # Chess board
        self.board: Board = Board()  # Assumes Board() initializes standard setup
        Board.setup_standard(self.board)
        
        # Players
        self.players: Dict[Color, Player] = {
            Color.WHITE: white_player,
            Color.BLACK: black_player
        }
        
        # Turn tracking
        self.turn: Color = Color.WHITE  # White goes first
        self.halfmove_clock: int = 0  # For fifty-move rule
        self.fullmove_number: int = 1  # Starts at 1
        
        # Move history
        self.move_history: List[Move] = []
        
        # Timestamps
        self.created_at: datetime = datetime.now()
        self.last_update: datetime = datetime.now()
        
        # Timers (15 minutes = 900 seconds per player)
        self.white_time_remaining: float = 900.0
        self.black_time_remaining: float = 900.0
        self.last_move_time: datetime = datetime.now()
        
        # Game end tracking
        self.winner: Optional[Color] = None
        self.win_reason: Optional[str] = None

    # --- Helper Methods ---
    def get_current_player(self) -> Player:
        """Get the player whose turn it is"""
        return self.players[self.turn]
    
    def get_opponent_player(self) -> Player:
        """Get the player who is NOT currently moving"""
        opponent_color = Color.BLACK if self.turn == Color.WHITE else Color.WHITE
        return self.players[opponent_color]
    
    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        """Find a player by their ID"""
        for player in self.players.values():
            if player.id == player_id:
                return player
        return None
    
    def get_player_color(self, player_id: str) -> Optional[Color]:
        """Get the color for a given player ID"""
        for color, player in self.players.items():
            if player.id == player_id:
                return color
        return None
    
    def is_players_turn(self, player_id: str) -> bool:
        """Check if it's this player's turn"""
        return self.get_current_player().id == player_id

    # --- Timer Management ---
    def update_timer(self) -> None:
        """Update the timer for the current player"""
        now = datetime.now()
        elapsed = (now - self.last_move_time).total_seconds()
        
        if self.turn == Color.WHITE:
            self.white_time_remaining -= elapsed
            if self.white_time_remaining <= 0:
                self.status = GameStatus.TIMEOUT
                self.winner = Color.BLACK
                self.win_reason = "White ran out of time"
        else:
            self.black_time_remaining -= elapsed
            if self.black_time_remaining <= 0:
                self.status = GameStatus.TIMEOUT
                self.winner = Color.WHITE
                self.win_reason = "Black ran out of time"
        
        self.last_move_time = now
        self.last_update = now
    
    def switch_turn(self) -> None:
        """Switch to the other player's turn"""
        self.update_timer()
        self.turn = Color.BLACK if self.turn == Color.WHITE else Color.WHITE
        self.last_move_time = datetime.now()
        
        # Update fullmove number (increments after black's move)
        if self.turn == Color.WHITE:
            self.fullmove_number += 1

    # --- Move Methods ---
    def legal_moves_for(self, coord: Coordinate) -> List[Move]:
        """Get all legal moves for the piece at the given coordinate"""
        piece = self.board.piece_at_coord(coord)
        if not piece:
            return []
        
        # Get pseudo-legal moves from the piece
        moves = piece.get_legal_moves(self.board, coord)
        
        # TODO: Filter out moves that leave king in check
        # legal_moves = [m for m in moves if not self.leaves_king_in_check(m)]
        
        return moves

    def is_legal(self, m: Move) -> bool:
        """Check if a move is legal in the current position"""
        legal_moves = self.legal_moves_for(m.from_sq)
        return m in legal_moves

    def apply_move(self, player_id: str, m: Move) -> tuple[bool, str]:
        """
        Apply a move to the board.
        Returns (success, message)
        """
        # Verify it's this player's turn
        if not self.is_players_turn(player_id):
            return False, "Not your turn"
        
        # Update timer
        self.update_timer()
        if self.status == GameStatus.TIMEOUT:
            return False, "Time expired"
        
        # Verify the piece belongs to the current player
        piece = self.board.piece_at_coord(m.from_sq)
        if not piece or piece.color != self.turn:
            return False, "Invalid piece selection"
        
        # Get legal moves for debugging
        legal_moves = self.legal_moves_for(m.from_sq)
        print(f"DEBUG: Piece at {m.from_sq.to_algebraic()}: {piece}")
        print(f"DEBUG: Legal moves count: {len(legal_moves)}")
        for move in legal_moves:
            print(f"  - {move.from_sq.to_algebraic()} -> {move.to_sq.to_algebraic()}")
        print(f"DEBUG: Attempting move: {m.from_sq.to_algebraic()} -> {m.to_sq.to_algebraic()}")
        
        # Verify move is legal
        if not self.is_legal(m):
            return False, "Illegal move"
        
        # Execute the move on the board
        captured = self.board.move_piece(m)
        
        # Update halfmove clock (resets on capture or pawn move)
        if captured or piece.type == PieceType.PAWN:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        
        # Add to move history
        self.move_history.append(m)
        self.last_update = datetime.now()
        
        # Check for game-ending conditions
        self.check_end_conditions()
        
        # Switch turns if game is still in progress
        if self.status == GameStatus.IN_PROGRESS:
            self.switch_turn()
        
        return True, "Move successful"

    # --- Card Methods ---
    def play_card(self, player_id: str, card_id: str, target) -> tuple[bool, str]:
        """
        Play a card from the player's hand.
        Returns (success, message)
        """
        # Verify it's this player's turn
        if not self.is_players_turn(player_id):
            return False, "Not your turn"
        
        # Update timer
        self.update_timer()
        if self.status == GameStatus.TIMEOUT:
            return False, "Time expired"
        
        player = self.get_player_by_id(player_id)
        if not player:
            return False, "Player not found"
        
        # Verify player has the card
        if not player.has_card(card_id):
            return False, "Card not in hand"
        
        # Apply the card effect
        success, message = self._apply_card_effect(player, card_id, target)
        
        if success:
            # Remove card from hand, add to discard
            player.play_card(card_id)
            
            # Draw a new card if deck has cards
            player.draw_card()
            
            # Record in history (optional: track card plays)
            self.last_update = datetime.now()
            
            # Check for game-ending conditions
            self.check_end_conditions()
            
            # Switch turns if game is still in progress
            if self.status == GameStatus.IN_PROGRESS:
                self.switch_turn()
        
        return success, message
    
    def _apply_card_effect(self, player: Player, card_id: str, target) -> tuple[bool, str]:
        """
        Apply the effect of a specific card.
        This is where you implement each card's unique ability.
        """
        # TODO: Implement card effects based on card_id
        # This will vary greatly depending on card designs
        
        # Example structure:
        # card = get_card_by_id(card_id)
        # return card.apply_effect(self.board, target)
        
        return False, f"Card '{card_id}' not implemented yet"

    # --- Game End Conditions ---
    def check_end_conditions(self) -> GameStatus:
        """
        Check if the game has ended (checkmate, stalemate, draw).
        Updates self.status, self.winner, and self.win_reason.
        Returns the current game status.
        """
        # TODO: Implement using Board class
        
        # Check for checkmate
        # if self.board.is_checkmate(self.turn):
        #     self.status = GameStatus.CHECKMATE
        #     self.winner = Color.BLACK if self.turn == Color.WHITE else Color.WHITE
        #     self.win_reason = "Checkmate"
        #     return self.status
        
        # Check for stalemate
        # if self.board.is_stalemate(self.turn):
        #     self.status = GameStatus.STALEMATE
        #     self.win_reason = "Stalemate"
        #     return self.status


        # Check for insufficient material
        # if self.board.insufficient_material():
        #     self.status = GameStatus.DRAW
        #     self.win_reason = "Insufficient material"
        #     return self.status
        
        return self.status

    # --- Serialization ---
    def to_dict(self, perspective_player_id: Optional[str] = None) -> dict:
        """
        Convert game state to dictionary for JSON serialization.
        If perspective_player_id is provided, include only info that player should see.
        """
        base_dict = {
            "game_id": self.game_id,
            "status": self.status.value,
            "current_turn": self.turn.value,
            "board": self.board.to_dict(),
            "white_time": self.white_time_remaining,
            "black_time": self.black_time_remaining,
            "halfmove_clock": self.halfmove_clock,
            "fullmove_number": self.fullmove_number,
            "move_history": [m.to_dict() for m in self.move_history[-10:]],  # Last 10 moves
            "winner": self.winner.value if self.winner else None,
            "win_reason": self.win_reason,
            "created_at": self.created_at.isoformat(),
            "last_update": self.last_update.isoformat()
        }
        
        # If perspective is provided, add player-specific info
        if perspective_player_id:
            player = self.get_player_by_id(perspective_player_id)
            player_color = self.get_player_color(perspective_player_id)
            opponent_color = Color.BLACK if player_color == Color.WHITE else Color.WHITE
            opponent = self.players[opponent_color]
            
            if player:
                base_dict["your_color"] = player_color.value
                base_dict["your_turn"] = self.is_players_turn(perspective_player_id)
                base_dict["your_hand"] = player.get_hand()
                base_dict["your_deck_size"] = player.deck_size()
                base_dict["opponent_hand_size"] = opponent.hand_size()
                base_dict["opponent_deck_size"] = opponent.deck_size()
        
        return base_dict