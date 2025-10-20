from typing import List, Optional
from cards import Card

class DiscardPile:
    def __init__(self):
        self.cards: List[Card] = []

    def add_card(self, card: Card) -> None:
        self.cards.append(card)

    def top(self) -> Optional[Card]:
        return self.cards[-1] if self.cards else None

    def size(self) -> int:
        return len(self.cards)