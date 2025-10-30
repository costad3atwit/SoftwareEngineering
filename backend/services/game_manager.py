"""
GameManager - Handles the complete lifecycle of games
- Matchmaking
- Game creation with deck building
- Game state management
- Timer updates
"""

from typing import Dict, Optional, List, Tuple
import asyncio
from datetime import datetime
from backend.services.game_state import GameState, GameStatus
from backend.player import Player
from backend.cards.deck import Deck
from backend.cards.card import Card
from backend.enums import Color


class GameManager:
    """Manages all active games and matchmaking"""
    
    def __init__(self):
        self.games: Dict[str, GameState] = {}
        self.matchmaking_queue: List[Dict] = []  # Queue of players waiting to be matched
        self._timer_task: Optional[asyncio.Task] = None
        self._game_counter = 0  # For unique game IDs
    
    # ============================================================================
    # MATCHMAKING
    # ============================================================================
    
    def add_to_queue(self, player_id: str, player_name: str, deck_card_ids: List[str]) -> Tuple[bool, str]:
        """
        Add a player to the matchmaking queue with their deck.
        Returns (success, message)
        """
        # Validate deck size (16 cards per requirements)
        if len(deck_card_ids) != 16:
            return False, f"Deck must contain exactly 16 cards (got {len(deck_card_ids)})"
        
        # Check if player already in queue
        if any(p["player_id"] == player_id for p in self.matchmaking_queue):
            return False, "Already in matchmaking queue"
        
        # Check if player already in a game
        if self.get_player_game(player_id):
            return False, "Already in an active game"
        
        # Add to queue
        self.matchmaking_queue.append({
            "player_id": player_id,
            "player_name": player_name,
            "deck_card_ids": deck_card_ids,
            "joined_at": datetime.now()
        })
        
        return True, f"Added to queue at position {len(self.matchmaking_queue)}"
    
    def remove_from_queue(self, player_id: str) -> bool:
        """Remove a player from the matchmaking queue"""
        original_length = len(self.matchmaking_queue)
        self.matchmaking_queue = [p for p in self.matchmaking_queue if p["player_id"] != player_id]
        return len(self.matchmaking_queue) < original_length
    
    def try_match_players(self) -> Optional[GameState]:
        """
        Try to match two players from the queue and start a game.
        Returns the created GameState if successful, None otherwise.
        """
        if len(self.matchmaking_queue) < 2:
            return None
        
        # Get first two players in queue
        player1_data = self.matchmaking_queue.pop(0)
        player2_data = self.matchmaking_queue.pop(0)
        
        # Create the game
        game = self.start_game(
            player1_id=player1_data["player_id"],
            player1_name=player1_data["player_name"],
            player1_deck_ids=player1_data["deck_card_ids"],
            player2_id=player2_data["player_id"],
            player2_name=player2_data["player_name"],
            player2_deck_ids=player2_data["deck_card_ids"]
        )
        
        return game
    
    # ============================================================================
    # GAME CREATION
    # ============================================================================
    
    def start_game(self, player1_id: str, player1_name: str, player1_deck_ids: List[str],
                   player2_id: str, player2_name: str, player2_deck_ids: List[str]) -> GameState:
        """
        Start a new game between two players.
        Creates Player objects with their decks and initializes the game.
        """
        # Generate unique game ID
        self._game_counter += 1
        game_id = f"game_{self._game_counter}_{player1_id[:8]}_{player2_id[:8]}"
        
        # Create decks from card IDs
        deck1 = self._create_deck_from_ids(player1_deck_ids)
        deck2 = self._create_deck_from_ids(player2_deck_ids)
        
        # Create Player objects
        player1 = Player(player1_id, player1_name, Color.WHITE, deck1)
        player2 = Player(player2_id, player2_name, Color.BLACK, deck2)
        
        # Create GameState
        game = GameState(game_id, player1, player2)
        
        # Store game
        self.games[game_id] = game
        
        print(f"✓ Game {game_id} created: {player1_name} (White) vs {player2_name} (Black)")
        
        return game
    
    def _create_deck_from_ids(self, card_ids: List[str]) -> Deck:
        """
        Create a Deck object from a list of card IDs.
        TODO: Replace with actual card loading from card database/registry
        """
        deck = Deck()
        
        for card_id in card_ids:
            # TODO: Load actual card from card registry
            # For now, create placeholder cards
            card = self._create_card_by_id(card_id)
            deck.add(card)
        
        return deck
    
    def _create_card_by_id(self, card_id: str) -> Card:
        """
        Create a Card object by ID.
        TODO: Implement actual card loading from a card database/registry
        """
        # Placeholder - replace this with actual card data
        # Example: return CARD_REGISTRY.get(card_id)
        
        # For now, create a basic card
        return Card(id=card_id, name=card_id.replace("_", " ").title())
    
    def create_sample_game(self, player1_id: str = "alice", player2_id: str = "bob") -> GameState:
        """
        Create a sample game with predefined decks for testing.
        Useful for development and testing without full UI.
        """
        sample_deck = [
            "transform_pawn", "king_switch", "summon_peon", "safe_zone",
            "teleport_knight", "double_move", "freeze_piece", "sacrifice",
            "heal_king", "destroy_square", "swap_pieces", "mirror_move",
            "time_warp", "lightning_strike", "shield_barrier", "cursed_effigy"
        ]
        
        return self.start_game(
            player1_id=player1_id,
            player1_name=player1_id.capitalize(),
            player1_deck_ids=sample_deck,
            player2_id=player2_id,
            player2_name=player2_id.capitalize(),
            player2_deck_ids=sample_deck  # Same deck for simplicity
        )
    
    # ============================================================================
    # GAME RETRIEVAL
    # ============================================================================
    
    def get_game(self, game_id: str) -> Optional[GameState]:
        """Get a game by its ID"""
        return self.games.get(game_id)
    
    def get_player_game(self, player_id: str) -> Optional[GameState]:
        """Find the active game a player is currently in"""
        for game in self.games.values():
            if game.get_player_by_id(player_id):
                return game
        return None
    
    def get_all_active_games(self) -> List[GameState]:
        """Get all games that are still in progress"""
        return [
            game for game in self.games.values() 
            if game.status == GameStatus.IN_PROGRESS
        ]
    
    # ============================================================================
    # GAME LIFECYCLE
    # ============================================================================
    
    def end_game(self, game_id: str) -> bool:
        """
        Mark a game as ended and perform cleanup.
        Returns True if game was found and ended.
        """
        game = self.get_game(game_id)
        if not game:
            return False
        
        # Game might already be ended
        if game.status == GameStatus.IN_PROGRESS:
            game.status = GameStatus.FORFEIT
            game.win_reason = "Game manually ended"
        
        print(f"✓ Game {game_id} ended: {game.status.value}")
        return True
    
    def remove_game(self, game_id: str) -> bool:
        """
        Remove a game from active games (for cleanup).
        Returns True if game was removed.
        """
        if game_id in self.games:
            del self.games[game_id]
            print(f"✓ Game {game_id} removed from active games")
            return True
        return False
    
    def cleanup_finished_games(self) -> int:
        """
        Remove all games that have ended.
        Returns number of games removed.
        """
        finished_games = [
            game_id for game_id, game in self.games.items()
            if game.status != GameStatus.IN_PROGRESS
        ]
        
        for game_id in finished_games:
            self.remove_game(game_id)
        
        return len(finished_games)
    
    # ============================================================================
    # GAME ACTIONS (Delegate to GameState)
    # ============================================================================
    
    def make_move(self, game_id: str, player_id: str, from_square: str, to_square: str) -> Tuple[bool, str, Optional[GameState]]:
        """
        Make a move in a game.
        Returns (success, message, updated_game_state)
        """
        game = self.get_game(game_id)
        if not game:
            return False, "Game not found", None
        
        # TODO: Parse coordinates and create Move object
        # For now, return not implemented
        return False, "Move functionality requires Coordinate.from_algebraic() implementation", game
    
    def play_card(self, game_id: str, player_id: str, card_id: str, target_data: dict) -> Tuple[bool, str, Optional[GameState]]:
        """
        Play a card in a game.
        Returns (success, message, updated_game_state)
        """
        game = self.get_game(game_id)
        if not game:
            return False, "Game not found", None
        
        success, message = game.play_card(player_id, card_id, target_data)
        return success, message, game
    
    # ============================================================================
    # TIMER MANAGEMENT
    # ============================================================================
    
    async def start_timer_updates(self, callback=None):
        """
        Start a background task that updates all game timers every second.
        callback: Optional async function called when a game times out
        """
        async def update_timers():
            while True:
                await asyncio.sleep(1)  # Update every second
                
                for game in self.games.values():
                    if game.status == GameStatus.IN_PROGRESS:
                        game.update_timer()
                        
                        # If game just timed out, notify via callback
                        if game.status == GameStatus.TIMEOUT and callback:
                            await callback(game)
        
        self._timer_task = asyncio.create_task(update_timers())
        print("✓ Timer update task started")
    
    def stop_timer_updates(self):
        """Stop the timer update background task"""
        if self._timer_task:
            self._timer_task.cancel()
            print("✓ Timer update task stopped")
    
    # ============================================================================
    # STATISTICS & INFO
    # ============================================================================
    
    def get_stats(self) -> dict:
        """Get statistics about current games and queue"""
        return {
            "total_games": len(self.games),
            "active_games": len(self.get_all_active_games()),
            "finished_games": len(self.games) - len(self.get_all_active_games()),
            "queue_size": len(self.matchmaking_queue),
            "total_players": len(self.matchmaking_queue) + (len(self.games) * 2)
        }
    
    def __repr__(self):
        stats = self.get_stats()
        return f"<GameManager: {stats['active_games']} active, {stats['queue_size']} in queue>"