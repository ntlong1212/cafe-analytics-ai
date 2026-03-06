package com.cafe.analytics.controller;

import com.cafe.analytics.dto.EventPayload;
import com.cafe.analytics.model.TrackingEvent;
import com.cafe.analytics.repository.TrackingEventRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;

@RestController
@RequestMapping("/api/events")
@RequiredArgsConstructor
@Slf4j
public class EventController {

    private final TrackingEventRepository repository;
    private final com.cafe.analytics.service.FaceRecognitionService faceRecognitionService;

    // Cache to map Python YOLO tracking_id to Postgres DB IDs
    private final java.util.Map<Integer, java.util.UUID> trackingToCustomerMap = new java.util.concurrent.ConcurrentHashMap<>();
    private final java.util.Map<Integer, Integer> trackingToStaffMap = new java.util.concurrent.ConcurrentHashMap<>();

    @PostMapping("/batch")
    public ResponseEntity<String> receiveEventBatch(@RequestBody java.util.List<EventPayload> payloads) {
        log.info("Received batch of {} events from AI service", payloads.size());

        java.util.List<TrackingEvent> events = new java.util.ArrayList<>();
        for (EventPayload payload : payloads) {
            TrackingEvent event = new TrackingEvent();
            event.setEventType(payload.getEventType());
            event.setEventTime(
                    payload.getTimestamp() != null 
                            ? java.time.Instant.ofEpochMilli(payload.getTimestamp()).atZone(java.time.ZoneId.systemDefault()).toLocalDateTime()
                            : java.time.LocalDateTime.now());
            event.setCameraId(payload.getCameraId());
            event.setZoneId(payload.getZoneId());

            java.util.UUID finalCustomerId = payload.getCustomerId();
            Integer finalStaffId = payload.getStaffId();
            
            // Phase 3 & 4: Extract Face Embedding and run Old/New/Staff Recognition
            if (payload.getMetadata() != null) {
                try {
                    java.util.Map<String, Object> metadata = payload.getMetadata();
                    java.util.List<Number> embedList = null;
                    String gender = "Unknown";
                    String ageRange = "Unknown";

                    // The face info can be directly in metadata or nested in demographics
                    if (metadata.containsKey("face_embedding")) {
                        embedList = (java.util.List<Number>) metadata.get("face_embedding");
                        gender = (String) metadata.getOrDefault("gender", "Unknown");
                        Object ageObj = metadata.get("age");
                        ageRange = ageObj != null ? ageObj.toString() : "Unknown";
                        metadata.remove("face_embedding"); // Don't save array in postgres log
                    } else if (metadata.containsKey("demographics")) {
                        java.util.Map<String, Object> demographics = (java.util.Map<String, Object>) metadata.get("demographics");
                        if (demographics.containsKey("face_embedding")) {
                            embedList = (java.util.List<Number>) demographics.get("face_embedding");
                            gender = (String) demographics.getOrDefault("gender", "Unknown");
                            Object ageObj = demographics.get("age");
                            ageRange = ageObj != null ? ageObj.toString() : "Unknown";
                            demographics.remove("face_embedding"); // Don't save array in postgres log
                        }
                    }

                    Integer trackId = null;
                    if (metadata.containsKey("tracking_id")) {
                         trackId = ((Number) metadata.get("tracking_id")).intValue();
                    }

                    if (embedList != null) {
                        double[] faceVector = embedList.stream().mapToDouble(Number::doubleValue).toArray();
                        com.cafe.analytics.dto.RecognitionResult result = faceRecognitionService.processFaceVector(faceVector, gender, ageRange);
                        
                        if (result != null) {
                            if (result.isStaff()) {
                                finalStaffId = result.getStaffId();
                                finalCustomerId = null;
                                if (trackId != null) trackingToStaffMap.put(trackId, finalStaffId);
                            } else {
                                finalCustomerId = result.getCustomerId();
                                if (trackId != null) trackingToCustomerMap.put(trackId, finalCustomerId);
                            }
                        }
                    } else if (trackId != null && finalStaffId == null && finalCustomerId == null) {
                        // Lookup existing mapping
                        if (trackingToStaffMap.containsKey(trackId)) {
                            finalStaffId = trackingToStaffMap.get(trackId);
                        } else if (trackingToCustomerMap.containsKey(trackId)) {
                            finalCustomerId = trackingToCustomerMap.get(trackId);
                        }
                    }
                } catch (Exception e) {
                    log.error("Error processing face embedding in payload", e);
                }
            }
            
            event.setStaffId(finalStaffId);
            event.setCustomerId(finalCustomerId);
            event.setMetadata(payload.getMetadata());

            // Avoid violating PostgreSQL ENUM constraints
            if ("FACE_ANALYZED".equals(payload.getEventType())) {
                continue;
            }

            events.add(event);
        }

        try {
            repository.saveAll(events);
            return ResponseEntity.ok("Batch of " + events.size() + " events received and saved successfully.");
        } catch (Exception e) {
            log.error("Failed to save event batch to database", e);
            return ResponseEntity.internalServerError().body("Database error occurred while saving events.");
        }
    }
}
