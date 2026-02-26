# Cafe Analytics System ☕📷

An Enterprise-grade Computer Vision and AI-based analytics system designed for cafes and F&B businesses. This project integrates cutting-edge realtime video processing with a scalable backend architecture.

## 🌟 System Architecture

This project is built using a Microservices Architecture, decoupling heavy AI computation from business logic and data management.

1. **AI Video Processing Service (`ai-service`)**
   - **Role:** Ingests RTSP camera streams, performs real-time object detection, face recognition, and pose estimation. Extracts metadata such as demographics, returning customer status, and staff actions.
   - **Tech Stack:** Python, OpenCV, PyTorch, YOLOv8, DeepFace, MediaPipe.
   - **Output:** Streams structured event data (JSON) to the Core Backend.

2. **Core Backend API (`backend-service`)**
   - **Role:** Handles business logic, data persistence, and provides a RESTful API for frontend dashboards. Calculates staff working hours, customer statistics, and dwell times.
   - **Tech Stack:** Java 17+, Spring Boot, Spring Data JPA, Hibernate.
   - **Architecture:** Layered Architecture (Controller -> Service -> Repository).

3. **Database**
   - **Role:** Relational data storage for structured logs and summaries.
   - **Tech Stack:** PostgreSQL.

## 📂 Repository Structure

```text
├── ai-service/          # Python AI engine for vision processing
│   ├── models/          # Pre-trained models
│   ├── src/             # Core tracking & recognition logic
│   └── requirements.txt
├── backend-service/     # Spring Boot core API
│   ├── src/main/java    # Java source code
│   └── pom.xml          # Maven dependencies
├── database/            # SQL scripts & initialization
└── README.md            # Project documentation
```

## 🚀 Key Features

*   **Customer Demographics:** Real-time age and gender estimation using face embeddings.
*   **Returning Customer Detection:** Facial recognition to identify loyal customers without invading privacy (using vector embeddings only).
*   **Dwell Time & Area Analysis:** Object tracking to measure time spent at tables vs. ordering.
*   **Staff Performance Monitoring:** Activity recognition to distinguish making drinks, cleaning, serving, and idle time.
*   **Automated Attendance:** Face-based login/logout for staff shifts.

## 🛠️ Setup Instructions

*Stay tuned! Setup instructions will be updated as the components are built.*
