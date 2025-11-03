from ultralytics import YOLO
import cv2
import os
import argparse
import csv
from pathlib import Path
import numpy as np
from utils import draw_circle


def compute_iou(det1, det2):

    dist = np.sqrt((det1["x"] - det2["x"]) ** 2 + (det1["y"] - det2["y"]) ** 2)
 
    r1, r2 = det1["r"], det2["r"]
    
    if dist >= r1 + r2:
        intersection = 0.0
    elif dist <= abs(r1 - r2):
        intersection = np.pi * min(r1, r2) ** 2
    else:
        d = dist
        r1_sq, r2_sq = r1 ** 2, r2 ** 2
        
        cos_theta1 = (d * d + r1_sq - r2_sq) / (2 * d * r1)
        cos_theta2 = (d * d + r2_sq - r1_sq) / (2 * d * r2)
        
        theta1 = np.arccos(np.clip(cos_theta1, -1.0, 1.0))
        theta2 = np.arccos(np.clip(cos_theta2, -1.0, 1.0))
        
        sector1 = r1_sq * theta1
        sector2 = r2_sq * theta2
        
        triangle1 = 0.5 * r1_sq * np.sin(2 * theta1)
        triangle2 = 0.5 * r2_sq * np.sin(2 * theta2)
        
   
        intersection = sector1 + sector2 - triangle1 - triangle2
    
    union = np.pi * r1 ** 2 + np.pi * r2 ** 2 - intersection
    
    return intersection / union if union > 0 else 0.0


def merge_overlapping_detections(detections, iou_threshold=0.7):

    if len(detections) <= 1:
        return detections
    
    sorted_dets = sorted(detections, key=lambda d: d["conf"], reverse=True)
    
    kept = []
    while sorted_dets:
        current = sorted_dets.pop(0)
        kept.append(current)
        
        sorted_dets = [det for det in sorted_dets if compute_iou(current, det) < iou_threshold]
    
    return kept


def detect_video(model_path, video_path, conf_threshold=0.1, merge_iou_threshold=0.7):
    """
    Detect objects on each frame of video, keep only best per class, và trả về frames_data trong memory.
    
    Uses tracking to merge detections: if a detection in current frame has >70% IoU with a detection 
    from previous frame, it's considered the same object and the old detection is kept.
    
    Args:
        model_path: Đường dẫn đến model YOLO
        video_path: Đường dẫn đến video
        conf_threshold: Ngưỡng confidence
        merge_iou_threshold: Ngưỡng IoU để merge detections
    
    Returns:
        list: Danh sách các dict với format [{"frame_idx": int, "balls": [dict, ...]}, ...]
    """
    model = YOLO(model_path)
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    print(f"[INFO] Processing video {video_path} ({total_frames} frames, {fps} fps)")
    
    # Lưu trữ các detections của frame trước
    prev_frame_detections = []
    frames_data = []
    
    frame_id = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_id += 1
        try:
            results = model.predict(source=frame, conf=conf_threshold, verbose=False)[0]
            boxes = results.boxes.xyxy.cpu().numpy() if results.boxes.xyxy.numel() > 0 else []
            confs = results.boxes.conf.cpu().numpy() if results.boxes.conf.numel() > 0 else []
            classes = results.boxes.cls.cpu().numpy().astype(int) if results.boxes.cls.numel() > 0 else []
            names = [model.names[c] for c in classes] if len(classes) else []
            detections = []
            for (box, conf, name) in zip(boxes, confs, names):
                if conf < conf_threshold:
                    continue
                x1, y1, x2, y2 = box
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                r = max((x2 - x1), (y2 - y1)) / 2
                detections.append({
                    "name": name,
                    "x": round(cx, 2),
                    "y": round(cy, 2),
                    "r": round(r, 2),
                    "conf": conf
                })
            
            # Bước 1: Gộp các detections trùng lặp trong cùng frame (tại cùng vị trí hoặc gần nhau)
            detections_merged = merge_overlapping_detections(detections, iou_threshold=merge_iou_threshold)
            
            # Bước 2: Tracking với frame trước - điều chỉnh label detection mới theo label frame trước
            if prev_frame_detections:
                for det in detections_merged:
                    best_iou = 0
                    best_prev_det = None
                    for prev_det in prev_frame_detections:
                        iou = compute_iou(det, prev_det)
                        if iou > best_iou:
                            best_iou = iou
                            best_prev_det = prev_det
                    
                    # Nếu IoU > threshold, đổi label thành label frame trước
                    if best_iou > merge_iou_threshold:
                        det["name"] = best_prev_det["name"]
            
            # Bước 3: Giữ lại mỗi loại ball có confidence cao nhất
            best_per_class = {}
            for det in detections_merged:
                cls = det["name"]
                if cls not in best_per_class or det["conf"] > best_per_class[cls]["conf"]:
                    best_per_class[cls] = det
            detections_filtered = list(best_per_class.values())
            
            prev_frame_detections = [det.copy() for det in detections_filtered]
            
            # Lưu vào frames_data
            frames_data.append({
                "frame_idx": frame_id,
                "balls": [det.copy() for det in detections_filtered]
            })
            
            if frame_id % 50 == 0:
                print(f"[INFO] Frame {frame_id}/{total_frames}: {len(detections_filtered)} balls kept after filtering.")
        except Exception as e:
            print(f"[ERROR] Frame {frame_id}: {e}")
    cap.release()
    print(f"[DONE] Detected {len(frames_data)} frames with detections.")
    return frames_data


def detect_video_and_log(model_path, video_path, output_dir, csv_path, conf_threshold=0.1, merge_iou_threshold=0.7):
    """
    Detect objects on each frame of video, keep only best per class, log to CSV, and save frames with box to output_dir.
    (Hàm này giữ lại để tương thích với code cũ)
    """
    model = YOLO(model_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[INFO] Processing video {video_path} ({total_frames} frames)")
    
    # Lưu trữ các detections của frame trước
    prev_frame_detections = []
    
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["frame", "name", "x", "y", "r"])
        writer.writeheader()
        frame_id = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_id += 1
            try:
                results = model.predict(source=frame, conf=conf_threshold, verbose=False)[0]
                boxes = results.boxes.xyxy.cpu().numpy() if results.boxes.xyxy.numel() > 0 else []
                confs = results.boxes.conf.cpu().numpy() if results.boxes.conf.numel() > 0 else []
                classes = results.boxes.cls.cpu().numpy().astype(int) if results.boxes.cls.numel() > 0 else []
                names = [model.names[c] for c in classes] if len(classes) else []
                detections = []
                for (box, conf, name) in zip(boxes, confs, names):
                    if conf < conf_threshold:
                        continue
                    x1, y1, x2, y2 = box
                    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                    r = max((x2 - x1), (y2 - y1)) / 2
                    detections.append({
                        "name": name,
                        "x": round(cx, 2),
                        "y": round(cy, 2),
                        "r": round(r, 2),
                        "conf": conf
                    })
                
                # Bước 1: Gộp các detections trùng lặp trong cùng frame (tại cùng vị trí hoặc gần nhau)
                detections_merged = merge_overlapping_detections(detections, iou_threshold=merge_iou_threshold)
                
                # Bước 2: Tracking với frame trước - điều chỉnh label detection mới theo label frame trước
                if prev_frame_detections:
                    for det in detections_merged:
                        best_iou = 0
                        best_prev_det = None
                        for prev_det in prev_frame_detections:
                            iou = compute_iou(det, prev_det)
                            if iou > best_iou:
                                best_iou = iou
                                best_prev_det = prev_det
                        
                        # Nếu IoU > threshold, đổi label thành label frame trước
                        if best_iou > merge_iou_threshold:
                            det["name"] = best_prev_det["name"]
                
                # Bước 3: Giữ lại mỗi loại ball có confidence cao nhất
                best_per_class = {}
                for det in detections_merged:
                    cls = det["name"]
                    if cls not in best_per_class or det["conf"] > best_per_class[cls]["conf"]:
                        best_per_class[cls] = det
                detections_filtered = list(best_per_class.values())
                
                prev_frame_detections = [det.copy() for det in detections_filtered]
                
                for det in detections_filtered:
                    writer.writerow({
                        "frame": frame_id,
                        "name": det["name"],
                        "x": det["x"],
                        "y": det["y"],
                        "r": det["r"]
                    })

                if len(detections_filtered) > 0:
                    frame_with_boxes = frame.copy()
                    for det in detections_filtered:
                        draw_circle(frame_with_boxes, det, (0, 255, 0))
                        cv2.putText(frame_with_boxes, det["name"], 
                                   (int(det["x"]) - 20, int(det["y"]) - int(det["r"]) - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    out_path = output_dir / f"{frame_id:04d}.jpg"
                    cv2.imwrite(str(out_path), frame_with_boxes)
                if frame_id % 50 == 0:
                    print(f"[INFO] Frame {frame_id}/{total_frames}: {len(detections_filtered)} balls kept after filtering.")
            except Exception as e:
                print(f"[ERROR] Frame {frame_id}: {e}")
    cap.release()
    print(f"[DONE] Detections saved to: {csv_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect balls from video using YOLOv8 model and export to CSV + frames")
    parser.add_argument('--model', default="models/yolov8n-ball-v.1.0.0.pt", help="Path to YOLOv8 model weights")
    parser.add_argument('--video', required=True, help="Path to input video")
    parser.add_argument('--output-dir', required=True, help="Folder to save detected frames")
    parser.add_argument('--csv', required=True, help="Path to output CSV file")
    parser.add_argument('--conf', type=float, default=0.1, help="Confidence threshold (default: 0.1)")
    parser.add_argument('--merge-iou', type=float, default=0.7, help="IoU threshold for merging overlapping detections (default: 0.7)")
    args = parser.parse_args()
    detect_video_and_log(args.model, args.video, args.output_dir, args.csv, args.conf, args.merge_iou)
