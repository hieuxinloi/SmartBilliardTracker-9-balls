"""
Enhanced ball detection with pocket detection logic
Tracks ball disappearance to detect potted balls
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional


class BallTracker:
    """Track balls across frames to detect pocketing"""

    def __init__(self, disappearance_threshold: int = 30):
        """
        Initialize ball tracker

        Args:
            disappearance_threshold: Number of frames a ball must be missing to be considered potted
        """
        self.ball_history: Dict[str, List[Dict]] = {}  # ball_name -> list of detections
        self.last_seen: Dict[str, int] = {}  # ball_name -> last frame number
        self.potted_balls: Dict[str, int] = {}  # ball_name -> frame where potted
        self.disappearance_threshold = disappearance_threshold

    def update(self, frame_id: int, detections: List[Dict[str, Any]]):
        """
        Update tracker with new detections

        Args:
            frame_id: Current frame number
            detections: List of ball detections in current frame

        Returns:
            List of newly potted balls in this frame
        """
        detected_balls = set()
        newly_potted = []

        # Process current detections
        for detection in detections:
            ball_name = detection["name"]
            detected_balls.add(ball_name)

            # Update history
            if ball_name not in self.ball_history:
                self.ball_history[ball_name] = []

            self.ball_history[ball_name].append(
                {
                    "frame": frame_id,
                    "x": detection["x"],
                    "y": detection["y"],
                    "confidence": detection.get("confidence", 1.0),
                }
            )

            # Update last seen
            self.last_seen[ball_name] = frame_id

        # Check for disappeared balls
        for ball_name, last_frame in list(self.last_seen.items()):
            # Skip if already marked as potted
            if ball_name in self.potted_balls:
                continue

            # Check if ball has disappeared
            frames_missing = frame_id - last_frame

            if frames_missing >= self.disappearance_threshold:
                # Ball has been missing long enough - consider it potted
                self.potted_balls[ball_name] = last_frame
                newly_potted.append(
                    {
                        "ball_name": ball_name,
                        "frame_potted": last_frame,
                        "frame_detected": frame_id,
                        "position": self._get_last_position(ball_name),
                    }
                )

        return newly_potted

    def _get_last_position(self, ball_name: str) -> Optional[Tuple[float, float]]:
        """Get the last known position of a ball"""
        if ball_name not in self.ball_history or not self.ball_history[ball_name]:
            return None

        last_detection = self.ball_history[ball_name][-1]
        return (last_detection["x"], last_detection["y"])

    def is_potted(self, ball_name: str) -> bool:
        """Check if a ball has been potted"""
        return ball_name in self.potted_balls

    def get_potted_balls(self) -> List[str]:
        """Get list of all potted balls"""
        return list(self.potted_balls.keys())

    def get_active_balls(self) -> List[str]:
        """Get list of balls still on table"""
        all_balls = set(self.ball_history.keys())
        potted = set(self.potted_balls.keys())
        return list(all_balls - potted)

    def reset(self):
        """Reset tracker for new game"""
        self.ball_history.clear()
        self.last_seen.clear()
        self.potted_balls.clear()


def detect_pockets(
    frame_width: int, frame_height: int, margin_ratio: float = 0.05
) -> List[Dict[str, Any]]:
    """
    Define pocket locations for a standard pool table

    Args:
        frame_width: Width of video frame
        frame_height: Height of video frame
        margin_ratio: Ratio of frame size to use as pocket detection margin

    Returns:
        List of pocket definitions with positions and detection zones
    """
    margin_x = int(frame_width * margin_ratio)
    margin_y = int(frame_height * margin_ratio)

    pockets = [
        # Corner pockets
        {
            "name": "top_left",
            "x": margin_x,
            "y": margin_y,
            "zone": (0, 0, margin_x * 2, margin_y * 2),
        },
        {
            "name": "top_right",
            "x": frame_width - margin_x,
            "y": margin_y,
            "zone": (frame_width - margin_x * 2, 0, frame_width, margin_y * 2),
        },
        {
            "name": "bottom_left",
            "x": margin_x,
            "y": frame_height - margin_y,
            "zone": (0, frame_height - margin_y * 2, margin_x * 2, frame_height),
        },
        {
            "name": "bottom_right",
            "x": frame_width - margin_x,
            "y": frame_height - margin_y,
            "zone": (
                frame_width - margin_x * 2,
                frame_height - margin_y * 2,
                frame_width,
                frame_height,
            ),
        },
        # Side pockets
        {
            "name": "middle_left",
            "x": margin_x,
            "y": frame_height // 2,
            "zone": (
                0,
                frame_height // 2 - margin_y,
                margin_x * 2,
                frame_height // 2 + margin_y,
            ),
        },
        {
            "name": "middle_right",
            "x": frame_width - margin_x,
            "y": frame_height // 2,
            "zone": (
                frame_width - margin_x * 2,
                frame_height // 2 - margin_y,
                frame_width,
                frame_height // 2 + margin_y,
            ),
        },
    ]

    return pockets


def is_ball_in_pocket(ball_pos: Tuple[float, float], pocket: Dict[str, Any]) -> bool:
    """
    Check if a ball position is within a pocket zone

    Args:
        ball_pos: (x, y) position of ball
        pocket: Pocket definition with zone

    Returns:
        True if ball is in pocket zone
    """
    x, y = ball_pos
    x1, y1, x2, y2 = pocket["zone"]

    return x1 <= x <= x2 and y1 <= y <= y2


def analyze_trajectory_for_pocketing(
    ball_history: List[Dict], pockets: List[Dict[str, Any]]
) -> Optional[str]:
    """
    Analyze ball trajectory to determine which pocket it likely went into

    Args:
        ball_history: List of ball positions over time
        pockets: List of pocket definitions

    Returns:
        Name of pocket ball went into, or None if unclear
    """
    if len(ball_history) < 2:
        return None

    # Get last few positions
    recent_positions = ball_history[-5:]
    last_pos = (recent_positions[-1]["x"], recent_positions[-1]["y"])

    # Check which pocket the ball was closest to
    min_distance = float("inf")
    closest_pocket = None

    for pocket in pockets:
        # Calculate distance to pocket center
        dx = last_pos[0] - pocket["x"]
        dy = last_pos[1] - pocket["y"]
        distance = np.sqrt(dx**2 + dy**2)

        if distance < min_distance:
            min_distance = distance
            closest_pocket = pocket["name"]

    # If ball was moving toward closest pocket, return it
    if len(recent_positions) >= 2:
        prev_pos = (recent_positions[-2]["x"], recent_positions[-2]["y"])

        for pocket in pockets:
            if pocket["name"] == closest_pocket:
                # Check if ball was in pocket zone or moving toward it
                if is_ball_in_pocket(last_pos, pocket):
                    return closest_pocket

                # Calculate velocity direction
                vx = last_pos[0] - prev_pos[0]
                vy = last_pos[1] - prev_pos[1]

                # Direction to pocket
                dx = pocket["x"] - last_pos[0]
                dy = pocket["y"] - last_pos[1]

                # Dot product to check if moving toward pocket
                dot = vx * dx + vy * dy
                if dot > 0:  # Moving toward pocket
                    return closest_pocket

    return None
