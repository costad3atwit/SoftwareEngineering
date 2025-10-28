from typing import List, Optional
from card import Card

class Hand:
    def __init__(self):
        self.cards: List[Card] = []

    def add(self, card: Card) -> None:
        """Add a card to the hand"""
        self.cards.append(card)

    def remove(self, card_id: str) -> Optional[Card]:
        """
        Remove a card by ID and return it.
        Returns None if card not found.
        """
        for card in self.cards:
            if card.id == card_id:
                self.cards.remove(card)
                return card
        return None

    def has_card(self, card_id: str) -> bool:
        """Check if a card is in the hand"""
        return any(card.id == card_id for card in self.cards)

    def size(self) -> int:
        """Return the number of cards in hand"""
        return len(self.cards)

    def list(self) -> List[Card]:
        """Return all cards in hand"""
        return self.cards

    def __len__(self):
        return len(self.cards)