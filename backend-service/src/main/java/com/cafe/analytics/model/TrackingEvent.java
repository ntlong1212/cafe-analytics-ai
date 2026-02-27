package com.cafe.analytics.model;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import org.hibernate.annotations.ColumnTransformer;

import java.time.Instant;
import java.util.UUID;
import java.util.Map;

@Entity
@Table(name = "ai_events_log")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TrackingEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "event_time", nullable = false)
    private Instant eventTime;

    @Column(name = "event_type", nullable = false, columnDefinition = "event_category")
    @ColumnTransformer(write = "?::event_category")
    private String eventType;

    @Column(name = "staff_id")
    private Integer staffId;

    @Column(name = "customer_id")
    private UUID customerId;

    @Column(name = "camera_id", length = 50)
    private String cameraId;

    @Column(name = "zone_id", length = 50)
    private String zoneId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata", columnDefinition = "jsonb")
    private Map<String, Object> metadata;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;
}
