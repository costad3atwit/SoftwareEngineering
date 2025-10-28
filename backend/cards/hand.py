from typing import List
from cards import Card

class Hand:
    def __init__(self):
        self.cards: List[Card] = []

    def add(self, card: Card) -> None:
        self.cards.append(card)

    def remove(self, card: Card) -> None:
        if card in self.cards:
            self.cards.remove(card)

    def list(self) -> List[Card]:
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
        print(f"{'✅' if passed else '❌'} {name}")

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
        print(f"❌ Unexpected error: {e}")
