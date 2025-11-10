import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
from core.tracker import BallTracker
from utils.helpers import  GameState, GameSession, ShotResult, Detection


class Visualizer:
    """Hiển thị trực quan thông tin game lên video"""
    
    def __init__(self, table_width=1920, table_height=1080):
        self.table_width = table_width
        self.table_height = table_height
        
        # Màu sắc
        self.colors = {
            'cue': (255, 255, 255),      # Trắng
            '1': (255, 255, 0),           # Vàng
            '2': (0, 0, 255),             # Đỏ
            '3': (0, 0, 255),             # Đỏ
            '4': (128, 0, 128),           # Tím
            '5': (255, 165, 0),           # Cam
            '6': (0, 255, 0),             # Xanh lá
            '7': (139, 69, 19),           # Nâu
            '8': (0, 0, 0),               # Đen
            '9': (255, 255, 0),           # Vàng sọc
            'default': (128, 128, 128)    # Xám
        }
        
    def draw_ball(self, frame, detection: Detection, is_target=False, is_moving=False):
        """Vẽ bi và thông tin"""
        x, y, r = int(detection.x), int(detection.y), int(detection.r)
        color = self.colors.get(detection.name, self.colors['default'])
        
        # Vẽ vòng tròn bi
        thickness = 3 if is_target else 2
        if is_moving:
            cv2.circle(frame, (x, y), int(r), (0, 255, 255), thickness)  # Vàng khi đang di chuyển
        else:
            cv2.circle(frame, (x, y), int(r), color, thickness)
        
        # Vẽ tâm bi
        cv2.circle(frame, (x, y), 3, color, -1)
        
        # Vẽ số bi
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = detection.name
        text_size = cv2.getTextSize(text, font, 0.6, 2)[0]
        text_x = x - text_size[0] // 2
        text_y = y + text_size[1] // 2
        
        # Background cho text
        cv2.rectangle(frame, 
                     (text_x - 3, text_y - text_size[1] - 3),
                     (text_x + text_size[0] + 3, text_y + 3),
                     (0, 0, 0), -1)
        cv2.putText(frame, text, (text_x, text_y), font, 0.6, (255, 255, 255), 2)
        
        # Đánh dấu bi mục tiêu
        if is_target:
            cv2.putText(frame, "TARGET", (x - 30, y - int(r) - 10), 
                       font, 0.5, (0, 255, 0), 2)
    
    def draw_pockets(self, frame, pocket_zones):
        """Vẽ các lỗ bi"""
        for pocket in pocket_zones:
            x, y = int(pocket['x']), int(pocket['y'])
            radius = int(pocket['radius'])
            cv2.circle(frame, (x, y), radius, (50, 50, 50), 2)
            cv2.circle(frame, (x, y), 5, (255, 0, 0), -1)
    
    def draw_info_panel(self, frame, game_session: GameSession, shot_result: Optional[ShotResult], 
                       active_balls: List[str], frame_id: int):
        """Vẽ bảng thông tin game"""
        panel_height = 200
        panel = np.zeros((panel_height, frame.shape[1], 3), dtype=np.uint8)
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Tiêu đề
        cv2.putText(panel, "POOL 9-BALL GAME TRACKER", (10, 30), 
                   font, 0.8, (0, 255, 255), 2)
        
        # Frame ID
        cv2.putText(panel, f"Frame: {frame_id}", (10, 60), 
                   font, 0.5, (255, 255, 255), 1)
        
        # Trạng thái game
        state_color = {
            GameState.WAITING: (255, 255, 0),
            GameState.SHOOTING: (0, 255, 0),
            GameState.ANALYZING: (255, 165, 0),
            GameState.GAME_OVER: (0, 0, 255)
        }
        cv2.putText(panel, f"State: {game_session.game_state.value.upper()}", 
                   (10, 90), font, 0.5, state_color[game_session.game_state], 2)
        
        # Người chơi
        p1 = game_session.player1
        p2 = game_session.player2
        
        p1_color = (0, 255, 0) if p1.is_current else (200, 200, 200)
        p2_color = (0, 255, 0) if p2.is_current else (200, 200, 200)
        
        cv2.putText(panel, f"Player 1: {p1.name}", (10, 120), 
                   font, 0.5, p1_color, 2 if p1.is_current else 1)
        cv2.putText(panel, f"Fouls: {p1.consecutive_fouls}", (10, 145), 
                   font, 0.4, p1_color, 1)
        
        cv2.putText(panel, f"Player 2: {p2.name}", (300, 120), 
                   font, 0.5, p2_color, 2 if p2.is_current else 1)
        cv2.putText(panel, f"Fouls: {p2.consecutive_fouls}", (300, 145), 
                   font, 0.4, p2_color, 1)
        
        # Bi trên bàn
        cv2.putText(panel, f"Balls on table: {len(active_balls)}", (600, 60), 
                   font, 0.5, (255, 255, 255), 1)
        balls_text = ", ".join(sorted(active_balls, key=lambda x: int(x) if x.isdigit() else 0))
        cv2.putText(panel, balls_text[:50], (600, 90), 
                   font, 0.4, (200, 200, 200), 1)
        
        # Thông tin cú đánh hiện tại
        if shot_result:
            cv2.putText(panel, f"Target Ball: {shot_result.target_ball or 'N/A'}", 
                       (600, 120), font, 0.5, (0, 255, 255), 1)
            
            if shot_result.balls_pocketed:
                pocketed_text = ", ".join(shot_result.balls_pocketed)
                cv2.putText(panel, f"Pocketed: {pocketed_text}", 
                           (600, 145), font, 0.4, (0, 255, 0), 1)
        
        # Thông báo thắng/thua
        if game_session.winner:
            winner_name = f"Player {game_session.winner}"
            cv2.putText(panel, f"WINNER: {winner_name}!", (10, 180), 
                       font, 0.7, (0, 255, 0), 2)
        
        return panel
    
    def draw_shot_info(self, frame, shot_result: ShotResult):
        """Vẽ thông tin cú đánh"""
        if not shot_result:
            return
        
        y_offset = 50
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Trạng thái cú đánh
        if shot_result.is_valid:
            status_text = "VALID SHOT"
            status_color = (0, 255, 0)
        else:
            status_text = f"FOUL: {shot_result.fault_type.value}"
            status_color = (0, 0, 255)
        
        # Background
        text_size = cv2.getTextSize(status_text, font, 0.7, 2)[0]
        cv2.rectangle(frame, 
                     (frame.shape[1] - text_size[0] - 20, y_offset - 30),
                     (frame.shape[1] - 10, y_offset + 5),
                     (0, 0, 0), -1)
        
        cv2.putText(frame, status_text, 
                   (frame.shape[1] - text_size[0] - 15, y_offset), 
                   font, 0.7, status_color, 2)
        
        # Chi tiết
        details = []
        if shot_result.cue_ball_pocketed:
            details.append("Cue ball pocketed")
        if shot_result.balls_off_table:
            details.append(f"Off table: {', '.join(shot_result.balls_off_table)}")
        
        for i, detail in enumerate(details):
            cv2.putText(frame, detail, 
                       (frame.shape[1] - 300, y_offset + 30 + i * 25), 
                       font, 0.4, (255, 100, 100), 1)
    
    def draw_trajectory(self, frame, tracker: BallTracker, ball_id: str, frames=10):
        """Vẽ quỹ đạo di chuyển của bi"""
        positions = []
        for hist in list(tracker.history)[-frames:]:
            if ball_id in hist['balls']:
                pos = hist['balls'][ball_id].position
                positions.append((int(pos[0]), int(pos[1])))
        
        if len(positions) > 1:
            for i in range(1, len(positions)):
                cv2.line(frame, positions[i-1], positions[i], (255, 0, 255), 2)
                cv2.circle(frame, positions[i], 3, (255, 0, 255), -1)

