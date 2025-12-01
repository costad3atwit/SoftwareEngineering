from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from typing import Dict, List, Optional
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import uuid

from backend.services.game_manager import GameManager
from backend.enums import GameStatus, Color
from backend.services.game_state import GameState

# ============================================================================
# LOGGING SETUP
# ============================================================================

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Configure logging
log_filename = log_dir / f"server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()  # Also print to console
    ]
)

logger = logging.getLogger(__name__)
logger.info("="*60)
logger.info("ARCANE CHESS SERVER STARTING")
logger.info("="*60)

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI()

# Serve static files (your frontend)
base_dir = Path(__file__).resolve().parent.parent
frontend_dir = base_dir / "frontend"
static_dir = base_dir / "static"

# Mount static directories if they exist
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")
    logger.info(f"Mounted frontend directory: {frontend_dir}")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info(f"Mounted static directory: {static_dir}")

# Initialize game manager
game_manager = GameManager()

active_challenges: Dict[str, Dict] = {}

# ============================================================================
# CONNECTION MANAGER
# ============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client connected: {client_id} | Total connections: {len(self.active_connections)}")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        # Remove from matchmaking queue if present
        removed = game_manager.remove_from_queue(client_id)
        if removed:
            logger.info(f"Removed {client_id} from matchmaking queue")
        
        # Clean up any challenges involving this player
        challenges_to_remove = []
        for key, challenge in active_challenges.items():
            if challenge["challenger_id"] == client_id or challenge["target_id"] == client_id:
                challenges_to_remove.append(key)
        
        for key in challenges_to_remove:
            del active_challenges[key]
            logger.info(f"Removed challenge: {key}")
        
        logger.info(f"Client disconnected: {client_id} | Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message)
                logger.info(f"Sent to {client_id}: {message['type']}")  # Changed from debug to info
            except Exception as e:
                logger.error(f"Error sending to {client_id}: {e}", exc_info=True)
        else:
            logger.warning(f"Cannot send to {client_id}: not in active connections")
    
    async def broadcast_to_game(self, message: dict, game: GameState):
        """Send message to both players in a game"""
        white_player = game.players[game.turn if game.turn else GameStatus.IN_PROGRESS]
        black_player = game.get_opponent_player()
        
        for player in [white_player, black_player]:
            await self.send_personal_message(message, player.id)
        logger.info(f"Broadcast to game {game.game_id}: {message['type']}")

manager = ConnectionManager()

async def notify_game_timeout(game: GameState):
    """Callback for when a game times out"""
    logger.warning(f"Game timeout: {game.game_id} | Winner: {game.winner.value if game.winner else 'None'}")
    await manager.broadcast_to_game({
        "type": "game_over",
        "reason": "timeout",
        "winner": game.winner.value if game.winner else None,
        "message": game.win_reason
    }, game)
    # Try to match waiting players since a game slot opened up
    await try_match_waiting_players()

async def try_match_waiting_players():
    """
    Helper function to attempt matchmaking after a game slot opens up.
    Called after games end to match any waiting players.
    """
    game = game_manager.try_match_players()
    
    if game:
        # Get both players
        white_player = game.players[game.turn]
        black_player = game.get_opponent_player()
        
        logger.info(f"MATCH CREATED (slot opened): {game.game_id}")
        logger.info(f"  White: {white_player.name} ({white_player.id})")
        logger.info(f"  Black: {black_player.name} ({black_player.id})")
        
        # Notify both players with their perspective of game state
        await manager.send_personal_message({
            "type": "game_started",
            "game_id": game.game_id,
            "game_state": game.to_dict(white_player.id)
        }, white_player.id)
        
        await manager.send_personal_message({
            "type": "game_started",
            "game_id": game.game_id,
            "game_state": game.to_dict(black_player.id)
        }, black_player.id)


# ============================================================================
# HTTP ENDPOINTS
# ============================================================================

@app.get("/")
async def get():
    """Redirect to main menu"""
    return RedirectResponse(url="/frontend/pages/html/main_menu.html")

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    await game_manager.start_timer_updates(notify_game_timeout)
    logger.info("Timer updates enabled")
    logger.info(f"Log file: {log_filename}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background tasks"""
    game_manager.stop_timer_updates()
    logger.info("Server shutting down - cleaned up background tasks")

@app.get("/status")
async def status():
    """Get server status"""
    stats = game_manager.get_stats()
    return {
        "connections": len(manager.active_connections),
        "queue": stats["queue_size"],
        "active_games": stats["active_games"],
        "total_games": stats["total_games"],
        "finished_games": stats["finished_games"]
    }

@app.get("/get_player_id")
async def get_player_id():
    """Generate a unique player ID for a new client"""
    player_id = f"player_{uuid.uuid4().hex[:8]}"
    logger.info(f"Generated new player ID: {player_id}")
    return {
        "player_id": player_id
    }

@app.post("/test/create_sample_game")
async def create_sample_game():
    """Create a sample game for testing (no WebSocket needed)"""
    game = game_manager.create_sample_game()
    logger.info(f"Sample game created via HTTP: {game.game_id}")
    return {
        "success": True,
        "game_id": game.game_id,
        "game_state": game.to_dict()
    }

@app.get("/game/{game_id}")
async def get_game_state(game_id: str, player_id: str = None):
    """Get the state of a specific game"""
    game = game_manager.get_game(game_id)
    if not game:
        logger.warning(f"Game state request for nonexistent game: {game_id}")
        return {"error": "Game not found"}
    
    logger.info(f"Game state requested: {game_id} by {player_id if player_id else 'anonymous'}")
    return {
        "success": True,
        "game_state": game.to_dict(player_id) if player_id else game.to_dict()
    }

# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            logger.info(f"Message from {client_id}: {message_type}")
            
            if message_type == "join_queue":
                # Player submits their deck and joins queue
                player_name = message.get("name", client_id)
                deck = message.get("deck", ["forbidden_lands", "eye_for_an_eye", "summon_peon", "pawn_scout",
            "knight_headhunter", "bishop_warlock",
            "mine", "eye_for_an_eye", "summon_peon", "pawn_scout",
            "knight_headhunter", "bishop_warlock",
            "forbidden_lands", "eye_for_an_eye", "summon_peon", "pawn_scout"]) 
                # ^^^ REPLACE WITH ACTUAL DECK DATA, THIS IS USED AS A FALLBACK INCASE FRONTEND DOESN"T SEND A DECK IN MAIN_MENU.js
                
                logger.info(f"Join queue request: {client_id} ({player_name}) with {len(deck)} cards")
                
                # Validate deck (16 cards)
                if len(deck) != 16:
                    error_msg = f"Deck must contain exactly 16 cards (got {len(deck)})"
                    logger.warning(f"Invalid deck from {client_id}: {error_msg}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": error_msg
                    }, client_id)
                    continue
                
                # Add player to matchmaking queue
                success, msg = game_manager.add_to_queue(client_id, player_name, deck)
                
                if success:
                    logger.info(f"Added to queue: {client_id} | {msg}")
                    active_count = len(game_manager.get_all_active_games())
                    waiting_for_slot = active_count >= 20
                    
                    await manager.send_personal_message({
                        "type": "queue_joined",
                        "message": msg,
                        "queue_size": len(game_manager.matchmaking_queue),
                        "active_games": active_count,
                        "max_games": 20,
                        "waiting_for_slot": waiting_for_slot
                    }, client_id)
                    
                    # Try to match players
                    game = game_manager.try_match_players()
                    
                    if game:
                        # Get both players
                        white_player = game.players[game.turn]
                        black_player = game.get_opponent_player()
                        
                        logger.info(f"MATCH CREATED: {game.game_id}")
                        logger.info(f"  White: {white_player.name} ({white_player.id})")
                        logger.info(f"  Black: {black_player.name} ({black_player.id})")
                        
                        # Notify both players with their perspective of game state
                        await manager.send_personal_message({
                            "type": "game_started",
                            "game_id": game.game_id,
                            "game_state": game.to_dict(white_player.id)
                        }, white_player.id)
                        
                        await manager.send_personal_message({
                            "type": "game_started",
                            "game_id": game.game_id,
                            "game_state": game.to_dict(black_player.id)
                        }, black_player.id)
                else:
                    logger.warning(f"Failed to add to queue: {client_id} | {msg}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": msg
                    }, client_id)
            elif message_type == "leave_queue":
                # Player wants to leave the matchmaking queue
                removed = game_manager.remove_from_queue(client_id)
                if removed:
                    logger.info(f"Player left queue: {client_id}")
                    await manager.send_personal_message({
                        "type": "queue_left",
                        "message": "You have left the matchmaking queue"
                    }, client_id)
                
            elif message_type == "send_challenge":
                # Player wants to challenge another player directly
                target_player_id = message.get("target_player_id")
                challenger_name = message.get("challenger_name", client_id)
                deck = message.get("deck", [])
                
                logger.info(f"Challenge request: {client_id} -> {target_player_id}")
                
                # Validate deck
                if len(deck) != 16:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Invalid deck size: {len(deck)}"
                    }, client_id)
                    continue
                
                # Check if target player exists and is connected
                if target_player_id not in manager.active_connections:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Player {target_player_id} is not online"
                    }, client_id)
                    continue
                
                # Check if target is already in a game
                if game_manager.get_player_game(target_player_id):
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Player {target_player_id} is already in a game"
                    }, client_id)
                    continue
                # Check if server is at capacity (20 concurrent games)
                active_count = len(game_manager.get_all_active_games())
                if active_count >= 20:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Server at capacity ({active_count}/20 games). Please wait for a slot to open."
                    }, client_id)
                    continue
                
                # Check if challenger is already in a game
                if game_manager.get_player_game(client_id):
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "You are already in a game"
                    }, client_id)
                    continue
                
                # Store the challenge
                challenge_key = f"{client_id}_{target_player_id}"
                active_challenges[challenge_key] = {
                    "challenger_id": client_id,
                    "challenger_name": challenger_name,
                    "challenger_deck": deck,
                    "target_id": target_player_id
                }
                
                # Send challenge notification to target player
                await manager.send_personal_message({
                    "type": "challenge_received",
                    "challenger_id": client_id,
                    "challenger_name": challenger_name
                }, target_player_id)
                
                logger.info(f"Challenge sent: {client_id} -> {target_player_id}")
                
            elif message_type == "accept_challenge":
                # Player accepts a challenge
                challenger_id = message.get("challenger_id")
                accepter_name = message.get("accepter_name", client_id)
                deck = message.get("deck", [])
                
                logger.info(f"Challenge accepted: {challenger_id} <- {client_id}")
                
                # Validate deck
                if len(deck) != 16:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Invalid deck size: {len(deck)}"
                    }, client_id)
                    continue
                
                # Find the challenge
                challenge_key = f"{challenger_id}_{client_id}"
                challenge = active_challenges.get(challenge_key)
                
                if not challenge:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Challenge not found or expired"
                    }, client_id)
                    continue
                # Check if server is at capacity (20 concurrent games)
                active_count = len(game_manager.get_all_active_games())
                if active_count >= 20:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Server at capacity ({active_count}/20 games). Challenge cannot be accepted right now."
                    }, client_id)
                    # Notify the challenger too
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Challenge to {client_id} failed: server at capacity"
                    }, challenger_id)
                    continue
                # Remove from matchmaking queue if present
                game_manager.remove_from_queue(challenger_id)
                game_manager.remove_from_queue(client_id)
                
                # Create the game
                game = game_manager.start_game(
                    player1_id=challenger_id,
                    player1_name=challenge["challenger_name"],
                    player1_deck_ids=challenge["challenger_deck"],
                    player2_id=client_id,
                    player2_name=accepter_name,
                    player2_deck_ids=deck
                )
                
                # Get both players
                white_player = game.players[Color.WHITE]
                black_player = game.players[Color.BLACK]
                
                logger.info(f"CHALLENGE GAME CREATED: {game.game_id}")
                logger.info(f"  White: {white_player.name} ({white_player.id})")
                logger.info(f"  Black: {black_player.name} ({black_player.id})")
                
                # Notify both players
                await manager.send_personal_message({
                    "type": "game_started",
                    "game_id": game.game_id,
                    "game_state": game.to_dict(white_player.id)
                }, white_player.id)
                
                await manager.send_personal_message({
                    "type": "game_started",
                    "game_id": game.game_id,
                    "game_state": game.to_dict(black_player.id)
                }, black_player.id)
                
                # Clean up challenge
                del active_challenges[challenge_key]
                
            elif message_type == "decline_challenge":
                # Player declines a challenge
                challenger_id = message.get("challenger_id")
                
                logger.info(f"Challenge declined: {challenger_id} <- {client_id}")
                
                # Find and remove the challenge
                challenge_key = f"{challenger_id}_{client_id}"
                if challenge_key in active_challenges:
                    del active_challenges[challenge_key]
                
                # Notify challenger
                await manager.send_personal_message({
                    "type": "challenge_declined",
                    "decliner_id": client_id
                }, challenger_id)
            elif message_type == "make_move":
                # Handle piece movement
                game_id = message.get("game_id")
                from_square = message.get("from")
                to_square = message.get("to")
                
                logger.info(f"Move attempt: {client_id} in {game_id}: {from_square} -> {to_square}")
                
                game = game_manager.get_game(game_id)
                if not game:
                    logger.error(f"Move in nonexistent game: {game_id}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Game not found"
                    }, client_id)
                    continue
                
                # Use game_manager.make_move
                success, msg, updated_game = game_manager.make_move(
                    game_id, client_id, from_square, to_square
                )
                
                if success:
                    logger.info(f"Move successful: {from_square} -> {to_square} in {game_id}")
                    
                    white_player = updated_game.players[Color.WHITE]
                    black_player = updated_game.players[Color.BLACK]
                    
                    logger.info(f"DEBUG: About to send to white player: {white_player.id}")
                    logger.info(f"DEBUG: About to send to black player: {black_player.id}")
                    logger.info(f"DEBUG: Active connections: {list(manager.active_connections.keys())}")
                    
                    try:
                        # Serialize game state first to catch any errors
                        logger.info(f"DEBUG: Starting to serialize white state")
                        white_state = updated_game.to_dict(white_player.id)
                        logger.info(f"DEBUG: White state serialized successfully")
                        
                        logger.info(f"DEBUG: Starting to serialize black state")
                        black_state = updated_game.to_dict(black_player.id)
                        logger.info(f"DEBUG: Black state serialized successfully")
                        
                        # Broadcast updated game state to both players
                        await manager.send_personal_message({
                            "type": "game_update",
                            "action": "move",
                            "game_state": white_state
                        }, white_player.id)
                        logger.info(f"DEBUG: Sent to white player")
                        
                        await manager.send_personal_message({
                            "type": "game_update",
                            "action": "move",
                            "game_state": black_state
                        }, black_player.id)
                        logger.info(f"DEBUG: Sent to black player")
                        
                        logger.info(f"Sent game updates to both players")
                        
                    except Exception as e:
                        logger.error(f"ERROR sending game updates: {e}", exc_info=True)
                        import traceback
                        traceback.print_exc()
                    # Check if game is over
                    if updated_game.status != GameStatus.IN_PROGRESS:
                        logger.info(f"GAME OVER: {game_id} | Status: {updated_game.status.value}")
                        await manager.broadcast_to_game({
                            "type": "game_over",
                            "reason": updated_game.status.value,
                            "winner": updated_game.winner.value if updated_game.winner else None,
                            "message": updated_game.win_reason
                        }, updated_game)
                        # Try to match waiting players since a game slot opened up
                        await try_match_waiting_players()
                else:
                    logger.warning(f"Move failed: {msg}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": msg
                    }, client_id)
            elif message_type == "play_card":
                # Handle card play
                game_id = message.get("game_id")
                card_id = message.get("card_id")
                target_data = message.get("target", {})
                
                logger.info(f"Card play attempt: {client_id} in {game_id}: {card_id}")
                
                game = game_manager.get_game(game_id)
                if not game:
                    logger.error(f"Card play in nonexistent game: {game_id}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Game not found"
                    }, client_id)
                    continue
                
                # Use game_manager.play_card
                success, msg, updated_game = game_manager.play_card(
                    game_id, client_id, card_id, target_data
                )
                
                if success:
                    logger.info(f"Card played successfully: {card_id} in {game_id}")
                    
                    # Get both players correctly
                    white_player = updated_game.players[Color.WHITE]
                    black_player = updated_game.players[Color.BLACK]
                    
                    # Broadcast updated game state to both players
                    await manager.send_personal_message({
                        "type": "game_update",
                        "action": "card_played",
                        "card_id": card_id,
                        "game_state": updated_game.to_dict(white_player.id)
                    }, white_player.id)
                    
                    await manager.send_personal_message({
                        "type": "game_update",
                        "action": "card_played",
                        "card_id": card_id,
                        "game_state": updated_game.to_dict(black_player.id)
                    }, black_player.id)
                    
                    logger.info(f"Sent game updates to both players")
                    
                    # Check if game is over
                    if updated_game.status != GameStatus.IN_PROGRESS:
                        logger.info(f"GAME OVER: {game_id} | Status: {updated_game.status.value}")
                        await manager.broadcast_to_game({
                            "type": "game_over",
                            "reason": updated_game.status.value,
                            "winner": updated_game.winner.value if updated_game.winner else None,
                            "message": updated_game.win_reason
                        }, updated_game)
                        # Try to match waiting players since a game slot opened up
                        await try_match_waiting_players()
                else:
                    logger.warning(f"Card play failed: {msg}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": msg
                    }, client_id)
            elif message_type == "card_query":
                # Generic card query handler
                game_id = message.get("game_id")
                card_id = message.get("card_id")
                action = message.get("action")
                query_data = message.get("data", {})
                
                logger.info(f"Card query: {client_id} asking {card_id} for {action}")
                
                game = game_manager.get_game(game_id)
                if not game:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Game not found"
                    }, client_id)
                    continue
                
                # Delegate to game state
                response = game.get_card_metadata(client_id, card_id, action, query_data)
                
                if response:
                    await manager.send_personal_message({
                        "type": "card_query_response",
                        "card_id": card_id,
                        "action": action,
                        "data": response
                    }, client_id)
                else:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Invalid card query"
                    }, client_id)
            elif message_type == "get_promotion_options":
                # Generic promotion query
                game_id = message.get("game_id")
                square = message.get("square")
                
                game = game_manager.get_game(game_id)
                if game:
                    options = game.get_promotion_options(square)
                    if options:
                        await manager.send_personal_message({
                            "type": "promotion_options",
                            "data": options
                        }, client_id)
            elif message_type == "get_game_state":
                # Request current game state
                game_id = message.get("game_id")
                logger.info(f"Game state request: {client_id} for {game_id}")
                
                game = game_manager.get_game(game_id)
                
                if game:
                    try:
                        logger.info(f"DEBUG: Serializing game state for {client_id}")
                        game_state = game.to_dict(client_id)
                        logger.info(f"DEBUG: Game state serialized, sending to {client_id}")
                        
                        await manager.send_personal_message({
                            "type": "game_state",
                            "game_state": game_state
                        }, client_id)
                        logger.info(f"Sent game state to {client_id}")
                    except Exception as e:
                        logger.error(f"ERROR getting game state: {e}", exc_info=True)
                else:
                    logger.warning(f"Game state request for nonexistent game: {game_id}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Game not found"
                    }, client_id)            
            elif message_type == "ping":
                # Keep connection alive
                await manager.send_personal_message({"type": "pong"}, client_id)
            
            else:
                logger.warning(f"Unknown message type from {client_id}: {message_type}")
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"Client disconnected normally: {client_id}")
    except Exception as e:
        logger.error(f"Error with client {client_id}: {e}", exc_info=True)
        manager.disconnect(client_id)

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)