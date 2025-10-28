from card import Card
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
    # Helper for display
    def print_test(name, result=True):
        print(f"{'✅' if result else '❌'} {name}")

    # Create deck
    deck = Deck()

    # --- Test 1: add_card success ---
    try:
        c1 = Card("Fireball")
        deck.add_card(c1)
        assert deck.size() == 1
        print_test("add_card success")
    except Exception as e:
        print_test(f"add_card failed: {e}", False)

    # --- Test 2: add_card rejects non-card ---
    try:
        deck.add_card("NotACard")
        print_test("add_card non-card type check failed", False)
    except TypeError:
        print_test("add_card rejects non-card")

    # --- Test 3: deck limit 16 cards ---
    try:
        for i in range(15):
            deck.add_card(Card(f"C{i}"))
        assert deck.size() == 16
        try:
            deck.add_card(Card("Extra"))
            print_test("add_card limit check failed", False)
        except ValueError:
            print_test("add_card enforces 16-card limit")
    except Exception as e:
        print_test(f"add_card limit setup failed: {e}", False)

    # --- Test 4: draw removes last card ---
    try:
        top_before = deck.top()
        drawn = deck.draw()
        assert drawn == top_before
        print_test("draw removes top card")
    except Exception as e:
        print_test(f"draw test failed: {e}", False)

    # --- Test 5: draw from empty deck ---
    try:
        empty_deck = Deck()
        empty_deck.draw()
        print_test("draw from empty deck failed", False)
    except ValueError:
        print_test("draw from empty deck raises ValueError")

    # --- Test 6: top() returns last card ---
    try:
        d = Deck()
        c = Card("Ice Spear")
        d.add_card(c)
        assert d.top() == c
        print_test("top() returns last card")
    except Exception as e:
        print_test(f"top() failed: {e}", False)

    # --- Test 7: top() on empty returns None ---
    try:
        d = Deck()
        assert d.top() is None
        print_test("top() returns None when empty")
    except Exception as e:
        print_test(f"top() on empty failed: {e}", False)

    # --- Test 8: shuffle changes order ---
    try:
        d = Deck()
        for i in range(5):
            d.add_card(Card(f"C{i}"))
        before = [c.name for c in d.cards]
        d.shuffle()
        after = [c.name for c in d.cards]
        assert sorted(before) == sorted(after)
        if before != after:
            print_test("shuffle changes order")
        else:
            print_test("shuffle no change (possible but rare)", False)
    except Exception as e:
        print_test(f"shuffle test failed: {e}", False)

    # --- Test 9: size() matches card count ---
    try:
        d = Deck()
        for i in range(3):
            d.add_card(Card(f"Card{i}"))
        assert d.size() == 3
        print_test("size() returns correct card count")
    except Exception as e:
        print_test(f"size() test failed: {e}", False)
