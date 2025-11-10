# import cv2
# from utils.geometry import GeometryUtils
# import numpy as np
# from utils.geometry import merge_overlapping_detections
# from utils.helpers import Detection
# import copy


# class BallTracker:
#     """
#     BallTracker:
#     - Nhận danh sách detection từ BallDetector.detect()
#     - Gán ID ổn định qua các frame bằng IoU matching
#     - Xử lý mất track, cập nhật ID mới, và gộp label từ frame trước
#     """

#     def __init__(self, iou_threshold=0.6, max_missing_frames=10, table_corners = None):
#         self.iou_threshold = iou_threshold
#         self.max_missing_frames = max_missing_frames

#         self.tracks = {}        
#         self.next_id = 1
#         self.prev_detections = []
#         self.frame_id = 0

#         self.merge_iou_threshold = iou_threshold
#         if table_corners is None:
#             table_corners = np.array([
#                 (370, 250),
#                 (1560, 250),
#                 (1550, 860),
#                 (370, 860)
#             ], np.int32)
#         self.table_corners = table_corners

#     # -------------------------------------------------------------
#     def update(self, detections: list[Detection,Detection,]) -> list:
#         """

#         Cập nhật danh sách bi đang theo dõi với detections mới.
#         Returns:
#             tracked_balls (list[dict]): các bi có ID ổn định
#         """
#         if self.frame_id <= 20:
#             pass
#         if detections is None:
#             detections = []
#         ### - Lấy các bi trong bàn
#         detections = [d for d in detections if cv2.pointPolygonTest(self.table_corners, (d.x, d.y), False) >= 0]


#         # --------- Gộp các detections trùng lặp trong cùng frame (tại cùng vị trí hoặc gần nhau)
#         detections_merged = merge_overlapping_detections(detections, iou_threshold=self.merge_iou_threshold)

#         # -------- Tracking với frame trước - điều chỉnh label detection mới theo label frame trước
#         # 2️-- Gộp label với frame trước
#         if self.prev_detections:
#             for det in detections_merged:
#                 best_iou, best_prev = 0, None
#                 for prev_det in self.prev_detections:
#                     iou = GeometryUtils.compute_iou(det, prev_det)
#                     if iou > best_iou:
#                         best_iou, best_prev = iou, prev_det

#                 # Nếu IoU > threshold, đổi label thành label frame trước
#                 if best_iou > self.iou_threshold:
#                     #-- lấy cũ
#                     det.x = best_prev.x
#                     det.y = best_prev.y
#                     det.r = best_prev.r

#         # 3️-- Lọc mỗi loại bi có confidence cao nhất
#         # detections = self._filter_best_per_class(detections)

 

#         self.prev_detections = [copy.copy(d) for d in detections]
#         self.frame_id +=1
#         return detections
        
 


#     # -------------------------------------------------------------
#     def _filter_best_per_class(self, detections):
#         """Giữ mỗi loại bi có confidence cao nhất."""
#         best = {}
#         for d in detections:
#             name = d.name
#             if name not in best or d.conf > best[name].conf:
#                 best[name] = d
#         return list(best.values())

#     # -------------------------------------------------------------

#     # -------------------------------------------------------------
#     def reset(self):
#         self.tracks.clear()
#         self.prev_detections = []
#         self.next_id = 1


#----------------------------------------------------------------------------------------------------------

import numpy as np
import cv2
from typing import List, Dict, Optional
from collections import deque
from utils.helpers import Detection, BallState

class BallTracker:
    """Theo dõi vị trí và trạng thái các bi qua các frame"""
    
    def __init__(self, distance_threshold=30, missing_threshold=5):
        self.distance_threshold = distance_threshold
        self.missing_threshold = missing_threshold  # Giảm ngưỡng phát hiện bi mất để nhạy hơn
        self.tracked_balls: Dict[str, BallState] = {}
        self.history: deque = deque(maxlen=30)  # Lưu 30 frame gần nhất
        self.confidence_threshold = 0.5  # Ngưỡng độ tin cậy tối thiểu để theo dõi bi
        self.stable_frames_required = 3  # Số frame liên tiếp cần để xác nhận bi mất
        
        # Khởi tạo tọa độ bàn bi-a
        self.table_corners = np.array([
            (370, 250),   # Top-left
            (1560, 250),  # Top-right
            (1550, 860),  # Bottom-right
            (370, 860)    # Bottom-left
        ], np.int32)
        
    def update(self, frame_id: int, detections: List[Detection]):
        """Cập nhật trạng thái bi từ detections"""
        current_frame_balls = {}
        
        # Xử lý các detection
        for det in detections:
            ball_id = det.name
            position = (det.x, det.y)
            
            if ball_id not in self.tracked_balls:
                # Bi mới xuất hiện
                self.tracked_balls[ball_id] = BallState(
                    ball_id=ball_id,
                    position=position,
                    is_pocketed=False,
                    frame_id=frame_id
                )
            else:
                # Cập nhật vị trí bi đã track
                self.tracked_balls[ball_id].position = position
                self.tracked_balls[ball_id].frame_id = frame_id
                self.tracked_balls[ball_id].is_pocketed = False
                
            current_frame_balls[ball_id] = self.tracked_balls[ball_id]
        
        # Lưu lịch sử
        self.history.append({
            'frame_id': frame_id,
            'balls': dict(current_frame_balls)
        })
        
        return current_frame_balls
    
    def get_missing_balls(self, frame_id: int) -> List[str]:
        """Tìm các bi bị mất (có thể vào lỗ hoặc rơi khỏi bàn)"""
        missing = []
        for ball_id, ball_state in self.tracked_balls.items():
            if ball_state.is_pocketed:
                continue
                
            frames_missing = frame_id - ball_state.frame_id
            if frames_missing > self.missing_threshold:
                # Kiểm tra xem bi có thực sự biến mất không bằng cách xem lịch sử
                missing_count = 0
                for hist in reversed(list(self.history)[-self.stable_frames_required:]):
                    if ball_id not in hist['balls']:
                        missing_count += 1
                
                # Chỉ coi là mất nếu bi không xuất hiện trong nhiều frame liên tiếp
                if missing_count >= self.stable_frames_required:
                    # Lấy vị trí cuối cùng đã biết của bi
                    last_position = ball_state.position
                    if last_position:
                        missing.append(ball_id)
                        
        return missing
    
    def mark_pocketed(self, ball_id: str):
        """Đánh dấu bi đã vào lỗ"""
        if ball_id in self.tracked_balls:
            self.tracked_balls[ball_id].is_pocketed = True
    
    def get_active_balls(self) -> List[str]:
        """Lấy danh sách bi còn trên bàn"""
        return [bid for bid, bstate in self.tracked_balls.items() 
                if not bstate.is_pocketed]
    
    def get_last_position(self, ball_id: str):
        """Lấy vị trí cuối cùng đã biết của bi"""
        if ball_id in self.tracked_balls:
            return self.tracked_balls[ball_id]
        return None

    def calculate_movement(self, ball_id: str, frames_back=5) -> float:
        """Tính toán độ di chuyển của bi trong N frame gần nhất"""
        if len(self.history) < 2:
            return 0.0
        
        positions = []
        for hist in list(self.history)[-frames_back:]:
            if ball_id in hist['balls']:
                positions.append(hist['balls'][ball_id].position)
        
        if len(positions) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(1, len(positions)):
            dx = positions[i][0] - positions[i-1][0]
            dy = positions[i][1] - positions[i-1][1]
            total_distance += np.sqrt(dx*dx + dy*dy)
        
        return total_distance