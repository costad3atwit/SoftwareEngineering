"""
WebSocket test client for Arcane Chess
Tests all GameManager functionality over actual WebSocket connections
"""

import asyncio
import websockets
import json
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime

# ============================================================================
# LOGGING SETUP
# ============================================================================

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

log_filename = log_dir / f"test_websocket_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ============================================================================
# TEST CLIENT
# ============================================================================

class TestClient:
    def __init__(self, client_id: str, name: str):
        self.client_id = client_id
        self.name = name
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.game_id: Optional[str] = None
        self.messages = []
    
    async def connect(self, url="ws://localhost:8000/ws"):
        """Connect to the WebSocket server"""
        full_url = f"{url}/{self.client_id}"
        self.ws = await websockets.connect(full_url)
        logger.info(f"{self.name} connected as {self.client_id}")
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.ws:
            await self.ws.close()
            logger.info(f"{self.name} disconnected")
    
    async def send(self, message: dict):
        """Send a message to the server"""
        if not self.ws:
            raise Exception("Not connected")
        await self.ws.send(json.dumps(message))
        logger.info(f"{self.name} sent: {message['type']}")
    
    async def receive(self, timeout=5):
        """Receive a message from the server"""
        if not self.ws:
            raise Exception("Not connected")
        try:
            response = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            data = json.loads(response)
            self.messages.append(data)
            logger.info(f"{self.name} received: {data['type']}")
            if data.get('type') == 'error':
                logger.warning(f"  Error message: {data.get('message')}")
            return data
        except asyncio.TimeoutError:
            logger.warning(f"{self.name} receive timeout after {timeout}s")
            return None
    
    async def join_queue(self, deck):
        """Join the matchmaking queue"""
        logger.info(f"{self.name} joining queue with {len(deck)} cards")
        await self.send({
            "type": "join_queue",
            "name": self.name,
            "deck": deck
        })
    
    async def play_card(self, card_id: str, target_data: dict = None):
        """Play a card"""
        if not self.game_id:
            raise Exception("Not in a game")
        logger.info(f"{self.name} playing card: {card_id}")
        await self.send({
            "type": "play_card",
            "game_id": self.game_id,
            "card_id": card_id,
            "target": target_data or {}
        })
    
    async def make_move(self, from_square: str, to_square: str):
        """Make a move"""
        if not self.game_id:
            raise Exception("Not in a game")
        logger.info(f"{self.name} moving: {from_square} -> {to_square}")
        await self.send({
            "type": "make_move",
            "game_id": self.game_id,
            "from": from_square,
            "to": to_square
        })


# ============================================================================
# TEST CASES
# ============================================================================

async def test_matchmaking():
    """Test 1: Matchmaking - Two players join queue and get matched"""
    logger.info("="*60)
    logger.info("TEST 1: Matchmaking")
    logger.info("="*60)
    
    # Sample deck (16 cards)
    sample_deck = [
        "mine", "eye_for_an_eye", "summon_peon", "pawn_scout",
        "knight_headhunter", "bishop_warlock",
        "mine", "eye_for_an_eye", "summon_peon", "pawn_scout",
        "knight_headhunter", "bishop_warlock",
        "mine", "eye_for_an_eye", "summon_peon", "pawn_scout"
    ]
    
    # Create two clients
    alice = TestClient("alice_test_1", "Alice")
    bob = TestClient("bob_test_1", "Bob")
    
    try:
        # Connect both clients
        await alice.connect()
        await bob.connect()
        
        # Alice joins queue
        await alice.join_queue(sample_deck)
        response = await alice.receive()
        assert response["type"] == "queue_joined", "Alice should join queue"
        logger.info(f"✓ Alice joined queue: {response['message']}")
        
        # Bob joins queue
        await bob.join_queue(sample_deck)
        response = await bob.receive()
        assert response["type"] == "queue_joined", "Bob should join queue"
        logger.info(f"✓ Bob joined queue: {response['message']}")
        
        # Both should receive game_started
        alice_game = await alice.receive()
        bob_game = await bob.receive()
        
        assert alice_game["type"] == "game_started", "Alice should get game start"
        assert bob_game["type"] == "game_started", "Bob should get game start"
        
        alice.game_id = alice_game["game_id"]
        bob.game_id = bob_game["game_id"]
        
        logger.info(f"✓ Game created: {alice.game_id}")
        logger.info(f"  Alice color: {alice_game['game_state']['your_color']}")
        logger.info(f"  Bob color: {bob_game['game_state']['your_color']}")
        logger.info(f"  Alice turn: {alice_game['game_state']['your_turn']}")
        logger.info(f"  Bob turn: {bob_game['game_state']['your_turn']}")
        logger.info(f"  Alice hand: {alice_game['game_state']['your_hand']}")
        
        logger.info("TEST 1 PASSED")
        
    except AssertionError as e:
        logger.error(f"TEST 1 FAILED: {e}")
        raise
    finally:
        await alice.disconnect()
        await bob.disconnect()


async def test_card_play():
    """Test 2: Card Play - Player plays a card"""
    logger.info("="*60)
    logger.info("TEST 2: Card Play")
    logger.info("="*60)
    
    sample_deck = [
        "mine", "eye_for_an_eye", "summon_peon", "pawn_scout",
        "knight_headhunter", "bishop_warlock",
        "mine", "eye_for_an_eye", "summon_peon", "pawn_scout",
        "knight_headhunter", "bishop_warlock",
        "mine", "eye_for_an_eye", "summon_peon", "pawn_scout"
    ]
    
    alice = TestClient("alice_test_2", "Alice")
    bob = TestClient("bob_test_2", "Bob")
    
    try:
        # Setup: Create game
        await alice.connect()
        await bob.connect()
        await alice.join_queue(sample_deck)
        await alice.receive()  # queue_joined
        await bob.join_queue(sample_deck)
        await bob.receive()  # queue_joined
        
        alice_game = await alice.receive()  # game_started
        bob_game = await bob.receive()  # game_started
        alice.game_id = alice_game["game_id"]
        bob.game_id = bob_game["game_id"]
        
        # Get Alice's hand
        hand = alice_game["game_state"]["your_hand"]
        logger.info(f"Alice's hand: {hand}")
        
        # Alice plays first card
        card_to_play = hand[0]
        await alice.play_card(card_to_play)
        
        # Alice should get update
        alice_response = await alice.receive()
        logger.info(f"Alice received: {alice_response.get('type')}")
        
        # Bob should get update
        bob_response = await bob.receive()
        logger.info(f"Bob received: {bob_response.get('type')}")
        
        if alice_response.get("type") == "error":
            logger.warning(f"Card effect not implemented yet (expected)")
        elif alice_response.get("type") == "game_update":
            logger.info("✓ Card played successfully")
        
        logger.info("TEST 2 COMPLETED")
        
    except Exception as e:
        logger.error(f"TEST 2 FAILED: {e}")
        raise
    finally:
        await alice.disconnect()
        await bob.disconnect()


async def test_game_state_retrieval():
    """Test 3: Game State Retrieval"""
    logger.info("="*60)
    logger.info("TEST 3: Game State Retrieval")
    logger.info("="*60)
    
    sample_deck = [
        "mine", "eye_for_an_eye", "summon_peon", "pawn_scout",
        "knight_headhunter", "bishop_warlock",
        "mine", "eye_for_an_eye", "summon_peon", "pawn_scout",
        "knight_headhunter", "bishop_warlock",
        "mine", "eye_for_an_eye", "summon_peon", "pawn_scout"
    ]
    
    alice = TestClient("alice_test_3", "Alice")
    
    try:
        await alice.connect()
        await alice.join_queue(sample_deck)
        await alice.receive()  # queue_joined
        
        # Request game state before match
        await alice.send({
            "type": "get_game_state",
            "game_id": "nonexistent"
        })
        response = await alice.receive()
        assert response["type"] == "error", "Should get error for nonexistent game"
        logger.info("✓ Correctly handled nonexistent game request")
        
        logger.info("TEST 3 PASSED")
        
    except AssertionError as e:
        logger.error(f"TEST 3 FAILED: {e}")
        raise
    finally:
        await alice.disconnect()


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def main():
    """Run all tests"""
    logger.info("="*60)
    logger.info("🎮 ARCANE CHESS - WEBSOCKET TEST SUITE")
    logger.info("="*60)
    logger.info(f"Log file: {log_filename}")
    logger.info("Make sure the server is running: python main.py")
    logger.info("="*60)
    
    await asyncio.sleep(1)  # Give server time to start if just launched
    
    tests_passed = 0
    tests_failed = 0
    
    try:
        await test_matchmaking()
        tests_passed += 1
    except Exception as e:
        tests_failed += 1
        logger.error(f"Test 1 failed: {e}")
    
    try:
        await test_card_play()
        tests_passed += 1
    except Exception as e:
        tests_failed += 1
        logger.error(f"Test 2 failed: {e}")
    
    try:
        await test_game_state_retrieval()
        tests_passed += 1
    except Exception as e:
        tests_failed += 1
        logger.error(f"Test 3 failed: {e}")
    
    logger.info("="*60)
    logger.info(f"Tests passed: {tests_passed}")
    logger.info(f"Tests failed: {tests_failed}")
    logger.info("="*60)
    logger.info(f"Full log saved to: {log_filename}")


if __name__ == "__main__":
    asyncio.run(main())