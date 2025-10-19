from abc import ABC, abstractmethod #abc's are python's version of (AB)stract (C)lasses 
from enums import CardType, TargetType


class Card(ABC):
    id = ""
    name = ""
    description = ""
    big_img = ""
    small_img = ""

    def __init__(self, id: str, name: str, description: str, big_img: str, small_img: str):
        self.id = id
        self.name = name
        self.description = description
        self.big_img = big_img
        self.small_img = small_img  

    @property
    @abstractmethod
    def card_type(self) -> CardType:
        """Must be implemented in subclasses.
        e.g. return CardType.CURSE"""
        pass

    def get_desc(self):
        return self.description
    
    def get_big_img(self):
        return self.big_img
    
    def get_small_img(self):
        return self.small_img
    
    def get_id(self):
        return self.id
    
    def get_name(self):
        return self.name
    
    

