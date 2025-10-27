from abc import ABC, abstractmethod  # Abstract Base Class tools
from enums import CardType, TargetType


class Card(ABC):
    """
    Abstract Base Class representing a general card in the game.
    Each card has an ID, name, description, and two image versions (big and small).
    Concrete subclasses (like SpellCard, CurseCard, etc.) must define their own card_type.
    """

    def __init__(self, id: str, name: str, description: str, big_img: str, small_img: str):
        self.id = id
        self.name = name
        self.description = description
        self.big_img = big_img
        self.small_img = small_img

    # --- Abstract property to be implemented by subclasses ---
    @property
    @abstractmethod
    def card_type(self) -> CardType:
        """
        Returns the specific type of card.
        Must be implemented by subclasses.
        Example: return CardType.CURSE
        """
        pass

    # --- Getters ---
    def get_desc(self) -> str:
        """Return the card's description."""
        return self.description

    def get_big_img(self) -> str:
        """Return the large image URL or file path of the card."""
        return self.big_img

    def get_small_img(self) -> str:
        """Return the small image URL or file path of the card."""
        return self.small_img

    def get_id(self) -> str:
        """Return the unique card ID."""
        return self.id

    def get_name(self) -> str:
        """Return the card name."""
        return self.name

    # --- Dictionary for frontend/UI ---
    def to_dict(self, include_target: bool = False) -> dict:
        """
        Convert the card into a frontend-friendly dictionary.
        Optionally include target type if relevant (for playable cards).
        """
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cardType": self.card_type.name if self.card_type else None,
            "images": {
                "big": self.big_img,
                "small": self.small_img,
            }
        }

        # If the subclass defines a target_type property (e.g., affects ally/enemy)
        if include_target and hasattr(self, "target_type"):
            data["targetType"] = self.target_type.name if isinstance(self.target_type, TargetType) else str(self.target_type)

        return data


