"""
SmartBilliardTracker Backend API
FastAPI server for 9-ball billiards AI referee system
"""

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import sys
import json
import asyncio
import cv2
from datetime import datetime
from pathlib import Path
import shutil
import numpy as np
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create game events log file
game_events_logger = logging.getLogger('game_events')
game_events_logger.setLevel(logging.INFO)
game_log_dir = Path('backend/logs')
game_log_dir.mkdir(parents=True, exist_ok=True)
game_log_file = game_log_dir / f'game_events_{datetime.now().strftime("%Y%m%d")}.log'
file_handler = logging.FileHandler(game_log_file)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
game_events_logger.addHandler(file_handler)

# Add parent directory to path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ball_detect import detect_video, YOLO
from detect_collision import get_collisions_from_data
from game_manager import GameManager, GameState
from pocket_detection import BallTracker

app = FastAPI(
    title="SmartBilliardTracker API",
    description="AI-powered 9-ball billiards referee system",
    version="2.0.0",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory setup
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
DATA_DIR = Path("backend/data")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Global game state
game_manager = GameManager()
# Quick pocket detection: 10 frames (~0.33 seconds at 30fps) missing + 5 frames static check
ball_tracker = BallTracker(
    disappearance_threshold=10,  # Must be missing for 10 frames (0.33 seconds)
    static_window=5,  # Check last 5 detections for movement
    static_thresh=3.0,  # Max 3.0 pixels movement to be considered static
)
active_detection_task = None
detection_stop_event = asyncio.Event()
# Use a simple variable to store latest frame instead of queue (avoids frame dropping)
latest_frame: bytes = b""
frame_lock = asyncio.Lock()


# ============= Models =============
class GameStartRequest(BaseModel):
    player1_name: str
    player2_name: str
    starting_player: int = 0  # 0 or 1
    use_camera: bool = False
    video_path: Optional[str] = None


class GameStopRequest(BaseModel):
    reason: str = "user_stop"


class PlayerInfo(BaseModel):
    id: int
    name: str
    potted_balls: List[int]
    foul_count: int
    is_current: bool


class GameStateResponse(BaseModel):
    state: str
    match_id: Optional[str]
    players: List[PlayerInfo]
    current_player: Optional[str]
    balls_on_table: List[int]
    lowest_ball: int
    last_hit_ball: Optional[int]
    balls_moving: bool


# ============= WebSocket Manager =============
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WebSocket] Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WebSocket] Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[WebSocket] Error sending to client: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


# ============= Helper Functions =============
def convert_numpy_types(obj):
    """Recursively convert numpy types to Python native types"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj


async def process_frame_for_game(frame, frame_idx, model, prev_frame_detections):
    """
    Process a single frame for ball detection

    Returns:
        Tuple of (balls_detected, prev_frame_detections)
    """
    try:
        # Run YOLO detection
        results = model.predict(source=frame, conf=0.1, verbose=False)[0]
        boxes = (
            results.boxes.xyxy.cpu().numpy() if results.boxes.xyxy.numel() > 0 else []
        )
        confs = (
            results.boxes.conf.cpu().numpy() if results.boxes.conf.numel() > 0 else []
        )
        classes = (
            results.boxes.cls.cpu().numpy().astype(int)
            if results.boxes.cls.numel() > 0
            else []
        )
        names = [model.names[c] for c in classes] if len(classes) else []

        detections = []
        for box, conf, name in zip(boxes, confs, names):
            if conf < 0.1:
                continue
            x1, y1, x2, y2 = box
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            r = max((x2 - x1), (y2 - y1)) / 2
            detections.append(
                {
                    "name": name,
                    "x": float(cx),
                    "y": float(cy),
                    "r": float(r),
                    "conf": float(conf),
                }
            )

        # Step 1: Merge overlapping detections in same frame (like video processing)
        from ball_detect import merge_overlapping_detections, compute_iou

        detections_merged = merge_overlapping_detections(detections, iou_threshold=0.7)

        # Step 2: IoU-based tracking - correct labels using previous frame (like video processing)
        if prev_frame_detections:
            for det in detections_merged:
                best_iou = 0
                best_prev_det = None
                for prev_det in prev_frame_detections:
                    iou = compute_iou(det, prev_det)
                    if iou > best_iou:
                        best_iou = iou
                        best_prev_det = prev_det

                # If IoU > threshold, use previous frame's label (corrects misdetections)
                if best_iou > 0.7:
                    det["name"] = best_prev_det["name"]

        # Step 3: Keep best detection per class (like video processing)
        best_per_class = {}
        for det in detections_merged:
            cls = det["name"]
            if cls not in best_per_class or det["conf"] > best_per_class[cls]["conf"]:
                best_per_class[cls] = det

        detections_filtered = list(best_per_class.values())

        return detections_filtered, detections_filtered

    except Exception as e:
        print(f"[ERROR] Frame {frame_idx} processing: {e}")
        return [], []


async def detect_pockets(frame_idx, balls):
    """
    Detect if any balls have been potted using BallTracker

    Args:
        frame_idx: Current frame number
        balls: List of detected balls in current frame

    Returns:
        List of newly potted ball names
    """
    global ball_tracker

    # Convert balls to detection format
    detections = []
    for ball in balls:
        detections.append(
            {
                "name": ball["name"],
                "x": ball["x"],
                "y": ball["y"],
                "confidence": ball.get("confidence", 1.0),
            }
        )

    # Update tracker and get newly potted balls
    newly_potted = ball_tracker.update(frame_idx, detections)

    # Return list of ball names that were just potted
    return [potted["ball_name"] for potted in newly_potted]


# ============= Real-time Detection Task =============
async def real_time_detection_task(
    video_source, model_path="models/yolov8n-ball-v.1.0.0.pt"
):
    """
    Real-time ball detection and game event processing

    Args:
        video_source: Path to video file or camera index (0 for webcam)
        model_path: Path to YOLO model
    """
    global game_manager

    try:
        # Load YOLO model
        print(f"[Detection] Loading model: {model_path}")
        model = YOLO(model_path)

        # Open video source
        if isinstance(video_source, int) or video_source == "camera":
            cap = cv2.VideoCapture(0)
            print("[Detection] Using camera feed")
        else:
            cap = cv2.VideoCapture(video_source)
            print(f"[Detection] Using video: {video_source}")

        if not cap.isOpened():
            await manager.broadcast(
                {"event": "error", "message": "Failed to open video source"}
            )
            return

        fps = int(cap.get(cv2.CAP_PROP_FPS)) if cap.get(cv2.CAP_PROP_FPS) > 0 else 30
        frame_delay = 1.0 / fps

        frame_idx = 0
        prev_frame_data = None
        prev_frame_detections = []  # For IoU-based tracking (like video processing)
        frames_buffer = (
            []
        )  # Store ALL frames for collision detection (like video processing)
        processed_collision_ids = (
            set()
        )  # Track collisions for game events (to avoid duplicate events)
        logged_collision_ids = (
            set()
        )  # Track collisions for log file (to avoid duplicates in JSON)
        recent_collisions = (
            []
        )  # Track recent collisions for visualization (frame_idx, ball_data)
        all_collisions = []  # Track all collisions for logging to file

        # Prepare collision log file path
        video_name = (
            Path(video_source).stem if isinstance(video_source, str) else "camera"
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        collision_log_file = f"outputs/{video_name}_{timestamp}_collisions.json"
        os.makedirs("outputs", exist_ok=True)

        # Notify game started
        await manager.broadcast(
            {
                "event": "detection_start",
                "message": "AI detection started",
                "game_state": convert_numpy_types(game_manager.get_game_state()),
            }
        )

        while game_manager.state == GameState.PLAYING:
            # Check stop event
            if detection_stop_event.is_set():
                print("[Detection] Stop event received")
                break

            ret, frame = cap.read()
            if not ret:
                if isinstance(video_source, str):  # Video file ended
                    print("[Detection] Video ended")

                    # Collision log is already saved in real-time
                    if all_collisions:
                        print(
                            f"[COLLISION LOG] Final count: {len(all_collisions)} collisions saved to {collision_log_file}"
                        )

                    break
                continue

            frame_idx += 1

            # Process frame with IoU-based tracking (like video processing)
            balls, prev_frame_detections = await process_frame_for_game(
                frame, frame_idx, model, prev_frame_detections
            )

            # Store frame data
            current_frame_data = {"frame_idx": frame_idx, "balls": balls}
            frames_buffer.append(current_frame_data)

            # Don't limit buffer size - keep ALL frames like video processing does
            # This ensures we don't miss any collisions

            # Check ball movement
            if prev_frame_data and len(frames_buffer) >= 2:
                # Simple movement detection
                cueball_prev = next(
                    (b for b in prev_frame_data["balls"] if b["name"] == "cueball"),
                    None,
                )
                cueball_now = next((b for b in balls if b["name"] == "cueball"), None)

                is_moving = False
                if cueball_prev and cueball_now:
                    dist = np.sqrt(
                        (cueball_now["x"] - cueball_prev["x"]) ** 2
                        + (cueball_now["y"] - cueball_prev["y"]) ** 2
                    )
                    is_moving = bool(dist > 2.0)  # Convert numpy.bool_ to Python bool

                game_manager.update_movement(is_moving)

            # Collision detection on recent frames to catch new collisions
            if len(frames_buffer) >= 2:
                # Check if cueball is present in current frame
                cueball_present = any(b["name"] == "cueball" for b in balls)

                if not cueball_present:
                    if frame_idx % 60 == 0:
                        print(
                            f"[COLLISION] Skipping - cueball not found at frame {frame_idx}"
                        )

                # Run collision detection on ALL frames (same as video processing)
                # The duplicate prevention with processed_collision_ids ensures we only handle new collisions
                try:
                    collisions = get_collisions_from_data(
                        frames_buffer,  # Use ALL frames like video processing
                        cue_ball_name="cueball",
                        move_thresh=0.3,  # Same as video processing
                        contact_margin=10.0,  # Same as video processing
                    )

                    # Log collision detection results with details
                    if collisions:
                        collision_details = ", ".join(
                            [f"{c['ball']['name']}" for c in collisions]
                        )
                        print(
                            f"[COLLISION] Detected {len(collisions)} collision(s) at frame {frame_idx}: {collision_details}"
                        )
                    elif cueball_present and frame_idx % 60 == 0:
                        # Log periodically when no collisions detected but cueball is present
                        print(
                            f"[COLLISION] No collisions detected at frame {frame_idx} (cueball present)"
                        )

                    # Process each collision (avoid duplicates)
                    for coll in collisions:
                        ball_name = coll["ball"]["name"]

                        # Create unique ID for this collision
                        collision_id = (coll["frame_id"], ball_name)

                        # Skip if already processed (prevents duplicate game events)
                        if collision_id in processed_collision_ids:
                            # Already handled this collision - skip silently
                            continue

                        processed_collision_ids.add(collision_id)

                        collision_event = game_manager.process_collision(ball_name)
                        collision_event["frame_idx"] = coll["frame_id"]
                        collision_event["cueball"] = convert_numpy_types(
                            coll["cueball"]
                        )
                        collision_event["ball"] = convert_numpy_types(coll["ball"])

                        # Log collision details to console
                        print(
                            f"[COLLISION] Frame {coll['frame_id']}: cueball hit {ball_name}"
                        )
                        print(
                            f"  Cueball pos: ({coll['cueball']['x']:.1f}, {coll['cueball']['y']:.1f})"
                        )
                        print(
                            f"  Ball pos: ({coll['ball']['x']:.1f}, {coll['ball']['y']:.1f})"
                        )
                        print(f"  Valid: {collision_event.get('valid', True)}")

                        # Store collision for visualization (keep for ~30 frames)
                        recent_collisions.append(
                            {
                                "frame_idx": frame_idx,
                                "cueball": coll["cueball"],
                                "ball": coll["ball"],
                                "ball_name": ball_name,
                            }
                        )

                        # Store collision permanently for log file (merge sequential collisions)
                        if collision_id not in logged_collision_ids:
                            # Check if this is a sequential collision (same ball, within 2 frames of last)
                            should_log = True
                            if all_collisions:
                                last_collision = all_collisions[-1]
                                same_ball = last_collision["ball"]["name"] == ball_name
                                frame_gap = (
                                    coll["frame_id"] - last_collision["frame_id"]
                                )

                                # If same ball and within 2 frames, it's a sequential collision - skip
                                if same_ball and 0 < frame_gap <= 2:
                                    should_log = False
                                    print(
                                        f"[COLLISION] Skipping sequential collision: {ball_name} at frame {coll['frame_id']} (already logged at {last_collision['frame_id']})"
                                    )

                            if should_log:
                                logged_collision_ids.add(collision_id)
                                collision_data = {
                                    "frame_id": coll["frame_id"],
                                    "cueball": convert_numpy_types(coll["cueball"]),
                                    "ball": convert_numpy_types(coll["ball"]),
                                    "valid": collision_event.get("valid", True),
                                    "player": collision_event.get("player", ""),
                                }
                                all_collisions.append(collision_data)

                                # Save to file immediately (real-time logging) - only when new collision added
                                try:
                                    with open(collision_log_file, "w") as f:
                                        json.dump(
                                            {
                                                "video": video_source,
                                                "timestamp": timestamp,
                                                "total_collisions": len(all_collisions),
                                                "collisions": all_collisions,
                                            },
                                            f,
                                            indent=2,
                                        )
                                except Exception as e:
                                    print(f"[ERROR] Failed to save collision log: {e}")

                        await manager.broadcast(collision_event)

                        # Check for foul if invalid hit
                        if not collision_event.get("valid", True):
                            foul_event = game_manager.process_foul(
                                collision_event.get("foul_reason", "Invalid hit")
                            )
                            await manager.broadcast(foul_event)

                except Exception as e:
                    print(f"[ERROR] Collision detection: {e}")

            # Check for potted balls using new ball tracking system
            try:
                # Extract ball numbers from detections
                detected_ball_numbers = []
                cueball_detected = False

                for ball in balls:
                    if ball["name"] == "cueball":
                        cueball_detected = True
                    elif ball["name"].startswith("bi"):
                        try:
                            ball_num = int(ball["name"].replace("bi", ""))
                            if 1 <= ball_num <= 9:
                                detected_ball_numbers.append(ball_num)
                        except (ValueError, AttributeError):
                            pass

                # Log detection every 30 frames for debugging
                if frame_idx % 30 == 0:
                    print(
                        f"[DETECT] Frame {frame_idx}: Cueball={cueball_detected}, Balls={sorted(detected_ball_numbers)}"
                    )

                # Update ball tracking (handles potted, reappeared, scratch)
                tracking_events = game_manager.update_ball_tracking(
                    frame_idx, detected_ball_numbers, cueball_detected
                )

                # Broadcast all tracking events
                for event in tracking_events:
                    event["frame_idx"] = frame_idx
                    await manager.broadcast(event)

                    # Log events
                    event_type = event.get("event")
                    if event_type == "potted":
                        print(
                            f"[POCKET] Ball {event.get('ball')} potted at frame {frame_idx}"
                        )
                    elif event_type == "ball_reappeared":
                        print(
                            f"[REAPPEAR] Ball {event.get('ball')} reappeared (was occluded)"
                        )
                    elif event_type == "cueball_scratch":
                        print(f"[SCRATCH] Cueball scratched at frame {frame_idx}")

                    # Check if game ended
                    if event.get("game_end", False):
                        print(f"[GAME] Game ended - Winner: {event.get('winner')}")
                        break

            except Exception as e:
                print(f"[ERROR] Ball tracking: {e}")
                import traceback

                traceback.print_exc()

            # Check for movement timeout
            timeout_event = game_manager.check_movement_timeout(current_frame=frame_idx)
            if timeout_event:
                await manager.broadcast(timeout_event)

            # Broadcast frame detection results
            await manager.broadcast(
                {
                    "event": "frame_update",
                    "frame_idx": frame_idx,
                    "balls": convert_numpy_types(balls),
                    "game_state": convert_numpy_types(game_manager.get_game_state()),
                }
            )

            # Build annotated frame for streaming (match Python visualize_video style)
            try:
                display = frame.copy()

                # Separate cueball and other balls
                cueball = None
                other_balls = []
                for b in balls:
                    if b["name"] == "cueball":
                        cueball = b
                    else:
                        other_balls.append(b)

                # Draw all balls with circles and labels
                for b in balls:
                    cx, cy, r = int(b["x"]), int(b["y"]), int(b["r"])

                    # Color: green for cueball, white for others
                    if b["name"] == "cueball":
                        color = (0, 255, 0)  # Green for cueball
                    else:
                        color = (255, 255, 255)  # White for other balls

                    # Draw circle around ball
                    cv2.circle(display, (cx, cy), r, color, 2)
                    # Draw center dot
                    cv2.circle(display, (cx, cy), 3, color, -1)
                    # Draw radius line (from center to edge)
                    cv2.line(display, (cx, cy), (cx + r, cy), color, 1)

                    # Draw ball name with black outline for visibility
                    label = f"{b['name']}"
                    label_pos = (max(cx - r, 0), max(cy - r - 10, 0))
                    cv2.putText(
                        display,
                        label,
                        label_pos,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 0),
                        3,
                        cv2.LINE_AA,
                    )
                    cv2.putText(
                        display,
                        label,
                        label_pos,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        1,
                        cv2.LINE_AA,
                    )

                # Draw distance lines from cueball to all other balls
                if cueball is not None:
                    for ball in other_balls:
                        # Draw line from cueball to ball
                        cv2.line(
                            display,
                            (int(cueball["x"]), int(cueball["y"])),
                            (int(ball["x"]), int(ball["y"])),
                            (128, 128, 128),  # Gray color
                            1,
                        )
                        # Calculate and display distance
                        dist = np.sqrt(
                            (cueball["x"] - ball["x"]) ** 2
                            + (cueball["y"] - ball["y"]) ** 2
                        )
                        mid_x = int((cueball["x"] + ball["x"]) / 2)
                        mid_y = int((cueball["y"] + ball["y"]) / 2)
                        cv2.putText(
                            display,
                            f"{dist:.1f}",
                            (mid_x, mid_y),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.4,
                            (128, 128, 128),
                            1,
                        )

                # Visualize recent collisions (keep visible for ~30 frames)
                # Clean up old collisions
                recent_collisions[:] = [
                    c for c in recent_collisions if frame_idx - c["frame_idx"] <= 30
                ]

                for coll_data in recent_collisions:
                    cue = coll_data["cueball"]
                    ball = coll_data["ball"]

                    # Highlight the collided ball with thick red circle
                    ball_cx, ball_cy, ball_r = (
                        int(ball["x"]),
                        int(ball["y"]),
                        int(ball["r"]),
                    )
                    cv2.circle(display, (ball_cx, ball_cy), ball_r, (0, 0, 255), 3)

                    # Draw thick yellow line from cueball to collided ball
                    cv2.line(
                        display,
                        (int(cue["x"]), int(cue["y"])),
                        (int(ball["x"]), int(ball["y"])),
                        (0, 255, 255),  # Yellow
                        3,
                    )

                    # Display collision text
                    cv2.putText(
                        display,
                        f"Collision with {coll_data['ball_name']}",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 255),
                        2,
                    )

                # Encode JPEG
                ok, buf = cv2.imencode(".jpg", display)
                if ok:
                    jpg_bytes = buf.tobytes()
                    # Store latest frame (thread-safe with lock)
                    async with frame_lock:
                        global latest_frame
                        latest_frame = jpg_bytes
            except Exception as e:
                print(f"[Stream] Annotate frame error: {e}")

            prev_frame_data = current_frame_data

            # Rate limiting
            await asyncio.sleep(frame_delay * 0.5)  # Process at 2x speed for demo

        cap.release()

        # Notify detection stopped
        await manager.broadcast(
            {
                "event": "detection_stop",
                "message": "AI detection stopped",
                "game_state": convert_numpy_types(game_manager.get_game_state()),
            }
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        await manager.broadcast(
            {"event": "error", "message": f"Detection error: {str(e)}"}
        )

    finally:
        print("[Detection] Task completed")


# ============= API Endpoints =============


@app.get("/")
async def root():
    return {
        "app": "SmartBilliardTracker AI Referee",
        "version": "2.0.0",
        "status": "running",
    }


@app.post("/api/game/upload")
async def upload_game_video(file: UploadFile = File(...)):
    """
    Upload a video file for Live Game mode and return its server path
    """
    # Validate file type
    filename = file.filename or "video.mp4"
    if not filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(
            status_code=400,
            detail="Invalid video format. Supported: mp4, avi, mov, mkv",
        )

    # Create unique filename with timestamp to avoid clashes
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_name = f"{ts}_{Path(filename).name}"
    video_path = UPLOAD_DIR / safe_name

    try:
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    return {"video_path": str(video_path)}


@app.post("/api/game/start")
async def start_game(request: GameStartRequest, background_tasks: BackgroundTasks):
    """
    Start a new game with player setup
    """
    global active_detection_task, detection_stop_event

    # Stop existing game if any
    if active_detection_task and not active_detection_task.done():
        print("[Game] Stopping existing detection task...")
        detection_stop_event.set()

        # Wait for task to complete with timeout
        try:
            await asyncio.wait_for(active_detection_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("[Game] Detection task timeout, cancelling...")
            active_detection_task.cancel()
            try:
                await active_detection_task
            except asyncio.CancelledError:
                pass
        except Exception as e:
            print(f"[Game] Error stopping task: {e}")

        active_detection_task = None

    # Reset detection event
    detection_stop_event.clear()

    # Clear latest frame
    async with frame_lock:
        global latest_frame
        latest_frame = b""

    # Reset game manager and ball tracker
    game_manager.reset_game()
    ball_tracker.reset()

    # Initialize new game
    game_state = game_manager.start_game(
        request.player1_name, request.player2_name, request.starting_player
    )

    # Determine video source
    if request.use_camera:
        video_source = 0  # Webcam
    elif request.video_path:
        video_source = request.video_path
    else:
        raise HTTPException(
            status_code=400, detail="Must specify video_path or use_camera"
        )

    # Start detection task
    active_detection_task = asyncio.create_task(real_time_detection_task(video_source))

    return {
        "status": "started",
        "game_state": game_state,
        "message": f"Game started: {request.player1_name} vs {request.player2_name}",
    }


@app.post("/api/game/stop")
async def stop_game(request: GameStopRequest):
    """
    Stop the current game
    """
    global detection_stop_event

    detection_stop_event.set()

    return {
        "status": "stopped",
        "reason": request.reason,
        "game_state": convert_numpy_types(game_manager.get_game_state()),
    }


@app.post("/api/game/restart")
async def restart_game():
    """
    Reset game to initial state
    """
    global detection_stop_event

    detection_stop_event.set()
    await asyncio.sleep(0.5)

    game_manager.reset_game()

    return {"status": "reset", "message": "Game reset to initial state"}


@app.get("/api/game/state", response_model=GameStateResponse)
async def get_game_state():
    """
    Get current game state
    """
    return game_manager.get_game_state()


@app.get("/api/game/history")
async def get_match_history():
    """
    Get match history
    """
    history_file = DATA_DIR / "matches.json"

    if not history_file.exists():
        return {"matches": []}

    try:
        with open(history_file, "r") as f:
            history = json.load(f)
        return {"matches": history}
    except:
        return {"matches": []}


# ============= WebSocket Endpoint =============


@app.websocket("/ws/game")
async def websocket_game(websocket: WebSocket):
    """
    WebSocket for real-time game updates
    """
    await manager.connect(websocket)

    try:
        # Send current game state on connect
        await websocket.send_json(
            {
                "event": "connected",
                "game_state": convert_numpy_types(game_manager.get_game_state()),
            }
        )

        while True:
            # Keep connection alive and receive client messages
            data = await websocket.receive_text()

            # Handle client messages (heartbeat, etc.)
            try:
                message = json.loads(data)
                if message.get("type") == "heartbeat":
                    await websocket.send_json({"type": "heartbeat_ack"})
            except:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        manager.disconnect(websocket)


# ============= MJPEG Stream Endpoint =============


@app.get("/api/game/stream")
async def stream_video():
    """
    Stream the latest annotated frames as MJPEG for smooth live visualization.
    """
    boundary = "frame"

    def _make_placeholder_jpeg(text: str = "Waiting...") -> bytes:
        """Create a small placeholder JPEG to keep the stream alive."""
        try:
            img = np.zeros((360, 640, 3), dtype=np.uint8)
            cv2.putText(
                img,
                text,
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
            ok, buf = cv2.imencode(".jpg", img)
            if ok:
                return buf.tobytes()
        except Exception:
            pass
        return b""  # Fallback

    async def frame_generator():
        placeholder = _make_placeholder_jpeg("No frames yet - stream alive")
        last_sent_frame = None

        while True:
            # Get the latest frame (shared across all stream clients)
            async with frame_lock:
                current_frame = latest_frame if latest_frame else placeholder

            # Only send if frame has changed (reduces bandwidth for slow updates)
            if current_frame != last_sent_frame:
                last_sent_frame = current_frame
                frame = current_frame
            else:
                # Same frame, wait a bit before checking again
                await asyncio.sleep(0.033)  # ~30fps check rate
                continue

            yield (
                b"--"
                + boundary.encode()
                + b"\r\n"
                + b"Content-Type: image/jpeg\r\n"
                + f"Content-Length: {len(frame)}\r\n\r\n".encode()
                + frame
                + b"\r\n"
            )

            # Small delay to prevent excessive CPU usage
            await asyncio.sleep(0.001)

    return StreamingResponse(
        frame_generator(),
        media_type=f"multipart/x-mixed-replace; boundary={boundary}",
        headers={
            # Prevent intermediaries/browsers from caching the first frame which can cause frozen images
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            # Hint to proxies like NGINX to avoid buffering the stream
            "X-Accel-Buffering": "no",
            # Keep the TCP connection alive
            "Connection": "keep-alive",
        },
    )


@app.get("/api/game/stream/test")
async def stream_test_video():
    """
    Synthetic MJPEG stream for diagnostics. Does not require a running game.
    Generates simple frames with a timestamp to validate client rendering and proxies.
    """
    boundary = "frame"

    async def generator():
        t = 0
        while True:
            # Create a simple moving gradient with timestamp
            h, w = 360, 640
            img = np.zeros((h, w, 3), dtype=np.uint8)
            color = (int((np.sin(t) * 0.5 + 0.5) * 255), 128, 255)
            img[:] = color
            cv2.putText(
                img,
                datetime.now().strftime("%H:%M:%S"),
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 0, 0),
                3,
                cv2.LINE_AA,
            )
            cv2.putText(
                img,
                "MJPEG Test",
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            ok, buf = cv2.imencode(".jpg", img)
            frame = buf.tobytes() if ok else b""
            t += 0.1

            yield (
                b"--"
                + boundary.encode()
                + b"\r\n"
                + b"Content-Type: image/jpeg\r\n"
                + f"Content-Length: {len(frame)}\r\n\r\n".encode()
                + frame
                + b"\r\n"
            )

            await asyncio.sleep(0.1)

    return StreamingResponse(
        generator(),
        media_type=f"multipart/x-mixed-replace; boundary={boundary}",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ============= Health Check =============


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "game_state": game_manager.state.value,
        "active_connections": len(manager.active_connections),
    }


if __name__ == "__main__":
    # Run directly for local development. Note: reload requires import string; using app object, disable reload.
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
