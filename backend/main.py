from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import Dict, List, Optional
import json
import asyncio
from pathlib import Path

from backend.game_manager import GameManager, Game, GameStatus

app = FastAPI()

# Serve static files (your frontend)
# Adjust path to point to frontend directory
base_dir = Path(__file__).resolve().parent.parent
frontend_dir = base_dir / "frontend"

# Only mount if frontend directory exists
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
else:
    print(f"Warning: Frontend directory not found at {frontend_dir}")

# Initialize game manager
game_manager = GameManager()

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.matchmaking_queue: List[Dict] = []  # Store player_id and their deck
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.matchmaking_queue:
            self.matchmaking_queue.remove(client_id)
        print(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_json(message)
    
    async def broadcast_to_game(self, message: dict, game: Game):
        """Send message to both players in a game"""
        for player_id in [game.white_player_id, game.black_player_id]:
            await self.send_personal_message(message, player_id)

manager = ConnectionManager()

async def notify_game_timeout(game: Game):
    """Callback for when a game times out"""
    await manager.broadcast_to_game({
        "type": "game_over",
        "reason": "timeout",
        "winner": game.winner,
        "message": game.win_reason
    }, game)

@app.get("/")
async def get():
    """Serve the main page"""
    return HTMLResponse("""
    <html>
        <head>
            <title>Arcane Chess</title>
        </head>
        <body>
            <h1>Arcane Chess Server</h1>
            <p>Server is running! Connect via WebSocket at ws://localhost:8000/ws/{client_id}</p>
            <p>Active connections: <span id="connections">0</span></p>
            <script>
                // Simple status page
                setInterval(() => {
                    fetch('/status')
                        .then(r => r.json())
                        .then(data => {
                            document.getElementById('connections').textContent = data.connections;
                        });
                }, 2000);
            </script>
        </body>
    </html>
    """)

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    await game_manager.start_timer_updates(notify_game_timeout)

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background tasks"""
    game_manager.stop_timer_updates()

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

@app.post("/test/create_sample_game")
async def create_sample_game():
    """Create a sample game for testing (no WebSocket needed)"""
    game = game_manager.create_sample_game()
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
        return {"error": "Game not found"}
    
    return {
        "success": True,
        "game_state": game.to_dict(player_id) if player_id else game.to_dict()
    }

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "join_queue":
                # Player submits their deck and joins queue
                deck = message.get("deck", [])
                
                # TODO: Validate deck (16 cards from available 32)
                if len(deck) != 16:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Deck must contain exactly 16 cards"
                    }, client_id)
                    continue
                
                # Add player to matchmaking queue
                if client_id not in [p["player_id"] for p in manager.matchmaking_queue]:
                    manager.matchmaking_queue.append({
                        "player_id": client_id,
                        "deck": deck
                    })
                    await manager.send_personal_message({
                        "type": "queue_joined",
                        "position": len(manager.matchmaking_queue)
                    }, client_id)
                
                # Try to match players
                if len(manager.matchmaking_queue) >= 2:
                    player1_data = manager.matchmaking_queue.pop(0)
                    player2_data = manager.matchmaking_queue.pop(0)
                    
                    player1 = player1_data["player_id"]
                    player2 = player2_data["player_id"]
                    deck1 = player1_data["deck"]
                    deck2 = player2_data["deck"]
                    
                    game_id = f"game_{player1}_{player2}"
                    
                    # Create new game using GameManager
                    game = game_manager.create_game(
                        game_id=game_id,
                        white_player_id=player1,
                        black_player_id=player2,
                        white_deck=deck1,
                        black_deck=deck2
                    )
                    
                    # Notify both players with initial game state
                    await manager.send_personal_message({
                        "type": "game_started",
                        "game_state": game.get_game_state(player1)
                    }, player1)
                    
                    await manager.send_personal_message({
                        "type": "game_started",
                        "game_state": game.get_game_state(player2)
                    }, player2)
            
            elif message_type == "move":
                # Handle piece movement
                game_id = message.get("game_id")
                from_square = message.get("from")
                to_square = message.get("to")
                
                game = game_manager.get_game(game_id)
                if not game:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Game not found"
                    }, client_id)
                    continue
                
                # Attempt to make the move
                success, msg = game.make_move(client_id, from_square, to_square)
                
                if success:
                    # Broadcast updated game state to both players
                    await manager.send_personal_message({
                        "type": "game_update",
                        "game_state": game.get_game_state(game.white_player_id)
                    }, game.white_player_id)
                    
                    await manager.send_personal_message({
                        "type": "game_update",
                        "game_state": game.get_game_state(game.black_player_id)
                    }, game.black_player_id)
                    
                    # Check if game is over
                    if game.status != GameStatus.IN_PROGRESS:
                        await manager.broadcast_to_game({
                            "type": "game_over",
                            "reason": game.status.value,
                            "winner": game.winner,
                            "message": game.win_reason
                        }, game)
                else:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": msg
                    }, client_id)
            
            elif message_type == "play_card":
                # Handle card play
                game_id = message.get("game_id")
                card_name = message.get("card")
                target_data = message.get("target", {})
                
                game = game_manager.get_game(game_id)
                if not game:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Game not found"
                    }, client_id)
                    continue
                
                # Attempt to play the card
                success, msg = game.play_card(client_id, card_name, target_data)
                
                if success:
                    # Broadcast updated game state to both players
                    await manager.send_personal_message({
                        "type": "game_update",
                        "game_state": game.get_game_state(game.white_player_id)
                    }, game.white_player_id)
                    
                    await manager.send_personal_message({
                        "type": "game_update",
                        "game_state": game.get_game_state(game.black_player_id)
                    }, game.black_player_id)
                    
                    # Check if game is over
                    if game.status != GameStatus.IN_PROGRESS:
                        await manager.broadcast_to_game({
                            "type": "game_over",
                            "reason": game.status.value,
                            "winner": game.winner,
                            "message": game.win_reason
                        }, game)
                else:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": msg
                    }, client_id)
            
            elif message_type == "ping":
                # Keep connection alive
                await manager.send_personal_message({"type": "pong"}, client_id)
            
            else:
                print(f"Unknown message type: {message_type}")
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        # TODO: Handle disconnection during active game
    except Exception as e:
        print(f"Error: {e}")
        manager.disconnect(client_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)