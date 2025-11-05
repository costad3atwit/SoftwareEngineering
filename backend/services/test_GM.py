"""
Test the GameManager functionality
Run this to verify everything works before testing with WebSockets
"""

from backend.services.game_manager import GameManager


def test_sample_game():
    """Test creating a sample game"""
    print("="*60)
    print("TEST: Creating Sample Game")
    print("="*60)
    
    gm = GameManager()
    print(f" GameManager created: {gm}")
    
    # Create a sample game
    game = gm.create_sample_game("alice_123", "bob_456")
    print(f"\n Sample game created: {game.game_id}")
    print(f"  Status: {game.status.value}")
    print(f"  Turn: {game.turn.value}")
    
    # Get game state for Alice
    print("\n" + "-"*60)
    print("Alice's View:")
    print("-"*60)
    alice_state = game.to_dict("alice_123")
    print(f"Color: {alice_state['your_color']}")
    print(f"Turn: {'YES' if alice_state['your_turn'] else 'NO'}")
    print(f"Hand: {alice_state['your_hand']}")
    print(f"Deck: {alice_state['your_deck_size']} cards")
    
    # Get game state for Bob
    print("\n" + "-"*60)
    print("Bob's View:")
    print("-"*60)
    bob_state = game.to_dict("bob_456")
    print(f"Color: {bob_state['your_color']}")
    print(f"Turn: {'YES' if bob_state['your_turn'] else 'NO'}")
    print(f"Hand: {bob_state['your_hand']}")
    print(f"Deck: {bob_state['your_deck_size']} cards")
    
    return gm, game


def test_matchmaking():
    """Test the matchmaking queue"""
    print("\n" + "="*60)
    print("TEST: Matchmaking")
    print("="*60)
    
    gm = GameManager()
    
    sample_deck = [
        "mine", "eye_for_an_eye", "summon_peon", "pawn_scout",
        "knight_headhunter", "bishop_warlock",
        "mine", "eye_for_an_eye", "summon_peon", "pawn_scout",
        "knight_headhunter", "bishop_warlock",
        "mine", "eye_for_an_eye", "summon_peon", "pawn_scout"
    ]
    
    # Add first player to queue
    success, msg = gm.add_to_queue("player1", "Alice", sample_deck)
    print(f"\nPlayer 1: {msg}")
    print(f"Queue size: {len(gm.matchmaking_queue)}")
    
    # Add second player to queue
    success, msg = gm.add_to_queue("player2", "Bob", sample_deck)
    print(f"\nPlayer 2: {msg}")
    print(f"Queue size: {len(gm.matchmaking_queue)}")
    
    # Try to match
    print("\nAttempting to match players...")
    game = gm.try_match_players()
    
    if game:
        print(f" Match found! Game created: {game.game_id}")
        print(f"  White: {game.players[game.turn].name}")
        print(f"  Queue size after match: {len(gm.matchmaking_queue)}")
    else:
        print(" No match found")
    
    return gm


def test_game_retrieval():
    """Test retrieving games"""
    print("\n" + "="*60)
    print("TEST: Game Retrieval")
    print("="*60)
    
    gm = GameManager()
    game1 = gm.create_sample_game("alice", "bob")
    game2 = gm.create_sample_game("charlie", "david")
    
    print(f"\n Created 2 games")
    print(f"  Game 1: {game1.game_id}")
    print(f"  Game 2: {game2.game_id}")
    
    # Test get_game
    print("\nTesting get_game()...")
    retrieved = gm.get_game(game1.game_id)
    print(f"  Retrieved: {retrieved.game_id if retrieved else 'None'}")
    
    # Test get_player_game
    print("\nTesting get_player_game()...")
    alice_game = gm.get_player_game("alice")
    print(f"  Alice's game: {alice_game.game_id if alice_game else 'None'}")
    
    # Test get_all_active_games
    print("\nTesting get_all_active_games()...")
    active = gm.get_all_active_games()
    print(f"  Active games: {len(active)}")
    
    # Test stats
    print("\nGameManager Stats:")
    stats = gm.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    return gm


def test_card_play():
    """Test playing a card"""
    print("\n" + "="*60)
    print("TEST: Card Play")
    print("="*60)
    
    gm = GameManager()
    game = gm.create_sample_game("alice", "bob")
    
    # Get Alice's first card
    alice = game.get_player_by_id("alice")
    print(f"\nAlice's hand: {alice.get_hand()}")
    
    if alice.hand_size() > 0:
        card_to_play = alice.get_hand()[0]
        print(f"\nAttempting to play: {card_to_play}")
        
        # Try to play the card through GameManager
        success, msg, updated_game = gm.play_card(game.game_id, "alice", card_to_play, {})
        
        print(f"Result: {msg}")
        
        if success:
            print(f" Card played successfully")
            print(f"  New hand size: {alice.hand_size()}")
            print(f"  Current turn: {updated_game.turn.value}")
        else:
            print(f" Card play failed (expected - effects not implemented)")
    
    return gm


def test_game_lifecycle():
    """Test complete game lifecycle"""
    print("\n" + "="*60)
    print("TEST: Game Lifecycle")
    print("="*60)
    
    gm = GameManager()
    
    # Create game
    game = gm.create_sample_game("alice", "bob")
    print(f"\n Game created: {game.game_id}")
    print(f"  Status: {game.status.value}")
    
    # Check stats
    stats = gm.get_stats()
    print(f"\nStats after creation:")
    print(f"  Total games: {stats['total_games']}")
    print(f"  Active games: {stats['active_games']}")
    
    # End game
    print(f"\nEnding game...")
    gm.end_game(game.game_id)
    print(f"  New status: {game.status.value}")
    
    # Cleanup
    print(f"\nCleaning up finished games...")
    removed = gm.cleanup_finished_games()
    print(f"  Removed {removed} game(s)")
    
    # Check stats again
    stats = gm.get_stats()
    print(f"\nStats after cleanup:")
    print(f"  Total games: {stats['total_games']}")
    print(f"  Active games: {stats['active_games']}")
    
    return gm


def main():
    """Run all tests"""
    print("\n ARCANE CHESS - GAMEMANAGER TEST SUITE")
    print("="*60)
    
    try:
        # Test 1: Sample game creation
        gm1, game1 = test_sample_game()
        
        # Test 2: Matchmaking
        gm2 = test_matchmaking()
        
        # Test 3: Game retrieval
        gm3 = test_game_retrieval()
        
        # Test 4: Card play
        gm4 = test_card_play()
        
        # Test 5: Game lifecycle
        gm5 = test_game_lifecycle()
        
        print("\n" + "="*60)
        print(" ALL TESTS COMPLETED")
        print("="*60)
        
        print("\nGameManager is ready to use! Key features:")
        print("   Create sample games for testing")
        print("   Matchmaking queue management")
        print("   Game state retrieval")
        print("   Card play (once effects are implemented)")
        print("   Game lifecycle management")

        
    except Exception as e:
        print(f"\n TEST FAILED:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()