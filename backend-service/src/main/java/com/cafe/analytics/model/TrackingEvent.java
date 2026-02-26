package com.cafe.analytics.model;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.Instant;

@Entity
@Table(name = "events")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TrackingEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "event_type", nullable = false)
    private String eventType;

    @Column(name = "tracking_id", nullable = false)
    private Long trackingId;

    @Column(name = "timestamp", nullable = false)
    private Instant timestamp;

    @Column(name = "details", length = 500)
    private String details;
}
