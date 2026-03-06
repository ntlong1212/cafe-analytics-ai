package com.cafe.analytics.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class RecognitionResult {
    private boolean isStaff;
    private Integer staffId;
    private UUID customerId;

    public static RecognitionResult asStaff(Integer staffId) {
        return new RecognitionResult(true, staffId, null);
    }

    public static RecognitionResult asCustomer(UUID customerId) {
        return new RecognitionResult(false, null, customerId);
    }
}
