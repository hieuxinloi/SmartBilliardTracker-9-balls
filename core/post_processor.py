import queue
import cv2
import numpy as np
from utils.helpers import (PlayerState, GameState, GameSession, ShotResult, 
                         Detection, BallState, FaultType)
from core.tracker import BallTracker
from core.game_logic import GameLogic
from core.motion_detector import MotionDetector
from core.visualizer import Visualizer
import time
import traceback


def post_processor_thread(detect_queue, rel_frame_queue, output_queue=None, 
                         display=True, output_video_path=None):
    """
    Luồng xử lý chính - phân tích logic game
    """
    print("##--PostProcessor started")
    
    # Khởi tạo logging
    import logging
    import os
    from datetime import datetime
    
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"game_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logging.info("=== Bắt đầu phiên chơi mới ===")
    
    # Khởi tạo các components
    original_width = 1920
    original_height = 1080
    display_scale = 0.7  # Giảm kích thước xuống 70%
    
    table_width = int(original_width * display_scale)
    table_height = int(original_height * display_scale)
    
    # Tính toán kích thước panel thông tin
    info_panel_height = 200
    total_height = table_height + info_panel_height
    
    tracker = BallTracker(distance_threshold=30, missing_threshold=10)
    motion_detector = MotionDetector(motion_threshold=5.0, stable_frames=15)
    game_logic = GameLogic()
    visualizer = Visualizer(table_width=original_width, table_height=original_height)
    
    # Khởi tạo output video nếu cần
    out = None
    if output_video_path:
        # Sử dụng DIVX codec cho Windows
        fourcc = cv2.VideoWriter_fourcc(*'DIVX')
        
        # Tạo thư mục chứa video nếu chưa tồn tại
        import os
        os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
        
        try:
            # Khởi tạo VideoWriter với kích thước đầy đủ (bao gồm cả panel thông tin)
            out = cv2.VideoWriter(
                output_video_path,
                fourcc,
                30.0,
                (table_width, total_height)
            )
            
            if not out.isOpened():
                print(f"Warning: Không thể tạo output video tại {output_video_path}")
                out = None
            else:
                print(f"Đã tạo output video: {output_video_path}")
        except Exception as e:
            print(f"Error creating video writer: {str(e)}")
            out = None
        
    # Khởi tạo biến theo dõi bi chạm
    first_contact_ball = None
    rail_contacts = []
    shot_frames = []  # Lưu các frame trong một cú đánh
    
    # Khởi tạo game session
    game_session = GameSession(
        player1=PlayerState(player_id=1, name="Player 1", is_current=True),
        player2=PlayerState(player_id=2, name="Player 2", is_current=False)
    )
    
    frame_count = 0
    current_shot = None
    
    while True:
        try:
            data = detect_queue.get(timeout=2)
            if data is None:
                break
            
            frame_id, detections = data
            frame_count += 1
            
            # Lọc bỏ các bi nằm ngoài bàn
            filtered_detections = []
            for det in detections:
                if hasattr(tracker, 'table_corners'):
                    # Kiểm tra xem bi có nằm trong vùng bàn không
                    if cv2.pointPolygonTest(tracker.table_corners, (det.x, det.y), False) >= 0:
                        filtered_detections.append(det)
                else:
                    # Nếu không có table_corners thì giữ nguyên detection
                    filtered_detections.append(det)
            
            if len(filtered_detections) < len(detections):
                logging.debug(f"[Frame {frame_id}] Đã lọc bỏ {len(detections) - len(filtered_detections)} bi nằm ngoài bàn")
            
            # 1. Cập nhật tracking
            current_balls = tracker.update(frame_id, filtered_detections)
            
            # Log trạng thái bi trên bàn
            if frame_count % 100 == 0:
                active_balls = current_balls
                ball_names = list(active_balls.keys()) if active_balls else []
                logging.info(f"[Frame {frame_id}] Bi trên bàn ({len(ball_names)}): {', '.join(sorted(ball_names))}")
            # 2. Phát hiện chuyển động và cú đánh
            is_moving, shot_started, collisions = motion_detector.detect_motion(tracker, frame_id)
            
            if is_moving:
                logging.debug(f"[Frame {frame_id}] Phát hiện chuyển động của các bi")
                
            # Xử lý va chạm
            if collisions:
                for collision in collisions:
                    ball_id = collision['ball_id']
                    if first_contact_ball is None and ball_id != 'cue':
                        first_contact_ball = ball_id
                        logging.info(f"[Frame {frame_id}] Phát hiện bi đầu tiên bị chạm: {first_contact_ball}")
                        
                        if first_contact_ball == current_shot.target_ball:
                            current_shot.lowest_ball_hit_first = True
                            logging.info(f"✓ Chạm đúng bi mục tiêu {target_ball}")
                        else:
                            logging.warning(f"Chạm sai bi! (Chạm bi {first_contact_ball} thay vì bi {target_ball})")
            
            # 3. Xử lý cú đánh mới
            if shot_started:
                current_player = game_session.get_current_player()
                logging.info(f"\n{'='*50}")
                logging.info(f"[Frame {frame_id}] PHÁT HIỆN CÚ ĐÁNH MỚI")
                logging.info(f"Người chơi hiện tại: {current_player.name}")
                
                active_balls = current_balls
                ball_names = list(active_balls.keys()) if active_balls else []
                target_ball = game_logic.get_lowest_ball(ball_names)
                
                current_shot = ShotResult(
                    frame_start=frame_id,
                    frame_end=frame_id,
                    target_ball=target_ball
                )
                
                logging.info(f"Bi mục tiêu: {target_ball}")
                logging.info(f"Các bi trên bàn: {', '.join(sorted(ball_names))}")
                
                game_session.current_shot = current_shot
                game_session.game_state = GameState.SHOOTING
                logging.info(f"Trạng thái game chuyển sang: {game_session.game_state.value}")
            
            # 4. Cập nhật cú đánh đang diễn ra và phát hiện chạm
            if current_shot and is_moving:
                current_shot.frame_end = frame_id
                shot_frames.append(frame_id)
                
                # Kiểm tra bi chạm băng
                for ball_id, ball_state in current_balls.items():
                    x, y = ball_state.position
                    # Phát hiện chạm băng khi bi gần với cạnh bàn (threshold ~50px)
                    if x < 50 or x > visualizer.table_width - 50 or y < 50 or y > visualizer.table_height - 50:
                        if ball_id not in rail_contacts:
                            rail_contacts.append(ball_id)
                            current_shot.rail_contact = True
                            print(f"[Frame {frame_id}] Bi {ball_id} chạm băng")
                    
                    # Phát hiện bi đầu tiên bị chạm
                    if first_contact_ball is None and ball_id != 'cue' and ball_state.frame_id == frame_id:
                        first_contact_ball = ball_id
                        logging.info(f"[Frame {frame_id}] Phát hiện bi đầu tiên bị chạm: {first_contact_ball}")
                        
                        if first_contact_ball == current_shot.target_ball:
                            current_shot.lowest_ball_hit_first = True
                            logging.info(f"✓ Chạm đúng bi mục tiêu {target_ball}")
                        else:
                            logging.warning(f"❌ Chạm sai bi! (Chạm bi {first_contact_ball} thay vì bi {target_ball})")
            
            # 5. Phân tích khi cú đánh kết thúc
            if motion_detector.is_shot_ended() and current_shot:
                print(f"\n[Frame {frame_id}] === PHÂN TÍCH CÚ ĐÁNH ===")
                game_session.game_state = GameState.ANALYZING
                
                # Tìm bi bị mất (vào lỗ hoặc rơi khỏi bàn)
                missing_balls = tracker.get_missing_balls(frame_id)
                
                # Phân loại bi bị mất
                if missing_balls:
                    logging.info(f"\n[Frame {frame_id}] === PHÂN TÍCH BI MẤT KHỎI BÀN ===")
                
                for ball_id in missing_balls:
                    last_position = tracker.get_last_position(ball_id)
                    if last_position:
                        x, y = last_position.position
                        # Kiểm tra xem bi có vào lỗ hay không
                        if game_logic.check_ball_in_pocket((x, y)):
                            if ball_id == 'cue' or ball_id == '0':
                                current_shot.cue_ball_pocketed = True
                                logging.warning(f"[Frame {frame_id}] ❌ Bi cái vào lỗ! => Phạm lỗi")
                            else:
                                current_shot.balls_pocketed.append(ball_id)
                                tracker.mark_pocketed(ball_id)
                                logging.info(f"[Frame {frame_id}] ✓ Bi {ball_id} vào lỗ hợp lệ")
                        else:
                            # Bi nhảy khỏi bàn
                            current_shot.balls_off_table.append(ball_id)
                            logging.warning(f"[Frame {frame_id}] ❌ Bi {ball_id} nhảy khỏi bàn! => Phạm lỗi")
                
                # Lấy thông tin tổng kết từ motion detector
                shot_summary = motion_detector.get_shot_summary()
                
                # Kiểm tra chạm băng
                current_shot.rail_contact = shot_summary['has_rail_contact']
                if current_shot.rail_contact:
                    logging.info(f"✓ Phát hiện chạm băng: {', '.join(shot_summary['rail_contacts'])}")
                else:
                    logging.warning("❌ Không phát hiện chạm băng")
                
                # Kiểm tra bi đầu tiên được chạm
                first_hit = shot_summary['first_hit_ball']
                if first_hit:
                    if first_hit == current_shot.target_ball:
                        current_shot.lowest_ball_hit_first = True
                        logging.info(f"✓ Xác nhận chạm đúng bi mục tiêu {first_hit} đầu tiên")
                    else:
                        current_shot.lowest_ball_hit_first = False
                        logging.warning(f"❌ Chạm sai bi! Chạm bi {first_hit} thay vì bi {current_shot.target_ball}")
                else:
                    current_shot.lowest_ball_hit_first = False
                    logging.warning("❌ Không phát hiện được bi nào bị chạm")
                
                # Phân tích cú đánh
                active_balls = tracker.get_active_balls()
                is_valid, continue_turn, fault_type = game_logic.analyze_shot(
                    current_shot, active_balls
                )
                
                current_shot.is_valid = is_valid
                current_shot.fault_type = fault_type
                
                # In kết quả phân tích cú đánh
                logging.info(f"\n[Frame {frame_id}] === KẾT QUẢ PHÂN TÍCH CÚ ĐÁNH ===")
                logging.info(f"Tình trạng: {'✓ HỢP LỆ' if is_valid else '❌ PHẠM LỖI'}")
                
                if not is_valid:
                    logging.warning(f"Lỗi phạm luật: {fault_type.value}")
                
                if current_shot.balls_pocketed:
                    logging.info(f"Bi vào lỗ: {', '.join(current_shot.balls_pocketed)}")
                if current_shot.cue_ball_pocketed:
                    logging.warning("Bi cái vào lỗ")
                if current_shot.balls_off_table:
                    logging.warning(f"Bi nhảy khỏi bàn: {', '.join(current_shot.balls_off_table)}")
                
                # Kiểm tra thắng/thua và cập nhật trạng thái
                current_player = game_session.get_current_player()
                
                if game_logic.check_win_condition(current_shot, active_balls):
                    logging.info(f"\n🏆 {current_player.name} THẮNG CUỘC! (Bi 9 vào lỗ hợp lệ)")
                    game_session.winner = current_player.player_id
                    game_session.game_state = GameState.GAME_OVER
                
                elif not is_valid:
                    # Phạm lỗi -> chuyển lượt
                    logging.warning(f"→ {current_player.name} phạm lỗi => Chuyển lượt")
                    current_player.consecutive_fouls += 1
                    if current_player.consecutive_fouls >= 3:
                        logging.warning(f"❌ {current_player.name} đã phạm lỗi {current_player.consecutive_fouls} lần liên tiếp!")
                    game_session.switch_player()
                    game_session.game_state = GameState.WAITING
                
                elif continue_turn:
                    # Đánh hợp lệ và có bi vào lỗ -> được đánh tiếp
                    logging.info(f"✓ {current_player.name} đánh hợp lệ và được tiếp tục")
                    current_player.consecutive_fouls = 0
                    game_session.game_state = GameState.WAITING
                
                else:
                    # Đánh hợp lệ nhưng không có bi vào lỗ -> chuyển lượt
                    next_player = game_session.player2 if current_player == game_session.player1 else game_session.player1
                    logging.info(f"→ Chuyển lượt sang {next_player.name}")
                    current_player.consecutive_fouls = 0
                    game_session.switch_player()
                    game_session.game_state = GameState.WAITING
                
                # Gửi kết quả ra ngoài nếu cần
                if output_queue:
                    output_queue.put({
                        'frame_id': frame_id,
                        'shot_result': current_shot,
                        'game_session': game_session
                    })
                
                # Reset cho cú đánh tiếp theo
                motion_detector.reset_shot()
                first_contact_ball = None
                rail_contacts.clear()
                shot_frames.clear()
                current_shot = None
                
                if game_session.game_state == GameState.GAME_OVER:
                    print("\n=== GAME OVER ===")
                    break
            
                # Lấy frame từ queue và hiển thị
            if display or output_video_path:
                try:
                    frame_data = rel_frame_queue.get(timeout=2)
                    if frame_data is not None:
                        _, frame = frame_data  # Unpack frame_id and frame from tuple
                        if isinstance(frame, tuple):
                            frame = np.array(frame)
                        frame = frame.copy()  # Make a copy of numpy array
                        
                        # Resize frame cho dễ xem
                        display_frame = cv2.resize(frame, (table_width, table_height))
                        
                        # Vẽ thông tin lên frame
                        active_balls = tracker.get_active_balls()
                        target_ball = current_shot.target_ball if current_shot else None
                        
                        # Vẽ lỗ bi
                        visualizer.draw_pockets(frame, game_logic.pocket_zones)
                        
                        # Vẽ bi và thông tin
                        for ball_id, ball_state in current_balls.items():
                            detection = Detection(
                                name=ball_id,
                                x=ball_state.position[0],
                                y=ball_state.position[1],
                                r=15,  # Bán kính mặc định của bi
                                conf=1.0
                            )
                            is_target = ball_id == target_ball
                            is_moving = ball_state.frame_id == frame_id  # Bi đang chuyển động nếu được cập nhật ở frame hiện tại
                            visualizer.draw_ball(frame, detection, is_target, is_moving)
                            
                            # Vẽ quỹ đạo cho bi cái khi đang trong cú đánh
                            if current_shot and ball_id == 'cue' and frame_id in shot_frames:
                                visualizer.draw_trajectory(frame, tracker, ball_id, frames=10)
                        
                        # Vẽ bảng thông tin game
                        info_panel = visualizer.draw_info_panel(frame, game_session, current_shot, 
                                                            list(active_balls), frame_id)
                        
                        # Resize frame cho hiển thị
                        display_frame = cv2.resize(frame, (table_width, table_height))
                        
                        # Vẽ thông tin lên frame hiển thị
                        if current_shot:
                            visualizer.draw_shot_info(display_frame, current_shot)
                        
                        # Tạo info panel với kích thước phù hợp
                        info_panel = visualizer.draw_info_panel(
                            display_frame, 
                            game_session,
                            current_shot,
                            list(active_balls),
                            frame_id
                        )
                        
                        # Ghép panel vào frame hiển thị
                        display_frame_with_info = np.vstack([display_frame, info_panel])
                        
                        # Hiển thị frame
                        if display:
                            cv2.imshow('Smart Billiard Tracker', display_frame_with_info)
                            key = cv2.waitKey(1)
                            if key == ord('q') or key == 27:  # q hoặc ESC để thoát
                                break
                        
                        # Lưu video
                        if out is not None and out.isOpened():
                            try:
                                # Đảm bảo frame là uint8 và có kích thước đúng
                                frame_to_write = cv2.convertScaleAbs(display_frame_with_info)
                                if frame_to_write.shape[:2] != (total_height, table_width):
                                    frame_to_write = cv2.resize(frame_to_write, (table_width, total_height))
                                out.write(frame_to_write)
                            except Exception as e:
                                print(f"Lỗi ghi frame: {str(e)}")
                                # Debug info
                                print(f"Frame shape: {frame_to_write.shape}, dtype: {frame_to_write.dtype}")
                except Exception as e:
                    print(f"Error processing frame {frame_id}: {str(e)}")
                    continue            # Log định kỳ
            if frame_count % 100 == 0:
                active_balls = tracker.get_active_balls()
                print(f"[Frame {frame_id}] Đang xử lý... Bi trên bàn: {len(active_balls)}")
                
        except queue.Empty:
            time.sleep(1)
            continue
        except Exception as e:
            print(f"PostProcessor error at frame {frame_id}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Cleanup
    if out is not None:
        out.release()
    cv2.destroyAllWindows()
    print("##--PostProcessor finished")
