

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from typing import List, Dict, Optional
from collections import deque
from utils.helpers import FaultType, ShotResult


class GameLogic:
    """Xử lý logic game bida 9 bi"""
    
    def __init__(self):
        self.ball_order = [str(i) for i in range(1, 10)]  # Bi 1-9
        self.pocket_zones = self._define_pocket_zones()
        
    def _define_pocket_zones(self):
        """Định nghĩa vùng lỗ (4 góc + 2 giữa cạnh dài)"""
        return [
            {'name': 'top_left', 'x': 370, 'y': 250, 'radius': 45},
            {'name': 'top_right', 'x': 1560, 'y': 250, 'radius': 45},
            {'name': 'mid_left', 'x': 370, 'y': 555, 'radius': 45},
            {'name': 'mid_right', 'x': 1560, 'y': 555, 'radius': 45},
            {'name': 'bottom_left', 'x': 370, 'y': 860, 'radius': 45},
            {'name': 'bottom_right', 'x': 1560, 'y': 860, 'radius': 45},
        ]
    
    def get_lowest_ball(self, active_balls: List[str]) -> Optional[str]:
        """Lấy bi nhỏ nhất còn trên bàn"""
        numbered_balls = [b for b in active_balls if b.isdigit()]
        if not numbered_balls:
            return None
        return min(numbered_balls, key=lambda x: int(x))
    
    def check_ball_in_pocket(self, position: Tuple[float, float]) -> bool:
        """Kiểm tra bi có trong vùng lỗ không"""
        x, y = position
        for pocket in self.pocket_zones:
            dx = x - pocket['x']
            dy = y - pocket['y']
            distance = np.sqrt(dx*dx + dy*dy)
            if distance <= pocket['radius']:
                return True
        return False
    
    def analyze_shot(self, shot_result: ShotResult, active_balls: List[str]) -> Tuple[bool, bool, FaultType]:
        """
        Phân tích cú đánh
        Returns: (is_valid, continue_turn, fault_type)
        """
        is_valid = True
        continue_turn = False
        fault_type = FaultType.NONE
        
        # Kiểm tra bi cái vào lỗ
        if shot_result.cue_ball_pocketed:
            is_valid = False
            fault_type = FaultType.CUE_BALL_POCKETED
            return is_valid, False, fault_type
        
        # Kiểm tra bi nhảy khỏi bàn
        if shot_result.balls_off_table:
            is_valid = False
            fault_type = FaultType.BALL_OFF_TABLE
            return is_valid, False, fault_type
        
        # Kiểm tra đánh bi nhỏ nhất trước
        if not shot_result.lowest_ball_hit_first:
            is_valid = False
            fault_type = FaultType.WRONG_BALL_FIRST
            return is_valid, False, fault_type
        
        # Kiểm tra bi chạm băng (nếu không có bi vào lỗ)
        if not shot_result.balls_pocketed and not shot_result.rail_contact:
            is_valid = False
            fault_type = FaultType.NO_RAIL_CONTACT
            return is_valid, False, fault_type
        
        # Cú đánh hợp lệ
        # Kiểm tra có bi vào lỗ không -> được đánh tiếp
        if shot_result.balls_pocketed:
            continue_turn = True
            # Kiểm tra bi 9 vào lỗ -> thắng
            if '9' in shot_result.balls_pocketed:
                continue_turn = False  # Kết thúc game
        
        return is_valid, continue_turn, fault_type
    
    def check_win_condition(self, shot_result: ShotResult, active_balls: List[str]) -> bool:
        """Kiểm tra điều kiện thắng: bi 9 vào lỗ hợp lệ"""
        if '9' in shot_result.balls_pocketed and shot_result.is_valid:
            return True
        return False
