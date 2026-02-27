package com.cafe.analytics.dto;

import lombok.Data;
import java.util.Map;
import java.util.UUID;

@Data
public class EventPayload {
    private String eventType;
    private Long timestamp;
    private Long staffId;
    private UUID customerId;
    private String cameraId;
    private String zoneId;
    private Map<String, Object> metadata;
}
