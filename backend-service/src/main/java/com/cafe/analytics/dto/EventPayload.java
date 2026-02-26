package com.cafe.analytics.dto;

import lombok.Data;

@Data
public class EventPayload {
    private String eventType;
    private Long trackingId;
    private Long timestamp; // Receive as epoch millis from Python
    private String details;
}
