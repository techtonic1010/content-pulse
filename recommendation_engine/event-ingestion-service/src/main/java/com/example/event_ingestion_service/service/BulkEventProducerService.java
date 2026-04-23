package com.example.event_ingestion_service.service;

import com.example.event_ingestion_service.model.UserEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;

@Service
public class BulkEventProducerService {

    private static final Logger log = LoggerFactory.getLogger(BulkEventProducerService.class);
    private static final long GAP_MILLIS = 2000;
    private static final int DEFAULT_USER_POOL_SIZE = 5;

    private static final List<String> SAMPLE_CONTENT_IDS = List.of(
            "movie_1",
            "movie_2",
            "movie_3",
            "movie_4",
            "movie_5",
            "movie_6",
            "movie_7",
            "movie_8",
            "movie_9",
            "movie_10"
    );

    private static final List<String> SAMPLE_EVENT_TYPES = List.of(
            "COMPLETE",
            "PLAY",
            "LIKE",
            "SKIP",
            "PLAY",
            "COMPLETE",
            "LIKE",
            "PLAY",
            "SKIP",
            "COMPLETE"
    );

    private static final List<Double> SAMPLE_COMPLETION_RATIOS = List.of(
            0.95,
            0.62,
            1.0,
            0.08,
            0.41,
            0.91,
            1.0,
            0.53,
            0.12,
            0.97
    );

    private final EventProducerService eventProducerService;

    public BulkEventProducerService(EventProducerService eventProducerService) {
        this.eventProducerService = eventProducerService;
    }

    public int produceForUser(String userId) {
        int count = SAMPLE_CONTENT_IDS.size();
        for (int i = 0; i < count; i++) {
            UserEvent event = createEventFor(userId, i);

            eventProducerService.send(event);
            log.info(
                    "Bulk event sent userId={} contentId={} eventType={} ratio={}",
                    event.getUserId(),
                    event.getContentId(),
                    event.getEventType(),
                    event.getCompletionRatio()
            );

            if (i < count - 1) {
                sleepGap();
            }
        }
        return count;
    }

    public BulkProductionResult produceForUserPool() {
        int count = SAMPLE_CONTENT_IDS.size();
        int userPoolSize = Math.min(DEFAULT_USER_POOL_SIZE, count);

        for (int i = 0; i < count; i++) {
            String userId = "u_" + ((i % userPoolSize) + 1);
            UserEvent event = createEventFor(userId, i);

            eventProducerService.send(event);
            log.info(
                    "Bulk event sent userId={} contentId={} eventType={} ratio={}",
                    event.getUserId(),
                    event.getContentId(),
                    event.getEventType(),
                    event.getCompletionRatio()
            );

            if (i < count - 1) {
                sleepGap();
            }
        }

        return new BulkProductionResult(count, userPoolSize, GAP_MILLIS / 1000);
    }

    private UserEvent createEventFor(String userId, int index) {
        UserEvent event = new UserEvent();
        event.setUserId(userId);
        event.setContentId(SAMPLE_CONTENT_IDS.get(index));
        event.setEventType(SAMPLE_EVENT_TYPES.get(index));
        event.setCompletionRatio(SAMPLE_COMPLETION_RATIOS.get(index));
        event.setTimestamp(Instant.now().getEpochSecond());
        event.setSessionId("s_bulk_" + userId);
        event.setSource("bulk-simulator");
        event.setContentType("movie");
        return event;
    }

    private void sleepGap() {
        try {
            Thread.sleep(GAP_MILLIS);
        } catch (InterruptedException interruptedException) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Bulk event generation interrupted", interruptedException);
        }
    }

    public record BulkProductionResult(int producedCount, int userPoolSize, long gapSeconds) {
    }
}
