# from typing import List, Dict, Optional
# from dataclasses import dataclass, field
# from enum import Enum

# @dataclass
# class Detection:
#     name: str
#     x: float
#     y: float
#     r: float
#     conf: float


from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time

@dataclass
class Detection:
    name: str
    x: float
    y: float
    r: float
    conf: float

class GameState(Enum):
    WAITING = "waiting"          # Chờ cú đánh
    SHOOTING = "shooting"         # Đang đánh
    ANALYZING = "analyzing"       # Phân tích sau cú đánh
    GAME_OVER = "game_over"      # Kết thúc

class FaultType(Enum):
    NONE = "none"
    CUE_BALL_POCKETED = "cue_ball_pocketed"      # Bi cái vào lỗ
    NO_BALL_HIT = "no_ball_hit"                   # Không chạm bi nào
    WRONG_BALL_FIRST = "wrong_ball_first"         # Chạm bi sai trước
    NO_RAIL_CONTACT = "no_rail_contact"           # Không có bi chạm băng
    BALL_OFF_TABLE = "ball_off_table"             # Bi nhảy khỏi bàn

@dataclass
class BallState:
    """Trạng thái của một bi"""
    ball_id: str
    position: Tuple[float, float]  # (x, y)
    is_pocketed: bool = False
    frame_id: int = 0

@dataclass
class ShotResult:
    """Kết quả một cú đánh"""
    frame_start: int
    frame_end: int
    balls_pocketed: List[str] = field(default_factory=list)
    cue_ball_pocketed: bool = False
    balls_off_table: List[str] = field(default_factory=list)
    lowest_ball_hit_first: bool = False
    rail_contact: bool = False
    fault_type: FaultType = FaultType.NONE
    is_valid: bool = True
    target_ball: Optional[str] = None  # Bi phải đánh (bi nhỏ nhất)

@dataclass
class PlayerState:
    """Trạng thái người chơi"""
    player_id: int
    name: str
    is_current: bool = False
    consecutive_fouls: int = 0
    score: int = 0

@dataclass
class GameSession:
    """Phiên chơi"""
    player1: PlayerState
    player2: PlayerState
    current_shot: Optional[ShotResult] = None
    game_state: GameState = GameState.WAITING
    winner: Optional[int] = None
    
    def get_current_player(self) -> PlayerState:
        return self.player1 if self.player1.is_current else self.player2
    
    def switch_player(self):
        self.player1.is_current = not self.player1.is_current
        self.player2.is_current = not self.player2.is_current


