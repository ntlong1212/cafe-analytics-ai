import cv2
import requests
import time
from ultralytics import YOLO
import queue
import threading
import json
import numpy as np
from deepface import DeepFace

# Camera or Video configuration
VIDEO_SOURCE = "video_chuyen_nghiep.mp4"
# Java Backend API URL
BACKEND_API_URL = "http://localhost:8080/api/events/batch"

# Queue cho luồng phân tích khuôn mặt (DeepFace)
face_queue = queue.Queue()

# Queue for background HTTP requests
event_queue = queue.Queue()

# Định nghĩa các vùng Region of Interest (ROI)
# Dựa trên kích thước video mới (1920x2160)
ROIS = {
    # Khu vực quầy pha chế (BAR) - Camera dưới (Bên trái, quầy màu xanH)
    "BAR_ZONE": np.array([[50, 1200], [850, 1200], [850, 2100], [50, 2100]], np.int32),
    # Khu vực cửa ra vào (ENTRANCE) - Camera trên (Bên phải, khu vực bàn ghế gỗ)
    "ENTRANCE_ZONE": np.array([[1000, 150], [1850, 150], [1850, 1000], [1000, 1000]], np.int32)
}

def event_worker():
    """Luồng chạy ngầm: Lấy event từ queue, gom thành mẻ (batch) và gửi đi."""
    while True:
        batch = []
        try:
            event = event_queue.get(timeout=2)
            batch.append(event)
            while not event_queue.empty() and len(batch) < 50:
                batch.append(event_queue.get_nowait())
        except queue.Empty:
            pass 

        if batch:
            send_batch_with_retry(batch)
            for _ in batch:
                event_queue.task_done()

def send_batch_with_retry(batch, max_retries=3):
    """Gửi một batch sự kiện tới Spring Boot Backend."""
    retries = 0
    while retries < max_retries:
        try:
            response = requests.post(BACKEND_API_URL, json=batch, timeout=3)
            if response.status_code in (200, 201):
                print(f"[Backend] Gửi thành công {len(batch)} sự kiện.")
                return
            else:
                print(f"[Backend] Lỗi server: {response.status_code}. Thử lại...")
        except requests.exceptions.RequestException as e:
            print(f"[Backend] Lỗi kết nối. Thử lại {retries + 1}/{max_retries}...")
        
        retries += 1
        time.sleep(2 ** retries) 
    
    print(f"[CẢNH BÁO] Không thể gửi {len(batch)} sự kiện sau {max_retries} lần thử.")

# Background thread for sending HTTP events
worker_thread = threading.Thread(target=event_worker, daemon=True)
worker_thread.start()

def face_analysis_worker():
    """Luồng chạy ngầm: Phân tích lần lượt từng Face để tránh cháy RAM (OOM)."""
    global person_info
    while True:
        try:
            track_id, frame_crop = face_queue.get()
            if frame_crop is None:
                continue

            # Check if person still exists in tracking dictionary
            if track_id not in person_info:
                face_queue.task_done()
                continue
            
            # Phân tích tuổi, giới tính
            res = DeepFace.analyze(frame_crop, actions=['age', 'gender'], enforce_detection=True)
            if isinstance(res, list):
                res = res[0]
            
            # Lấy Face Vector
            embedding = DeepFace.represent(frame_crop, model_name="Facenet512", enforce_detection=True)
            if isinstance(embedding, list) and len(embedding) > 0:
                face_vector = embedding[0].get('embedding')
                # Check existance safely to prevent race conditions during Garbage Collecting
                if track_id in person_info:
                    person_info[track_id]['metadata']['face_embedding'] = face_vector

            if track_id in person_info:
                person_info[track_id]['metadata']['age'] = res.get('age')
                person_info[track_id]['metadata']['gender'] = res.get('dominant_gender')
                person_info[track_id]['analyzed_face'] = True
                
                # SEND EVENT TO BACKEND IMMEDIATELY TO REGISTER CUSTOMER/STAFF
                event_queue.put({
                    "eventType": "FACE_ANALYZED",
                    "timestamp": int(time.time() * 1000),
                    "cameraId": "CAM_MAIN",
                    "metadata": person_info[track_id]['metadata']
                })
                
        except ValueError as e:
            # Lỗi không tìm thấy khuôn mặt (khi dùng enforce_detection=True)
            # Không đánh dấu analyzed_face = True để vòng main có thể gửi thử lại
            print(f"Không tìm thấy khuôn mặt cho ID {track_id}, sẽ thử lại sau.")
            if track_id in person_info:
                person_info[track_id]['analyzed_face'] = False
        except Exception as e:
            print(f"Face Analysis failed for ID {track_id}: {e}")
            if track_id in person_info:
                person_info[track_id]['analyzed_face'] = False # Vẫn cho phép thử lại nếu lỗi khác
        finally:
            face_queue.task_done()

# Khởi động Face Worker chậm lại ở ngã tư
face_thread = threading.Thread(target=face_analysis_worker, daemon=True)

def garbage_collector():
    """Luồng chạy ngầm: Tự động xóa data của những người không còn trong khung hình (tránh memory leak)."""
    global person_info
    while True:
        time.sleep(30) # Quét mỗi 30 giây
        current_time = time.time()
        keys_to_delete = []
        for track_id, info in list(person_info.items()):
            # Nếu người này không xuất hiện trong vòng 60 giây qua -> Xóa
            if current_time - info.get('last_seen', current_time) > 60:
                keys_to_delete.append(track_id)
                
        for key in keys_to_delete:
            del person_info[key]
            
        if keys_to_delete:
            print(f"[Garbage Collector] Đã xóa {len(keys_to_delete)} ID ẩn khỏi bộ nhớ.")

# Khởi động Garbage Collector
gc_thread = threading.Thread(target=garbage_collector, daemon=True)

def main():
    print("Loading YOLO model...")
    model = YOLO("yolov8n.pt")
    
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    if not cap.isOpened():
        print("Error: Could not open video source.")
        return

    print("Starting Background AI analysis tasks...")
    # Khởi động các luồng quan trọng trước khi bắt hình
    global person_info
    
    # Bắt đầu luồng kiểm tra khuôn mặt và dọn rác
    face_thread.start()
    gc_thread.start()

    print("Starting Object Tracking and ROI Analysis...")
    # Thay đổi độ phân giải về 1920x2160 (nếu dùng video có kích thước này)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)

    # Dictionary lưu trữ state của từng người
    person_info = {} # track_id -> {'analyzed_face': bool, 'analysis_attempts': int, 'last_analysis_time': float, 'current_roi': str, 'roi_entry_time': float, 'last_seen': float, 'metadata': dict}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Vẽ các vùng ROI trước
        for roi_name, polygon in ROIS.items():
            cv2.polylines(frame, [polygon], isClosed=True, color=(255, 0, 0), thickness=2)
            cv2.putText(frame, roi_name, tuple(polygon[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        results = model.track(frame, persist=True, classes=[0], verbose=False)

        if results[0].boxes and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().numpy()
            
            for i, track_id in enumerate(track_ids):
                x1, y1, x2, y2 = map(int, boxes[i])
                
                # Bottom-Center point
                bottom_center = (int((x1 + x2) / 2), y2)

                # Kiểm tra xem người này đang đứng trong ROI nào
                current_roi = None
                for roi_name, polygon in ROIS.items():
                    if cv2.pointPolygonTest(polygon, bottom_center, False) >= 0:
                        current_roi = roi_name
                        break
                
                # Khởi tạo state nếu là người mới
                if track_id not in person_info:
                    person_info[track_id] = {
                        'analyzed_face': False,
                        'analysis_attempts': 0,
                        'last_analysis_time': 0,
                        'current_roi': current_roi,
                        'roi_entry_time': time.time() if current_roi else None,
                        'metadata': {'tracking_id': int(track_id)}
                    }
                    
                    event_queue.put({
                        "eventType": "CUSTOMER_ENTER", 
                        "timestamp": int(time.time() * 1000),
                        "cameraId": "CAM_MAIN",
                        "metadata": person_info[track_id]['metadata']
                    })

                info = person_info[track_id]
                info['last_seen'] = time.time()  # Quan trọng cho Garbage Collector

                # Phân tích khuôn mặt: thử lại nếu lấy phân tích chưa xong
                if not info.get('analyzed_face', False):
                    # Timeout 1s giữa mỗi lần gửi mẫu thử, tối đa 4 lần thử (nếu người ta cứ quay lưng)
                    if time.time() - info.get('last_analysis_time', 0) > 1.0 and info.get('analysis_attempts', 0) < 4:
                        
                        # Mở rộng vùng cắt (padding) thêm 15% xung quanh khuôn mặt để DeepFace tìm được cằm và tóc dễ hơn
                        w, h = x2 - x1, y2 - y1
                        pad_x = int(w * 0.15)
                        pad_y = int(h * 0.15)
                        
                        person_crop = frame[max(0, y1 - pad_y):min(frame.shape[0], y2 + pad_y), 
                                            max(0, x1 - pad_x):min(frame.shape[1], x2 + pad_x)]
                                            
                        if person_crop.size > 0:
                            info['analyzed_face'] = True # Đánh dấu tạm để Worker không bị spam hình quá nhiều
                            info['last_analysis_time'] = time.time()
                            info['analysis_attempts'] = info.get('analysis_attempts', 0) + 1
                            face_queue.put((track_id, person_crop.copy()))

                # Kiểm tra thay đổi ROI và tính Dwell Time (Thời gian đứng trong 1 ROI)
                if current_roi != info['current_roi']:
                    if info['current_roi'] is not None and info['roi_entry_time'] is not None:
                        dwell_time = time.time() - info['roi_entry_time']
                        
                        # Chỉ gửi sự kiện nếu đứng ở 1 ROI hơn 3 giây
                        if dwell_time >= 3.0: 
                            event_type = "STAFF_PREPARE_DRINK" if info['current_roi'] == "BAR_ZONE" else "CUSTOMER_EXIT"
                            event_queue.put({
                                "eventType": event_type,
                                "timestamp": int(time.time() * 1000),
                                "cameraId": "CAM_MAIN",
                                "zoneId": info['current_roi'],
                                "metadata": {
                                    "tracking_id": int(track_id),
                                    "dwell_time_seconds": round(dwell_time, 2),
                                    "demographics": info['metadata']
                                }
                            })
                    
                    # Update ROI state
                    info['current_roi'] = current_roi
                    info['roi_entry_time'] = time.time() if current_roi else None

                # Vẽ UI
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.circle(frame, bottom_center, 4, (0, 0, 255), -1)
                
                age_gender = f"A:{info['metadata'].get('age','?')} G:{info['metadata'].get('gender','?')}"
                cv2.putText(frame, f"ID: {track_id} {age_gender}", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
            cv2.putText(frame, f"People count: {len(track_ids)}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            cv2.putText(frame, "People count: 0", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Thay đổi kích thước hiển thị cho vừa màn hình (chia 3 kích thước: 1920/3=640, 2160/3=720)
        display_frame = cv2.resize(frame, (640, 720))
        cv2.imshow("Cafe Analytics - Object Tracking", display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
