import cv2
import threading
import time 
import queue
import csv
import time

"""
 -----Các hàng đợi------
frame_queue = queue.Queue(maxsize=50)
detect_queue = queue.Queue(maxsize=50)
rel_frame_queue = queue.Queue(maxsize=50)
"""

# --------------------------
# Capture thread
def capture_thread(video_path, frame_queue):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"##--Cannot open video: {video_path}")
        return

    print("##--Start capturing video...")
    frame_id = 0
    while True:
        if frame_queue.full():
            time.sleep(1)
            continue
            
        ret, frame = cap.read()
        if not ret:
            break
        frame_queue.put((frame_id, frame))
        frame_id += 1

    cap.release()
    frame_queue.put(None)
    print("Capture done.")

# --------------------------
# Detect thread ====> detector.py
#------------------------


#-----------------------------------------
# Tracker thread
def tracker_thread(detect_queue, detect_queue_new, tracker):
    while True:
        try:
            data = detect_queue.get(timeout=2)
        except queue.Empty:
            # Không có dữ liệu trong queue, có thể break hoặc continue
            continue
        if data is None:
            break
        
        if not (isinstance(data, tuple) and len(data) == 2):
                    print(f"Skipping unexpected item in queue: {data}")
                    continue

        frame_id, detections = data
        detections = tracker.update(detections)
        detect_queue_new.put((frame_id,detections))
    detect_queue_new.put(None)
    

    



def postprocess_thread(detect_queue, tracker, physics, events, law):
    while True:
        item = detect_queue.get()
        if item is None:
            break
        frame_id, frame, detections = item
        tracked = tracker.update(detections)
        physics_info = physics.analyze(tracked)
        event = events.generate(physics_info)
        law.evaluate(event)
        cv2.imshow("Smart Billiard Tracker", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break



# --------------------------
# Save CSV thread: test detect
def save_detections_to_csv(detect_queue, output_path, rel_frame_queue):
    import csv
    print("Start saving detections...")

    with open(output_path, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame_id", "name", "x", "y", "r", "conf"])

        while True:
            try:
                data = detect_queue.get(timeout=2)
                if data is None:
                    break

                if isinstance(data, tuple) and len(data) == 2:
                    frame_id, detections = data
                else:
                    print(f"Skipping unexpected item in queue: {data}")
                    continue

                for det in detections:
                    if hasattr(det, "name"):
                        writer.writerow([
                            frame_id,
                            det.name,
                            round(det.x, 2),
                            round(det.y, 2),
                            round(det.r, 2),
                            round(det.conf, 3)
                        ])
                    else:
                        print(f"Skipping invalid detection object: {det}")

            except queue.Empty:
                break
            except Exception as e:
                print(f"Error saving detection: {e}")
                continue

    print("✅ Save done.")

# log test
def log_detection(detect_queue, output_path, rel_frame_queue, output_dir):
    import csv
    import os
    import queue
    import cv2

    print("Start saving detections...")

    os.makedirs(output_dir, exist_ok=True)

    with open(output_path, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame_id", "name", "x", "y", "r", "conf"])

        while True:
            try:
                data = detect_queue.get(timeout=2)
                if data is None:
                    break

                # Kiểm tra cấu trúc dữ liệu hợp lệ
                if not (isinstance(data, tuple) and len(data) == 2):
                    print(f"Skipping unexpected item in queue: {data}")
                    continue

                frame_id, detections = data

                # Lấy frame tương ứng
                try:
                    rel_frame_id, frame = rel_frame_queue.get(timeout=2)
                    if rel_frame_id != frame_id:
                        print(f"⚠️ Frame ID mismatch: detect={frame_id}, rel_frame={rel_frame_id}")
                        continue
                except queue.Empty:
                    print(f"⚠️ No frame found for frame_id={frame_id}")
                    continue

                if not detections:
                    continue

          

                # Ghi log ra CSV và vẽ bounding circle/box
                for det in detections:
                    writer.writerow([
                        frame_id,
                        det.name,
                        round(det.x, 2),
                        round(det.y, 2),
                        round(det.r, 2),
                        round(det.conf, 3)
                    ])

                    # Vẽ bounding circle (hoặc box tuỳ theo cấu trúc det)
                    cx, cy, r = int(det.x), int(det.y), int(det.r)
                    cv2.circle(frame, (cx, cy), r, (0, 255, 0), 2)
                    cv2.putText(frame, f"{det.name} {det.conf:.2f}",
                                (cx - r, cy - r - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # Lưu frame có box
                output_file = os.path.join(output_dir, f"frame_{frame_id:06d}.jpg")
                cv2.imwrite(output_file, frame)

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error saving detection: {e}")
                continue

    print("✅ Save done.")
