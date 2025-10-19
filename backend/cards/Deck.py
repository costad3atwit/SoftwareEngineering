from typing import List, Optional
from random import shuffle


class Deck:
    def __init__(self):
        self.cards: List[Card] = []

    def shuffle(self) -> None:
        shuffle(self.cards)

    def draw(self) -> Optional[Card]:
        if not self.cards:
            return None
        return self.cards.pop()

    def size(self) -> int:
        return len(self.cards)

    def add_card(self, card: Card) -> None:
        self.cards.insert(0, card)

