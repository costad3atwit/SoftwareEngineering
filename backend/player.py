from __future__ import annotations
from typing import List, Optional
from datetime import datetime

from backend.enums import Color
from backend.cards.card import Card
from backend.chess.piece import Piece
from backend.cards.deck import Deck
from backend.cards.hand import Hand


class Player:
    def __init__(self, id: str, name: str, color: Color, deck: Deck):
        self.id = id
        self.name = name
        self.color = color
        
        # Card management
        self.deck = deck
        self.discard_pile = Deck()  # Empty deck for discards
        self.hand = Hand()
        
        # Captured pieces
        self.captured: List[Piece] = []
        
        # Deal initial hand (4 cards per your requirements)
        for _ in range(4):
            if self.deck.size() > 0:
                self.draw_card()

    def draw_card(self) -> Optional[Card]:
        """
        Draws the top card from the player's deck into their hand.
        Returns the card drawn, or None if deck is empty.
        """
        if self.deck.size() == 0:
            return None
        
        card = self.deck.draw()
        self.hand.add(card)
        return card

    def play_card(self, card_id: str) -> Optional[Card]:
        """
        Removes a card from hand and adds it to discard pile.
        Returns the card, or None if not found.
        """
        card = self.hand.remove(card_id)
        if card:
            self.discard_pile.add(card)  # Assumes Deck has add() method
        return card

    def has_card(self, card_id: str) -> bool:
        """
        Check if player has a specific card in their hand.
        """
        return self.hand.has_card(card_id)

    def capture_piece(self, piece: Piece) -> None:
        """
        Adds a captured piece to the player's captured list.
        """
        self.captured.append(piece)

    def hand_size(self) -> int:
        """Returns the number of cards in hand"""
        return self.hand.size()

    def deck_size(self) -> int:
        """Returns the number of cards remaining in deck"""
        return self.deck.size()

    def get_hand(self) -> List[str]:
        """Returns list of card IDs in hand"""
        return [card.id for card in self.hand.cards]

    def __repr__(self) -> str:
        """
        Returns information about who the player is.
        """
        return f"<Player {self.name} ({self.color.name})>"

    def to_dict(self) -> dict:
        """
        Returns a dictionary snapshot of the player's current state.
        """
        # Get the top card of discard pile if it exists
        discard_top = None
        if self.discard_pile.size() > 0:
            top_card = self.discard_pile.top()
            if top_card:
                discard_top = top_card.to_dict()
        
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color.name,
            "hand": [card.id for card in self.hand.cards],
            "deck_size": self.deck.size(),
            "discard_size": self.discard_pile.size(),
            "discard_pile_top": discard_top,  # ← ADD THIS LINE
            "captured": [piece.id for piece in self.captured]
        }