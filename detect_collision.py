import os
import cv2
import csv
import numpy as np
from utils import distance, draw_circle, get_moving_balls
import argparse

# Default values được dùng cho cả detect_collision và argparse
DEFAULT_MOVE_THRESH = 0.3
DEFAULT_CONTACT_MARGIN = 10.0

def load_detections(csv_path):

    frames = {}
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            frame_idx = int(row["frame"])
            if frame_idx not in frames:
                frames[frame_idx] = []
            ball = {
                "name": row["name"],
                "x": float(row["x"]),
                "y": float(row["y"]),
                "r": float(row["r"]),
                "conf": float(row["conf"]) if "conf" in row and row["conf"] else 1.0
            }
            frames[frame_idx].append(ball)

    frames_data = [{"frame_idx": idx, "balls": balls} for idx, balls in sorted(frames.items())]
    return frames_data


def merge_sequential_collisions(collisions, max_gap=2):
    """
    Gộp các va chạm liên tiếp với cùng một ball thành một va chạm duy nhất.
    Loại bỏ duplicates có cùng (frame_idx, ball_name).
    
    Args:
        collisions: list các collision dicts
        max_gap: số frame tối đa được chấp nhận giữa các va chạm liên tiếp (mặc định 2)
    
    Returns:
        list các va chạm đã được gộp
    """
    if not collisions:
        return collisions
    
    # Loại bỏ duplicates (cùng frame_idx và ball name)
    seen = set()
    unique_collisions = []
    for c in collisions:
        key = (c["frame_idx"], c["ball"]["name"])
        if key not in seen:
            seen.add(key)
            unique_collisions.append(c)
    
    # Sắp xếp theo frame_idx và ball name
    sorted_collisions = sorted(unique_collisions, key=lambda x: (x["frame_idx"], x["ball"]["name"]))
    
    merged = []
    current_group = [sorted_collisions[0]]
    
    for i in range(1, len(sorted_collisions)):
        curr = sorted_collisions[i]
        prev = sorted_collisions[i-1]
        
        # Kiểm tra nếu cùng ball và frame liên tiếp (hoặc cách nhau <= max_gap)
        same_ball = curr["ball"]["name"] == prev["ball"]["name"]
        frame_gap = curr["frame_idx"] - prev["frame_idx"]
        
        if same_ball and frame_gap <= max_gap:
            current_group.append(curr)
        else:
            # Kết thúc group hiện tại, lấy frame đầu tiên
            merged.append(current_group[0])
            current_group = [curr]
    
    # Thêm group cuối cùng
    if current_group:
        merged.append(current_group[0])
    
    return merged


# =============================
# DETECT COLLISIONS
# =============================
def detect_collision(frames_data, move_thresh=DEFAULT_MOVE_THRESH, cue_ball_name="cueball", contact_margin=DEFAULT_CONTACT_MARGIN):
    """
    Phát hiện va chạm giữa cueball và các bi khác dựa trên 3 điều kiện:
    1. Cueball đã từng gần ball (min distance trong N-1 và N <= 100 pixels).
    2. Khoảng cách giữa cueball ở frame N và ball ở frame N-1 <= tổng bán kính ở frame N và N-1 + contact_margin.
    3. Bi đó di chuyển từ N-1 đến N với ngưỡng move_thresh (mặc định 0.3 = 30% bán kính).
    """
    collisions = []
    prev_frame = None
    for i, frame_data in enumerate(frames_data):
        frame_idx = frame_data["frame_idx"]
        balls = frame_data["balls"]
        if prev_frame is None:
            prev_frame = frame_data
            continue
        cueball = next((b for b in balls if b["name"] == cue_ball_name), None)
        prev_balls = prev_frame["balls"]
        prev_cueball = next((b for b in prev_balls if b["name"] == cue_ball_name), None)
        if cueball is None or prev_cueball is None:
            prev_frame = frame_data
            continue
        # --- Kiểm tra từng bi vật thể ---
        # Lấy danh sách các ball ở frame trước để kiểm tra cả ball mất detect
        for prev_b in prev_balls:
            if prev_b["name"] == cue_ball_name:
                continue
            
            # Kiểm tra xem ball có tồn tại ở frame hiện tại không
            b = next((ball for ball in balls if ball["name"] == prev_b["name"]), None)
            
            # Điều kiện 1: cueball đã từng gần ball ở N-1 hoặc N
            dist_prev = distance(prev_cueball, prev_b)
            if b is not None:
                dist_now = distance(cueball, b)
                min_dist = min(dist_prev, dist_now)
            else:
                # Ball mất detect, chỉ có dist_prev
                dist_now = None
                min_dist = dist_prev
            
            # Nếu khoảng cách nhỏ nhất vẫn quá xa thì bỏ qua
            if min_dist > 100:  # heuristic threshold
                continue
            
            # Điều kiện 2: cueball (N) gần ball (N-1) <= tổng bán kính + margin
            dist_cue_now_ball_prev = distance(cueball, prev_b)
            radius_sum = cueball["r"] + prev_b["r"]
            if dist_cue_now_ball_prev > (radius_sum + contact_margin):
                continue
            
            # Điều kiện 3: ball bị chạm phải di chuyển từ N-1 đến N
            ball_moved = get_moving_balls(frames_data, i, prev_b["name"], move_thresh=move_thresh)
            if not ball_moved:
                continue

            # Ghi nhận va chạm
            # Nếu ball mất detect, frame va chạm là frame N-1 (prev_frame)
            # Nếu ball còn detect, frame va chạm là frame N (frame hiện tại)
            if b is not None:
                # Ball còn detect, va chạm ở frame N
                collisions.append({
                    "frame_idx": frame_idx,
                    "cueball": cueball,
                    "ball": b
                })
            else:
                # Ball mất detect, va chạm ở frame N-1 (cuối cùng có ball)
                collisions.append({
                    "frame_idx": prev_frame["frame_idx"],
                    "cueball": prev_cueball,
                    "ball": prev_b
                })
        prev_frame = frame_data
    
    # Gộp các va chạm liên tiếp với cùng một ball
    collisions = merge_sequential_collisions(collisions, max_gap=2)
    
    return collisions


# =============================
# VISUALIZE COLLISIONS
# =============================
def visualize_collisions(video_path, collisions, output_dir):
    cap = cv2.VideoCapture(video_path)
    frame_idx = 0
    out_dir = os.path.join(output_dir, "frames")
    os.makedirs(out_dir, exist_ok=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_collisions = [c for c in collisions if c["frame_idx"] == frame_idx]
        for c in frame_collisions:
            cue = c["cueball"]
            ball = c["ball"]

            draw_circle(frame, cue, (0, 255, 0))  # cueball - xanh lá
            draw_circle(frame, ball, (0, 0, 255))  # ball - đỏ
            cv2.line(frame, (int(cue["x"]), int(cue["y"])),
                     (int(ball["x"]), int(ball["y"])), (255, 255, 0), 2)
            cv2.putText(frame, f"Collision: {ball['name']}",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        cv2.imwrite(os.path.join(out_dir, f"{frame_idx:04d}.jpg"), frame)
        frame_idx += 1

    cap.release()


def visualize_video(video_path, frames_data, collisions, output_video_path):
    """
    Tạo video output với visual: vẽ đường tròn và bán kính cho mỗi bi, 
    vẽ đường khoảng cách từ cueball đến các ball khác, và đánh dấu các va chạm.
    
    Args:
        video_path: Đường dẫn đến video input
        frames_data: List các dict với format [{"frame_idx": int, "balls": [dict, ...]}, ...]
        collisions: List các collision dict với format [{"cueball": dict, "ball": dict, "frame_id": int}, ...]
        output_video_path: Đường dẫn đến video output
    """
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    
   
    collisions_by_frame = {}
    for coll in collisions:
        frame_id = coll["frame_id"]
        if frame_id not in collisions_by_frame:
            collisions_by_frame[frame_id] = []
        collisions_by_frame[frame_id].append(coll)
    
    # Tạo dict để tra cứu frames_data theo frame_idx
    frames_dict = {fd["frame_idx"]: fd for fd in frames_data}
    
    frame_idx = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[INFO] Creating output video: {output_video_path}")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_idx += 1
        frame_draw = frame.copy()
        
        # Vẽ các bi từ frames_data
        cueball = None
        other_balls = []
        if frame_idx in frames_dict:
            balls = frames_dict[frame_idx]["balls"]
            for ball in balls:
                # Phân loại cueball và các ball khác
                if ball["name"] == "cueball":
                    cueball = ball
                else:
                    other_balls.append(ball)
                
                # Màu cho cueball và các bi khác
                if ball["name"] == "cueball":
                    color = (0, 255, 0)  # Xanh lá cho cueball
                else:
                    color = (255, 255, 255)  # Trắng cho các bi khác
                
                # Vẽ đường tròn quanh bi
                center = (int(ball["x"]), int(ball["y"]))
                radius = int(ball["r"])
                cv2.circle(frame_draw, center, radius, color, 2)
                # Vẽ tâm bi
                cv2.circle(frame_draw, center, 3, color, -1)
                # Vẽ bán kính (đường từ tâm đến viền)
                cv2.line(frame_draw, center, 
                        (int(ball["x"] + radius), int(ball["y"])), 
                        color, 1)
                # Vẽ tên bi
                cv2.putText(frame_draw, ball["name"], 
                           (int(ball["x"]) - 20, int(ball["y"]) - int(ball["r"]) - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Vẽ đường khoảng cách từ cueball đến các ball khác
        if cueball is not None:
            for ball in other_balls:
                # Vẽ đường nối từ cueball đến ball khác
                cv2.line(frame_draw,
                        (int(cueball["x"]), int(cueball["y"])),
                        (int(ball["x"]), int(ball["y"])),
                        (128, 128, 128), 1)  # Màu xám cho đường khoảng cách
                # Vẽ khoảng cách dưới dạng text
                dist = distance(cueball, ball)
                mid_x = int((cueball["x"] + ball["x"]) / 2)
                mid_y = int((cueball["y"] + ball["y"]) / 2)
                cv2.putText(frame_draw, f"{dist:.1f}",
                           (mid_x, mid_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
        
        # Vẽ các va chạm tại frame này
        if frame_idx in collisions_by_frame:
            frame_collisions = collisions_by_frame[frame_idx]
            for coll in frame_collisions:
                cue = coll["cueball"]
                ball = coll["ball"]
                
                # Highlight ball bị va chạm với màu đỏ
                draw_circle(frame_draw, ball, (0, 0, 255), thickness=3)
                
                # Vẽ lại đường nối giữa cueball và ball va chạm với màu vàng nổi bật
                cv2.line(frame_draw, 
                         (int(cue["x"]), int(cue["y"])),
                         (int(ball["x"]), int(ball["y"])), 
                         (0, 255, 255), 3)  # Màu vàng đậm cho đường va chạm
                
                # Hiển thị thông tin va chạm
                cv2.putText(frame_draw, f"Collision with {ball['name']}",
                           (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        
        out.write(frame_draw)
        
        if frame_idx % 50 == 0:
            print(f"[INFO] Processing frame {frame_idx}/{total_frames}")
    
    cap.release()
    out.release()
    print(f"[DONE] Output video saved: {output_video_path}")


# =============================
# LOG COLLISIONS
# =============================
def log_collisions(collisions, log_path):
    if not collisions:
        return
    with open(log_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame_idx", "cue_x", "cue_y", "ball_name", "ball_x", "ball_y"])
        for c in collisions:
            writer.writerow([
                c["frame_idx"],
                c["cueball"]["x"],
                c["cueball"]["y"],
                c["ball"]["name"],
                c["ball"]["x"],
                c["ball"]["y"],
            ])
    print(f"[INFO] Collision log saved: {log_path}")


# =============================
# GET COLLISIONS (Main function to be used by other modules)
# =============================
def get_collisions_from_data(frames_data, cue_ball_name="cueball", move_thresh=DEFAULT_MOVE_THRESH, contact_margin=DEFAULT_CONTACT_MARGIN):
    """
    Hàm chính để lấy danh sách các va chạm từ frames_data trong memory.
    
    Args:
        frames_data: List các dict với format [{"frame_idx": int, "balls": [dict, ...]}, ...]
        cue_ball_name: Tên của cue ball (default: "cueball")
        move_thresh: Ngưỡng di chuyển (default: 0.3)
        contact_margin: Margin cho contact check (default: 10.0)
    
    Returns:
        list: Danh sách các collision dict, mỗi dict chứa:
            - "cueball": dict với thông tin cueball {"name", "x", "y", "r", "conf"}
            - "ball": dict với thông tin ball bị va chạm {"name", "x", "y", "r", "conf"}
            - "frame_id": số frame xảy ra va chạm
    """
    print(f"[INFO] Processing {len(frames_data)} frames for collision detection...")

    print("[INFO] Detecting collisions...")
    collisions = detect_collision(
        frames_data,
        move_thresh=move_thresh,
        cue_ball_name=cue_ball_name,
        contact_margin=contact_margin,
    )
    print(f"[INFO] Found {len(collisions)} collisions")
    
    # Format lại collisions để có frame_id thay vì frame_idx
    formatted_collisions = []
    for coll in collisions:
        formatted_collisions.append({
            "cueball": coll["cueball"],
            "ball": coll["ball"],
            "frame_id": coll["frame_idx"]
        })
    
    return formatted_collisions


def get_collisions(csv_path, cue_ball_name="cueball", move_thresh=DEFAULT_MOVE_THRESH, contact_margin=DEFAULT_CONTACT_MARGIN):
    """
    Hàm để lấy danh sách các va chạm từ CSV detections (giữ lại để tương thích).
    
    Args:
        csv_path: Đường dẫn đến file CSV chứa detections
        cue_ball_name: Tên của cue ball (default: "cueball")
        move_thresh: Ngưỡng di chuyển (default: 0.3)
        contact_margin: Margin cho contact check (default: 10.0)
    
    Returns:
        list: Danh sách các collision dict, mỗi dict chứa:
            - "cueball": dict với thông tin cueball {"name", "x", "y", "r", "conf"}
            - "ball": dict với thông tin ball bị va chạm {"name", "x", "y", "r", "conf"}
            - "frame_id": số frame xảy ra va chạm
    """
    print("[INFO] Loading detections from CSV...")
    frames_data = load_detections(csv_path)
    print(f"[INFO] Loaded {len(frames_data)} frames")
    
    return get_collisions_from_data(frames_data, cue_ball_name, move_thresh, contact_margin)


# =============================
# MAIN
# =============================
def main():
    parser = argparse.ArgumentParser(description="Detect collision from YOLO CSV output and video.")
    parser.add_argument('--video', required=True, help='Input video path')
    parser.add_argument('--csv', required=True, help='CSV path with detections')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    parser.add_argument('--cue-ball-name', default='cueball', help='Cue ball class name (default: cueball)')
    parser.add_argument('--enable-visual', action='store_true', help='Enable collision visualization')
    parser.add_argument('--enable-log', action='store_true', help='Enable collision log (CSV)')
    parser.add_argument('--move-thresh', type=float, default=DEFAULT_MOVE_THRESH, help=f'Movement threshold as ratio of radius (default: {DEFAULT_MOVE_THRESH} = {DEFAULT_MOVE_THRESH*100:.0f}%%)')
    parser.add_argument('--contact-margin', type=float, default=DEFAULT_CONTACT_MARGIN, help=f'Extra pixels allowed for contact check (default: {DEFAULT_CONTACT_MARGIN})')
    args = parser.parse_args()

    video_path = args.video
    csv_path = args.csv
    output_dir = args.output_dir
    cue_ball_name = args.cue_ball_name
    enable_visual = args.enable_visual
    enable_log = args.enable_log
    move_thresh = args.move_thresh
    contact_margin = args.contact_margin

    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, "collision_log.csv")

    # Sử dụng hàm get_collisions và convert lại format cho visualize/log
    collisions_raw = get_collisions(csv_path, cue_ball_name, move_thresh, contact_margin)
    
    # Convert lại về format cũ cho visualize và log
    collisions = [{"cueball": c["cueball"], "ball": c["ball"], "frame_idx": c["frame_id"]} 
                  for c in collisions_raw]

    if enable_log:
        log_collisions(collisions, log_path)
    if enable_visual:
        visualize_collisions(video_path, collisions, output_dir)

if __name__ == "__main__":
    main()
