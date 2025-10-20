from card import Card

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
        def __init__(self):
        self.cards: List[Card] = []

    def shuffle(self) -> None:
        shuffle(self.cards)

    def size(self) -> int:
        return len(self.cards)
