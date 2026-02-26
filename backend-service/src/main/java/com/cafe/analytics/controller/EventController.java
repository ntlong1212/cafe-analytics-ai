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

    @PostMapping
    public ResponseEntity<String> receiveEvent(@RequestBody EventPayload payload) {
        log.info("Received event from AI service: {}", payload);

        TrackingEvent event = new TrackingEvent();
        event.setEventType(payload.getEventType());
        event.setTrackingId(payload.getTrackingId());
        // Convert epoch millis to Instant
        event.setTimestamp(
                payload.getTimestamp() != null ? Instant.ofEpochMilli(payload.getTimestamp()) : Instant.now());
        event.setDetails(payload.getDetails());

        repository.save(event);

        return ResponseEntity.ok("Event received and saved successfully.");
    }
}
