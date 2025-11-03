import os
from ball_detect import detect_video
from detect_collision import get_collisions_from_data, visualize_video


def get_collisions_from_video(video_path, model_path="models/yolov8n-ball-v.1.0.0.pt", 
                              output_dir="output", output_video_path=None, 
                              conf_threshold=0.1, merge_iou_threshold=0.7, 
                              cue_ball_name="cueball", move_thresh=0.3, contact_margin=10.0,
                              create_output_video=True):
    """
    Hàm chính để phát hiện và trả về danh sách các va chạm từ video.
    
    Args:
        video_path: Đường dẫn đến video
        model_path: Đường dẫn đến model YOLO (default: "models/yolov8n-ball-v.1.0.0.pt")
        output_dir: Thư mục output (default: "output")
        output_video_path: Đường dẫn đến video output (default: None, sẽ tự tạo trong output_dir)
        conf_threshold: Ngưỡng confidence cho detection (default: 0.1)
        merge_iou_threshold: Ngưỡng IoU để merge detections (default: 0.7)
        cue_ball_name: Tên của cue ball (default: "cueball")
        move_thresh: Ngưỡng di chuyển để phát hiện va chạm (default: 0.3)
        contact_margin: Margin cho contact check (default: 10.0)
        create_output_video: Có tạo video output với visual không (default: True)
    
    Returns:
        list: Danh sách các dict, mỗi dict chứa:
            - "cueball": dict với thông tin cueball {"name", "x", "y", "r", "conf"}
            - "ball": dict với thông tin ball bị va chạm {"name", "x", "y", "r", "conf"}
            - "frame_id": số frame xảy ra va chạm
    """
    # Tạo thư mục output nếu chưa có
    os.makedirs(output_dir, exist_ok=True)
    
    print("=== STEP 1: Detecting balls ===")
    frames_data = detect_video(
        model_path=model_path,
        video_path=video_path,
        conf_threshold=conf_threshold,
        merge_iou_threshold=merge_iou_threshold
    )
    
    print("=== STEP 2: Detecting collisions ===")
    collisions_raw = get_collisions_from_data(
        frames_data=frames_data,
        cue_ball_name=cue_ball_name,
        move_thresh=move_thresh,
        contact_margin=contact_margin
    )
    
    # Chuyển đổi sang format đơn giản: list các dict với cueball, ball, frame_id
    collisions = [
        {
            "cueball": coll["cueball"],
            "ball": coll["ball"],
            "frame_id": coll["frame_id"]
        }
        for coll in collisions_raw
    ]
    
    print(f"[DONE] Found {len(collisions)} collisions.")
    
    # Tạo video output với visual
    if create_output_video:
        if output_video_path is None:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_video_path = os.path.join(output_dir, f"{video_name}_output.mp4")
        
        print("=== STEP 3: Creating output video with visualizations ===")
        visualize_video(video_path, frames_data, collisions_raw, output_video_path)
    
    return collisions


def main():
    """
    Hàm main để chạy với tham số mặc định.
    """
    collisions = get_collisions_from_video(
        video_path="videos/10.mp4",
        output_dir="output10"
    )

    if collisions:
        print(f"\n=== All collisions (Total: {len(collisions)}) ===")
        for i, coll in enumerate(collisions): 
            print(f"Collision {i+1}:")
            print(f"  Frame: {coll['frame_id']}")
            print(f"  Cueball: {coll['cueball']}")
            print(f"  Ball hit: {coll['ball']}")
    else:
        print("No collisions detected.")
    
    return collisions


if __name__ == "__main__":
    main()
