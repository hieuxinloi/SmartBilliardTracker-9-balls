import threading
import queue
from core.detector import detect_thread
from pipeline.realtime_runner import capture_thread
from core.post_processor import post_processor_thread

def main():
    # Đường dẫn input/output
    video_path = r"data\video\clip_03.mp4"
    model_path = r"models\best.pt"
    output_path = r"output3\processed_video.avi"  # Đổi sang định dạng AVI
    
    # Khởi tạo queues
    frame_queue = queue.Queue(maxsize=50)
    detect_queue = queue.Queue(maxsize=50)
    rel_frame_queue = queue.Queue(maxsize=50)
    output_queue = queue.Queue()
    
    # Đảm bảo thư mục output tồn tại
    import os
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    
    # Tạo các threads
    t1 = threading.Thread(target=capture_thread, args=(video_path, frame_queue))
    t2 = threading.Thread(target=detect_thread, args=(model_path, frame_queue, detect_queue, rel_frame_queue))
    t3 = threading.Thread(target=post_processor_thread, args=(detect_queue, rel_frame_queue, output_queue, True, output_path))
    
    # Start threads
    t1.start()
    t2.start()
    t3.start()
    
    # Wait for completion
    t1.join()
    t2.join()
    t3.join()
    
    print("Pipeline completed!")

if __name__ == "__main__":
    main()