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

    @PostMapping("/batch")
    public ResponseEntity<String> receiveEventBatch(@RequestBody java.util.List<EventPayload> payloads) {
        log.info("Received batch of {} events from AI service", payloads.size());

        java.util.List<TrackingEvent> events = new java.util.ArrayList<>();
        for (EventPayload payload : payloads) {
            TrackingEvent event = new TrackingEvent();
            event.setEventType(payload.getEventType());
            // Convert epoch millis to LocalDateTime in JVM timezone
            event.setEventTime(
                    payload.getTimestamp() != null 
                            ? java.time.Instant.ofEpochMilli(payload.getTimestamp()).atZone(java.time.ZoneId.systemDefault()).toLocalDateTime()
                            : java.time.LocalDateTime.now());
            event.setCameraId(payload.getCameraId());
            event.setZoneId(payload.getZoneId());
            event.setStaffId(payload.getStaffId());
            event.setCustomerId(payload.getCustomerId());
            event.setMetadata(payload.getMetadata());
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
