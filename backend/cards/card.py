from abc import ABC #abc's are python's version of (AB)stract (C)lasses 

class Card(ABC):
    description = ""
    big_img = ""
    small_img = ""

    def __init__(self):
        pass

    def get_desc(self):
        return self.description
    
    def get_big_img(self):
        return self.big_img
    
    def get_small_img(self):
        return self.small_img
    
    


