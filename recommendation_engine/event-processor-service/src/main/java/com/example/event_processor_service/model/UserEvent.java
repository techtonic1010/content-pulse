package com.example.event_processor_service.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Set;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserEvent {
    private String userId;
    private String contentId;

    private String eventType;

    private Double completionRatio;

    private String sessionId;

    private String source;

    private String contentType;

    private Long timestamp;

    public boolean hasValidCoreFields() {
        return userId != null && !userId.isBlank()
                && contentId != null && !contentId.isBlank()
                && eventType != null && !eventType.isBlank()
                && completionRatio != null
                && completionRatio >= 0.0
                && completionRatio <= 1.0
                && sessionId != null && !sessionId.isBlank()
                && source != null && !source.isBlank()
                && contentType != null && !contentType.isBlank()
                && timestamp != null
                && timestamp > 0;
    }

    public boolean hasSupportedEventType() {
        return eventType != null && Set.of("COMPLETE", "PLAY", "SKIP", "LIKE", "DISLIKE").contains(eventType);
    }
}
