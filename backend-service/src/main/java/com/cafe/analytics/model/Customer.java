package com.cafe.analytics.model;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "customers")
@Data
@NoArgsConstructor
public class Customer {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    // Hibernate 6 supports mapping double[] directly to FLOAT8[] natively using JdbcTypeCode
    @Column(name = "face_vector", columnDefinition = "float8[]")
    @JdbcTypeCode(SqlTypes.ARRAY)
    private double[] faceVector;

    @Column(name = "predicted_gender")
    private String predictedGender;

    @Column(name = "predicted_age_range")
    private String predictedAgeRange;

    @Column(name = "first_seen_at")
    private LocalDateTime firstSeenAt;

    @Column(name = "last_seen_at")
    private LocalDateTime lastSeenAt;

    @Column(name = "visit_count")
    private Integer visitCount;

    @PrePersist
    protected void onCreate() {
        firstSeenAt = LocalDateTime.now();
        lastSeenAt = LocalDateTime.now();
        if (visitCount == null) {
            visitCount = 1;
        }
    }

    @PreUpdate
    protected void onUpdate() {
        lastSeenAt = LocalDateTime.now();
    }
}
