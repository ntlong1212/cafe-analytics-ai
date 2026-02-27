import cv2
import requests
import time
from ultralytics import YOLO
import queue
import threading
import json

# Cấu hình Camera hoặc Video
VIDEO_SOURCE = 0 # Sử dụng webcam. Có thể thay bằng đường dẫn video.
# URL của Java Backend API
BACKEND_API_URL = "http://localhost:8080/api/events/batch"

# Hàng đợi chứa các sự kiện chờ gửi
event_queue = queue.Queue()

def event_worker():
    """Luồng chạy ngầm: Lấy event từ queue, gom thành mẻ (batch) và gửi đi."""
    while True:
        batch = []
        # Chờ tối đa 2 giây để lấy event (tạo mini-batch)
        try:
            event = event_queue.get(timeout=2)
            batch.append(event)
            # Lấy thêm các event có sẵn trong queue mà không cần chờ tiếp
            while not event_queue.empty() and len(batch) < 50:
                batch.append(event_queue.get_nowait())
        except queue.Empty:
            pass # Quá thời gian chờ không có event mới thì bỏ qua

        if batch:
            send_batch_with_retry(batch)
            for _ in batch:
                event_queue.task_done()

def send_batch_with_retry(batch, max_retries=3):
    """Gửi một batch sự kiện, nếu lỗi thì thử lại vài lần."""
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
            print(f"[Backend] Lỗi kết nối: {e}. Thử lại {retries + 1}/{max_retries}...")
        
        retries += 1
        time.sleep(2 ** retries) # Exponential backoff: 2s, 4s, 8s
    
    # Nếu hết số lần retry mà vẫn lỗi thì có thể lưu ra file text (Dead letter queue)
    print(f"[CẢNH BÁO] Không thể gửi {len(batch)} sự kiện sau {max_retries} lần thử. Dữ liệu có thể bị mất.")

# Khởi chạy worker chạy ngầm
worker_thread = threading.Thread(target=event_worker, daemon=True)
worker_thread.start()

def main():
    # Tải mô hình YOLOv8 (sử dụng mô hình nhỏ gọn yolov8n.pt hoặc yolov8s.pt)
    print("Loading YOLO model...")
    model = YOLO("yolov8n.pt")
    
    # Khởi tạo VideoCapture
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    if not cap.isOpened():
        print("Error: Could not open video source.")
        return

    print("Starting Object Tracking...")
    
    # Set độ phân giải nếu dùng webcam
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Biến theo dõi để tránh gửi spam API liên tục cho cùng một người
    tracked_persons = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("End of video stream or error reading frame.")
            break

        # Chạy YOLOv8 tracking, persist=True để duy trì ID giữa các frame
        # classes=[0] để chỉ detect 'person'
        results = model.track(frame, persist=True, classes=[0], verbose=False)

        if results[0].boxes and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy() # Bounding boxes
            track_ids = results[0].boxes.id.int().cpu().numpy() # Tracking IDs
            
            # Đếm số người trong khung hình hiện tại
            current_people_count = len(track_ids)
            
            # Vẽ boxes lên frame và kiểm tra người mới
            for i, track_id in enumerate(track_ids):
                x1, y1, x2, y2 = map(int, boxes[i])
                
                # Vẽ box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # Chèn text ID
                cv2.putText(frame, f"ID: {track_id}", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Nếu phát hiện người mới có ID chưa từng thấy, gửi mock data
                if track_id not in tracked_persons:
                    tracked_persons.add(track_id)
                    
                    event_data = {
                        "eventType": "CUSTOMER_ENTER", # Map to Enum event_category in DB
                        "timestamp": int(time.time() * 1000),
                        "cameraId": "CAM_MAIN_DOOR",
                        "metadata": {
                            "tracking_id": int(track_id),
                            "details": f"Detected new person with ID {track_id}"
                        }
                    }
                    
                    # Thay vì tạo thread gửi ngay, đưa vào queue để worker gom mẻ (batch)
                    event_queue.put(event_data)
            
            # Hiển thị số lượng người trên màn hình
            cv2.putText(frame, f"People count: {current_people_count}", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            cv2.putText(frame, f"People count: 0", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Hiển thị video stream
        cv2.imshow("Cafe Analytics - Object Tracking", frame)

        # Nhấn 'q' để thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
