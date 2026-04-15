package com.example.event_processor_service.service;

import com.example.event_processor_service.model.UserEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class UserEventConsumer {

    private static final Logger log = LoggerFactory.getLogger(UserEventConsumer.class);
    private final ContentEnrichmentService contentEnrichmentService;
    private final ObjectMapper objectMapper;
    private final UserProfileService userProfileService;
    private final String topic;

    public UserEventConsumer(
            ObjectMapper objectMapper,
            UserProfileService userProfileService,
            ContentEnrichmentService contentEnrichmentService,
            @Value("${app.kafka.topic:user-events}") String topic
    ) 
    {
        this.objectMapper = objectMapper;
        this.userProfileService = userProfileService;
        this.contentEnrichmentService = contentEnrichmentService;
        this.topic = topic;
    }

    @KafkaListener(topics = "${app.kafka.topic:user-events}", groupId = "${spring.kafka.consumer.group-id}")
    public void consume(String payload) {
        try {
            UserEvent event = objectMapper.readValue(payload, UserEvent.class);

            if (!event.hasValidCoreFields()) {
                log.warn("Ignoring event due to missing required fields. payload={}", payload);
                return;
            }
            if (!event.hasSupportedEventType()) {
                log.warn("Ignoring event due to unsupported eventType={} payload={}", event.getEventType(), payload);
                return;
            }

            ContentEnrichmentService.GenreLookupResult lookupResult =
                    contentEnrichmentService.getGenresForContent(event.getContentId());
            List<String> genres = lookupResult.genres();

            log.info(
                    "Event enriched | userId={} | contentId={} | source={} | genres={}",
                    event.getUserId(),
                    event.getContentId(),
                    lookupResult.source(),
                    genres
            );

                userProfileService.processEvent(event, genres);

            log.info(
                    "Processed eventId={} for userId={} on topic={}",
                    event.getEventId(),
                    event.getUserId(),
                    topic
            );
        } catch (Exception ex) {
            log.error("Failed to process Kafka message. payload={}", payload, ex);
        }
    }
}