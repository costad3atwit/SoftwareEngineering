from enum import Enum


class EffectType(Enum):
    """Types of effects that can be tracked"""
    PIECE_EMPOWERMENT = "piece_empowerment"
    ALL_SEEING = "all_seeing"
    PIECE_MARK = "piece_mark"
    MINE = "mine"
    PAWN_BOMB = "pawn_bomb"
    GLUE_TRAP = "glue_trap"
    FORBIDDEN_LANDS = "forbidden_lands"
    CARD_ACTIVE = "card_active"
    PIECE_IMMOBILIZED = "piece_immobilized"
    # Add more as needed

class PieceType(Enum):
    KING = "K"
    QUEEN = "Q"
    ROOK = "R"
    BISHOP = "B"
    KNIGHT = "N"
    PAWN = "P"
    PEON = "E" 
    SCOUT = "S"
    HEADHUNTER = "H"
    WITCH = "T" 
    WARLOCK = "W" 
    CLERIC = "C"
    DARKLORD = "D"
    
class TargetType(Enum):
    BOARD = "BOARD"
    PIECE = "PIECE"
    TIMER = "TIMER"
    TURN = "TURN"

class CardType(Enum):
    UNSTABLE = "UNSTABLE"
    CURSE = "CURSE"
    HIDDEN = "HIDDEN"
    TRANSFORM = "TRANSFORM"
    FORCED = "FORCED"

class Color(Enum):
    WHITE = "W"
    BLACK = "B"

class GameStatus(Enum): 
    WAITING = "WAITING"
    IN_PROGRESS = "IN PROGRESS"
    CHECK = "CHECK"
    CHECKMATE = "CHECKMATE"
    STALEMATE = "STALEMATE"
    RESIGNED = "RESIGNED"
    DRAW = "DRAW"
    TIMEOUT = "TIMEOUT"
    FORFEIT = "FORFEIT"
