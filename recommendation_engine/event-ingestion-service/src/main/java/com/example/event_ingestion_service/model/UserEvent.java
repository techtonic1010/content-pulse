package com.example.event_ingestion_service.model;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserEvent {
    
    private String eventId;

        @NotBlank(message = "userId is required")
    private String userId;

        @NotBlank(message = "contentId is required")
    private String contentId;

        @Pattern(
            regexp = "PLAY|LIKE|SKIP|DISLIKE",
            message = "eventType must be one of PLAY, LIKE, SKIP, DISLIKE"
        )
        private String eventType;

    private Double completionRatio;

    private String sessionId;

    private String sourceScreen; // HOME, SEARCH

    private String timestamp;
}
