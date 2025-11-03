import os
import cv2
import numpy as np


def ensure_dir(path):
    """
    Tạo thư mục nếu chưa tồn tại.
    Args:
        path (str): Đường dẫn thư mục.
    """
    if not os.path.exists(path):
        os.makedirs(path)


def distance(b1, b2):

    return np.sqrt((b1["x"] - b2["x"]) ** 2 + (b1["y"] - b2["y"]) ** 2)


def draw_circle(frame, ball, color=(0, 255, 0), thickness=2):
  
    center = (int(ball["x"]), int(ball["y"]))
    radius = int(ball["r"])
    cv2.circle(frame, center, radius, color, thickness)
    cv2.circle(frame, center, 3, color, -1)


def get_moving_balls(frames_data, idx, ball_name, move_thresh=0.3):

    if idx - 1 < 0:
        return False
    prev_balls = frames_data[idx - 1]["balls"]
    b_prev = next((b for b in prev_balls if b["name"] == ball_name), None)
    if b_prev is None:
        return False
    

    curr = frames_data[idx]["balls"]
    b_curr = next((b for b in curr if b["name"] == ball_name), None)
    
    # Trường hợp 1: ball có detect ở frame hiện tại
    if b_curr is not None:
        d = distance(b_curr, b_prev)
        if d > b_curr["r"] * move_thresh:
            return True
        return False
    
    # Trường hợp 2: ball mất detect ở frame N, kiểm tra N+1 đến N+9
    for offset in range(1, 10):
        if idx + offset >= len(frames_data):
            return True
        
        next_balls = frames_data[idx + offset]["balls"]
        b_next = next((b for b in next_balls if b["name"] == ball_name), None)
        
        if b_next is not None:
            d = distance(b_next, b_prev)
            if d > b_prev["r"] * move_thresh:
                return True
            return False
    
    return True
