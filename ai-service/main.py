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
VIDEO_SOURCE = 0 # Use webcam. Can be replaced with a video file path.
# Java Backend API URL
BACKEND_API_URL = "http://localhost:8080/api/events/batch"

# Queue for background HTTP requests
event_queue = queue.Queue()

# Định nghĩa các vùng Region of Interest (ROI)
# Tọa độ (x, y) của các đa giác trên frame 640x480
ROIS = {
    "BAR_ZONE": np.array([[50, 200], [250, 200], [250, 480], [50, 480]], np.int32),
    "ENTRANCE_ZONE": np.array([[350, 50], [600, 50], [600, 250], [350, 250]], np.int32)
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

def async_analyze_face(frame_crop, track_id, person_info_dict):
    """Phân tích tuổi, giới tính trong một luồng riêng để tránh đứng hình video."""
    try:
        # Lấy thông tin tuổi và giới tính
        res = DeepFace.analyze(frame_crop, actions=['age', 'gender'], enforce_detection=False)
        if isinstance(res, list):
            res = res[0]
        
        # Lấy Face Vector
        embedding = DeepFace.represent(frame_crop, model_name="VGG-Face", enforce_detection=False)
        if isinstance(embedding, list) and len(embedding) > 0:
            face_vector = embedding[0].get('embedding')
            person_info_dict[track_id]['metadata']['face_embedding'] = face_vector

        person_info_dict[track_id]['metadata']['age'] = res.get('age')
        person_info_dict[track_id]['metadata']['gender'] = res.get('dominant_gender')
        
    except Exception as e:
        print(f"Face Analysis failed for ID {track_id}: {e}")
    finally:
        person_info_dict[track_id]['analyzed_face'] = True

def main():
    print("Loading YOLO model...")
    model = YOLO("yolov8n.pt")
    
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    if not cap.isOpened():
        print("Error: Could not open video source.")
        return

    print("Starting Object Tracking and ROI Analysis...")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Dictionary lưu trữ state của từng người
    person_info = {} # track_id -> {'analyzed_face': bool, 'current_roi': str, 'roi_entry_time': float, 'metadata': dict}

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

                # Phân tích khuôn mặt 1 lần
                if not info['analyzed_face']:
                    person_crop = frame[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
                    if person_crop.size > 0:
                        info['analyzed_face'] = True # Đánh dấu tạm để không phân tích liên tục
                        threading.Thread(target=async_analyze_face, args=(person_crop.copy(), track_id, person_info)).start()

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

        cv2.imshow("Cafe Analytics - Object Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
