from typing import List, Optional
from backend.cards.card import Card
from backend.enums import CardType

class Hand:
    def __init__(self):
        self.cards: List[Card] = []

    def add(self, card: Card) -> None:
        """Add a card to the hand"""
        if not isinstance(card, Card):
            raise TypeError(f"Object {card} is not a Card or subclass of Card.")
        self.cards.append(card)

    def remove(self, card):
        # Handle both string card_id and Card object
        if isinstance(card, str):
            card_id = card
        else:
            card_id = card.id
        
        for i, c in enumerate(self.cards):
            if c.id == card_id:
                return self.cards.pop(i)
        return None 

    def has_card(self, card):
        # Handle both string card_id and Card object
        if isinstance(card, str):
            card_id = card
        else:
            card_id = card.id
        
        return any(c.id == card_id for c in self.cards)

    def size(self) -> int:
        """Return the number of cards in hand"""
        return len(self.cards)

    def list(self) -> List[Card]:
        """Return all cards in hand"""
        return self.cards

    def __len__(self):
        return len(self.cards)

# -------------------------------------------------------------------------
# INLINE TESTS
# -------------------------------------------------------------------------
if __name__ == "__main__":
    from abc import ABC

    class DummyCard(Card):
        """Simple concrete subclass for testing."""
        @property
        def card_type(self) -> CardType:
            return CardType.HIDDEN

    def print_test(name, passed=True):
        print(f"{'Pass' if passed else 'Fail'} {name}")

    try:
        # --- Setup ---
        hand = Hand()
        c1 = DummyCard("C1", "Hidden Mine", "A hidden explosive card", "big1.png", "small1.png")
        c2 = DummyCard("C2", "Shroud", "Conceals positions", "big2.png", "small2.png")

        # --- Test 1: add() adds a card ---
        hand.add(c1)
        assert len(hand) == 1 and c1 in hand.list()
        print_test("add() adds a card")

        # --- Test 2: add() rejects non-Card types ---
        try:
            hand.add("NotACard")
            print_test("add() type check failed", False)
        except TypeError:
            print_test("add() rejects non-Card")

        # --- Test 3: remove() removes a specific card ---
        hand.add(c2)
        hand.remove(c1)
        assert c1 not in hand.list() and c2 in hand.list()
        print_test("remove() removes specified card")

        # --- Test 4: remove() silently ignores missing cards ---
        try:
            ghost_card = DummyCard("G1", "Ghost", "Not in hand", "x.png", "y.png")
            hand.remove(ghost_card)  # should not raise error
            print_test("remove() ignores missing cards")
        except Exception:
            print_test("remove() failed on missing card", False)

        # --- Test 5: list() returns correct card objects ---
        listed = hand.list()
        assert all(isinstance(c, Card) for c in listed)
        print_test("list() returns valid Card objects")

        # --- Test 6: __len__ matches number of cards ---
        assert len(hand) == len(hand.list())
        print_test("__len__ returns correct count")

    except Exception as e:
        print(f"Unexpected error: {e}")
