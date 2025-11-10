import cv2
import numpy as np
from ultralytics import YOLO
from typing import List
from utils.helpers import Detection
import queue


def detect_thread(model_path, frame_queue, detect_queue, rel_frame_queue,  conf_threshold=0.1):

    
    model = YOLO(model_path)
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    for _ in range(30):
        _ = model.predict(source=dummy, conf=conf_threshold, verbose=False)
    print("Model warmed up!")
    print("Start detecting...")
    while True:
        try:
            data = frame_queue.get(timeout=2)            
            if data is None:
                break
            rel_frame_queue.put(data)
            frame_id, item = data

            results = model.predict(source=item, conf=conf_threshold, verbose=False)[0]
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
                r = max(x2 - x1, y2 - y1) / 2
                detections.append(Detection(name=name, x=float(cx), y=float(cy), r=float(r), conf=float(conf)))

            detect_queue.put((frame_id,detections))
        except queue.Empty:
            break
        except Exception as e:
            print(f"Detection error: {e}")
            continue
    detect_queue.put(None)

    

    
 
    