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
