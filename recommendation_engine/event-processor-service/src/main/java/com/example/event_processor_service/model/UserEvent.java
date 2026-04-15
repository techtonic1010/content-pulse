package com.example.event_processor_service.model;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.util.Set;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserEvent {
    
    private String eventId;
    
    private String userId;
    private String contentId;

    private String eventType;   // PLAY, SKIP, LIKE

    private Double completionRatio;

    private String sessionId;

    private String sourceScreen; // HOME, SEARCH

    private String timestamp;

    public boolean hasValidCoreFields() {
        return userId != null && !userId.isBlank() && contentId != null && !contentId.isBlank();
    }

    public boolean hasSupportedEventType() {
        return eventType != null && Set.of("PLAY", "LIKE", "SKIP", "DISLIKE").contains(eventType);
    }
}
