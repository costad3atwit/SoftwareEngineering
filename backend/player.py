from __future__ import annotations
from typing import List
from datetime import datetime

from enums import Color
from card import Card
from piece import Piece
from deck import Deck
from hand import Hand

class Player:
    def __init__(self, id: str, name: str, color: Color, time_ms_remaining: int = 0):
        self.id = id
        self.name = name
        self.color = color
        self.time_ms_remaining = time_ms_remaining
        self.hand = Hand()
        self.captured: List[Piece] = []

    def draw_from_deck(self, deck: Deck) -> None:
        """
        Draws the top card from the deck into the player's hand.
        
        """
        if deck.size() == 0:
            raise ValueError("Cannot draw from an empty deck.")
        card = deck.draw()
        self.hand.add(card)

    def capture_piece(self, piece: Piece) -> None:
        """
        Adds a captured piece to the player's captured list.
        """
        self.captured.append(piece)

    def __repr__(self) -> str:
        """
        returns information about who the player is.
        """
        return f"<Player {self.name} ({self.color.name})>"

    def snapshot(self) -> dict:
        """
        Returns a dictionary snapshot of the player's current state.
        """
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color.name,
            "time_ms_remaining": self.time_ms_remaining,
            "hand": [card.id for card in self.hand.cards],
            "captured": [piece.id for piece in self.captured]
        }
