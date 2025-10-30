from backend.cards.card import Card
from typing import Optional
from abc import ABC
from backend.enums import Card, CardType
import random

class Deck:
    def __init__(self):
        self.cards: list[Card] = []

    def add_card(self, card: Card) -> None:
        if not isinstance(card, Card):
            raise TypeError(f"Object {card} is not a Card or subclass of Card.")
        if len(self.cards) >= 16:
            raise ValueError("Deck cannot hold more than 16 cards.")
        self.cards.append(card)

    def draw(self) -> Card:
        if not self.cards:
            raise ValueError("Deck is empty.")
        return self.cards.pop()

    def shuffle(self) -> None:
        random.shuffle(self.cards)

    def top(self) -> Optional[Card]:
        return self.cards[-1] if self.cards else None

    def size(self) -> int:
        return len(self.cards)

# -------------------------------------------------------------------------
# INLINE TESTS
# -------------------------------------------------------------------------
if __name__ == "__main__":
    class DummyCard(Card):
        """Simple concrete subclass for testing."""
        @property
        def card_type(self) -> CardType:
            return CardType.HIDDEN

    def print_test(name, passed=True):
        print(f"{'Pass' if passed else 'Fail'} {name}")

    try:
        # Create a test deck
        deck = Deck()

        # --- Test 1: Add a valid card ---
        c1 = DummyCard("C1", "Hidden Mine", "Places a hidden mine", "mine_big.png", "mine_small.png")
        deck.add_card(c1)
        assert deck.size() == 1
        print_test("Add valid card")

        # --- Test 2: Reject non-card objects ---
        try:
            deck.add_card("NotACard")
            print_test("Reject non-card failed", False)
        except TypeError:
            print_test("Reject non-card objects")

        # --- Test 3: Enforce 16-card limit ---
        for i in range(15):
            deck.add_card(DummyCard(f"C{i}", "Card", "Test", "img.png", "img_s.png"))
        assert deck.size() == 16
        try:
            deck.add_card(DummyCard("C17", "Over", "Limit", "a.png", "b.png"))
            print_test("Enforce 16-card limit failed", False)
        except ValueError:
            print_test("Enforce 16-card limit")

        # --- Test 4: Draw returns last card ---
        last = deck.top()
        drawn = deck.draw()
        assert drawn == last
        print_test("Draw returns last card")

        # --- Test 5: Drawing from empty deck raises ---
        empty_deck = Deck()
        try:
            empty_deck.draw()
            print_test("Draw from empty failed", False)
        except ValueError:
            print_test("Draw from empty deck raises")

        # --- Test 6: top() works correctly ---
        d = Deck()
        c = DummyCard("X1", "Scout", "Test", "a.png", "b.png")
        d.add_card(c)
        assert d.top() == c
        print_test("Top returns last card")

        # --- Test 7: top() returns None on empty deck ---
        empty = Deck()
        assert empty.top() is None
        print_test("Top returns None when empty")

        # --- Test 8: Shuffle modifies order ---
        s = Deck()
        for i in range(5):
            s.add_card(DummyCard(f"Card{i}", "C", "D", "big.png", "small.png"))
        before = [c.id for c in s.cards]
        s.shuffle()
        after = [c.id for c in s.cards]
        assert sorted(before) == sorted(after)
        if before != after:
            print_test("Shuffle changes order")
        else:
            print_test("Shuffle order unchanged (rare)", False)

        # --- Test 9: Size returns correct count ---
        deck2 = Deck()
        for i in range(3):
            deck2.add_card(DummyCard(f"D{i}", "Test", "Desc", "a.png", "b.png"))
        assert deck2.size() == 3
        print_test("Size returns correct count")

    except Exception as e:
        print(f"Unexpected test error: {e}")
