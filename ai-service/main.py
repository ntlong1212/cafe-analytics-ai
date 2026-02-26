import cv2
import requests
import time
from ultralytics import YOLO
import threading

# Cấu hình Camera hoặc Video
VIDEO_SOURCE = 0 # Sử dụng webcam. Có thể thay bằng đường dẫn video.
# URL của Java Backend API
BACKEND_API_URL = "http://localhost:8080/api/events"

def send_event_to_backend(event_data):
    """
    Gửi dữ liệu sự kiện nhận diện được sang Java Backend
    """
    try:
        response = requests.post(BACKEND_API_URL, json=event_data, timeout=2)
        print(f"[Backend Response] Status: {response.status_code}, Data: {event_data}")
    except requests.exceptions.RequestException as e:
        print(f"[Error] Failed to send data to backend: {e}")

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
                        "eventType": "CUSTOMER_ENTRY", # Tên sự kiện (có thể tùy chỉnh)
                        "trackingId": int(track_id),
                        "timestamp": int(time.time() * 1000),
                        "details": f"Detected new person with ID {track_id}"
                    }
                    
                    # Dùng luồng (thread) để không làm chậm video frame
                    threading.Thread(target=send_event_to_backend, args=(event_data,)).start()
            
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
