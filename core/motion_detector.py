from typing import List, Dict, Optional, Tuple
from utils.helpers import FaultType, ShotResult
import numpy as np
from core.tracker import BallTracker

def calculate_distance(p1, p2):
    """Tính khoảng cách giữa hai điểm"""
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return np.sqrt(dx*dx + dy*dy)

class VelocityVector:
    def __init__(self, vx: float = 0, vy: float = 0):
        self.vx = vx
        self.vy = vy
        self.magnitude = np.sqrt(vx*vx + vy*vy)
        self.direction = np.arctan2(vy, vx) if (vx != 0 or vy != 0) else 0

class BallMotionState:
    def __init__(self):
        self.positions = []  # List of (frame_id, x, y) tuples
        self.velocities = []  # List of VelocityVector objects
        self.is_moving = False
        self.last_collision_frame = None
        self.collision_count = 0

class MotionDetector:
    """Phát hiện chuyển động, cú đánh và va chạm"""
    
    def __init__(self, motion_threshold=5.0, stable_frames=15):
        self.motion_threshold = motion_threshold
        self.stable_frames = stable_frames
        self.stable_count = 0
        self.is_shooting = False
        self.shot_start_frame = None
        
        # Tham số phát hiện va chạm
        self.contact_margin = 10.0  # Margin cho phát hiện va chạm
        self.move_thresh = 0.3  # Ngưỡng di chuyển (30% bán kính)
        self.velocity_thresh = 2.0  # Ngưỡng vận tốc tối thiểu (pixels/frame)
        
        # Lịch sử và trạng thái
        self.collision_history = []  # Lưu lịch sử va chạm
        self.rail_contact_history = []  # Lưu lịch sử chạm băng
        self.first_hit_ball = None  # Bi đầu tiên bị chạm trong cú đánh
        self.ball_states = {}  # Dictionary lưu trạng thái chuyển động của từng bi
        
        # Buffer cho tính toán vận tốc
        self.position_buffer_size = 3  # Số frame để tính vận tốc
        self.velocity_history = {}  # Lưu lịch sử vận tốc của các bi
        
        # Định nghĩa ranh giới bàn
        self.table_bounds = {
            'left': 370,    # Cạnh trái
            'right': 1560,  # Cạnh phải
            'top': 250,     # Cạnh trên
            'bottom': 860   # Cạnh dưới
        }
        self.rail_margin = 50  # Khoảng cách để xác định chạm băng
        
    def detect_motion(self, tracker: BallTracker, frame_id: int) -> Tuple[bool, bool, List[dict]]:
        """
        Phát hiện chuyển động và va chạm
        Returns: (is_moving, shot_started, collisions)
        """
        current_balls = tracker.tracked_balls
        active_balls = tracker.get_active_balls()
        if not active_balls:
            return False, False, []
        
        # Cập nhật trạng thái chuyển động cho tất cả các bi
        moving_balls = []
        for ball_id, ball_state in current_balls.items():
            if not ball_state.is_pocketed:
                self.update_ball_state(ball_id, frame_id, ball_state.position)
                if ball_id in self.ball_states and self.ball_states[ball_id].is_moving:
                    moving_balls.append(ball_id)
        
        is_moving = len(moving_balls) > 0
        shot_started = False
        collisions = []
        
        if is_moving and 'cue' in current_balls:
            cue_ball = current_balls['cue']
            cue_pos = cue_ball.position
            
            # Kiểm tra bi cái chạm băng
            rail_hit = self.check_rail_contact(cue_pos)
            if rail_hit:
                self.rail_contact_history.append(rail_hit)
            
            # Kiểm tra va chạm với từng bi khác
            for ball_id, ball_state in current_balls.items():
                if ball_id == 'cue' or ball_state.is_pocketed:
                    continue
                
                ball_pos = ball_state.position
                # Kiểm tra bi khác chạm băng
                rail_hit = self.check_rail_contact(ball_pos)
                if rail_hit:
                    self.rail_contact_history.append(rail_hit)
                
                # Tính khoảng cách giữa bi cái và bi khác
                distance = calculate_distance(cue_pos, ball_pos)
                
                # Phát hiện va chạm dựa trên khoảng cách và vận tốc
                if distance <= (30 + self.contact_margin):
                    is_collision = self.detect_collision_by_velocity('cue', ball_id)
                    if is_collision:
                        collision_info = {
                            'frame_id': frame_id,
                            'ball_id': ball_id,
                            'distance': distance,
                            'velocity_change': True
                        }
                        collisions.append(collision_info)
                        
                        # Ghi nhận bi đầu tiên bị chạm
                        if self.first_hit_ball is None:
                            self.first_hit_ball = ball_id
                            
            if is_moving:
                self.stable_count = 0
                if not self.is_shooting:
                    # Bắt đầu cú đánh mới
                    self.is_shooting = True
                    self.shot_start_frame = frame_id
                    shot_started = True
                    self.collision_history.clear()
                    self.ball_states.clear()
            else:
                self.stable_count += 1
                if self.stable_count >= self.stable_frames and self.is_shooting:
                    # Kết thúc cú đánh
                    self.is_shooting = False
        
        # Cập nhật lịch sử va chạm
        if collisions:
            self.collision_history.extend(collisions)
        
        return is_moving, shot_started, collisions
    
    def is_shot_ended(self) -> bool:
        """Kiểm tra cú đánh đã kết thúc chưa"""
        return not self.is_shooting and self.shot_start_frame is not None
    
    def calculate_velocity(self, positions: List[Tuple[int, float, float]]) -> VelocityVector:
        """Tính vector vận tốc từ các vị trí liên tiếp"""
        if len(positions) < 2:
            return VelocityVector()
            
        # Lấy 2 frame gần nhất
        frame_t, x_t, y_t = positions[-1]
        frame_t_1, x_t_1, y_t_1 = positions[-2]
        
        # Tính vận tốc
        vx = x_t - x_t_1
        vy = y_t - y_t_1
        
        return VelocityVector(vx, vy)
    
    def update_ball_state(self, ball_id: str, frame_id: int, position: Tuple[float, float]):
        """Cập nhật trạng thái chuyển động của bi"""
        if ball_id not in self.ball_states:
            self.ball_states[ball_id] = BallMotionState()
        
        state = self.ball_states[ball_id]
        state.positions.append((frame_id, position[0], position[1]))
        
        # Giữ lại buffer_size frame gần nhất
        if len(state.positions) > self.position_buffer_size:
            state.positions.pop(0)
        
        # Tính vận tốc nếu có đủ dữ liệu
        if len(state.positions) >= 2:
            velocity = self.calculate_velocity(state.positions)
            state.velocities.append(velocity)
            if len(state.velocities) > self.position_buffer_size:
                state.velocities.pop(0)
            
            # Cập nhật trạng thái chuyển động
            state.is_moving = velocity.magnitude > self.velocity_thresh
    
    def check_rail_contact(self, ball_pos) -> str:
        """Kiểm tra bi có chạm băng không và trả về băng nào"""
        x, y = ball_pos
        if abs(x - self.table_bounds['left']) <= self.rail_margin:
            return 'left'
        if abs(x - self.table_bounds['right']) <= self.rail_margin:
            return 'right'
        if abs(y - self.table_bounds['top']) <= self.rail_margin:
            return 'top'
        if abs(y - self.table_bounds['bottom']) <= self.rail_margin:
            return 'bottom'
        return None
        
    def detect_collision_by_velocity(self, ball1_id: str, ball2_id: str) -> bool:
        """Phát hiện va chạm dựa trên thay đổi vận tốc"""
        if (ball1_id not in self.ball_states or 
            ball2_id not in self.ball_states):
            return False
            
        ball1_state = self.ball_states[ball1_id]
        ball2_state = self.ball_states[ball2_id]
        
        if (len(ball1_state.velocities) < 2 or 
            len(ball2_state.velocities) < 2):
            return False
            
        # Kiểm tra thay đổi đột ngột trong vận tốc
        v1_before = ball1_state.velocities[-2]
        v1_after = ball1_state.velocities[-1]
        v2_before = ball2_state.velocities[-2]
        v2_after = ball2_state.velocities[-1]
        
        # Tính thay đổi vận tốc
        v1_change = abs(v1_after.magnitude - v1_before.magnitude)
        v2_change = abs(v2_after.magnitude - v2_before.magnitude)
        
        # Nếu cả hai bi đều có thay đổi vận tốc đáng kể
        return (v1_change > self.velocity_thresh and 
                v2_change > self.velocity_thresh)

    def get_shot_summary(self) -> dict:
        """Lấy tổng kết về cú đánh hiện tại"""
        return {
            'rail_contacts': list(set(self.rail_contact_history)),  # Loại bỏ trùng lặp
            'first_hit_ball': self.first_hit_ball,
            'has_rail_contact': len(self.rail_contact_history) > 0
        }

    def reset_shot(self):
        """Reset trạng thái cú đánh"""
        self.shot_start_frame = None
        self.stable_count = 0
        self.collision_history.clear()
        self.rail_contact_history.clear()
        self.first_hit_ball = None
        self.ball_states.clear()
        self.velocity_history.clear()


# ===== core/game_logic.py =====
class GameLogic:
    """Xử lý logic game bida 9 bi"""
    
    def __init__(self):
        self.ball_order = [str(i) for i in range(1, 10)]  # Bi 1-9
        self.pocket_zones = self._define_pocket_zones()
        
    def _define_pocket_zones(self):
        """Định nghĩa vùng lỗ (4 góc + 2 giữa cạnh dài)"""
        # TODO: Điều chỉnh tọa độ theo kích thước bàn thực tế
        return [
            {'name': 'top_left', 'x': 50, 'y': 50, 'radius': 40},
            {'name': 'top_right', 'x': 950, 'y': 50, 'radius': 40},
            {'name': 'mid_left', 'x': 50, 'y': 500, 'radius': 40},
            {'name': 'mid_right', 'x': 950, 'y': 500, 'radius': 40},
            {'name': 'bottom_left', 'x': 50, 'y': 950, 'radius': 40},
            {'name': 'bottom_right', 'x': 950, 'y': 950, 'radius': 40},
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