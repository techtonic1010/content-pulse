package com.example.event_ingestion_service.model;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserEvent {
    @NotBlank(message = "userId is required")
    private String userId;

    @NotBlank(message = "contentId is required")
    private String contentId;

    @NotBlank(message = "eventType is required")
    @Pattern(
            regexp = "COMPLETE|PLAY|SKIP|LIKE|DISLIKE",
            message = "eventType must be one of COMPLETE, PLAY, SKIP, LIKE, DISLIKE"
    )
    private String eventType;

    @NotNull(message = "completionRatio is required")
    @DecimalMin(value = "0.0", message = "completionRatio must be >= 0.0")
    @DecimalMax(value = "1.0", message = "completionRatio must be <= 1.0")
    private Double completionRatio;

    @NotBlank(message = "sessionId is required")
    private String sessionId;

    @NotBlank(message = "source is required")
    private String source;

    @NotBlank(message = "contentType is required")
    private String contentType;

    @NotNull(message = "timestamp is required")
    private Long timestamp;
}
