package com.example.event_processor_service.service;

import com.example.event_processor_service.model.UserEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

import java.util.Objects;

@Service
public class UserEventConsumer {

    private static final Logger log = LoggerFactory.getLogger(UserEventConsumer.class);
    private static final String USER_EVENTS_KEY_PREFIX = "user_events:";
    private static final long EVENT_WINDOW_SIZE = 50;

    private final ObjectMapper objectMapper;
    private final RedisTemplate<String, String> redisTemplate;
    private final String topic;

    public UserEventConsumer(
            ObjectMapper objectMapper,
            RedisTemplate<String, String> redisTemplate,
            @Value("${app.kafka.topic:user-events}") String topic
    ) 
    {
        this.objectMapper = objectMapper;
        this.redisTemplate = redisTemplate;
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

            String redisKey = USER_EVENTS_KEY_PREFIX + event.getUserId();
            String normalizedEvent = objectMapper.writeValueAsString(event);

                redisTemplate.opsForList().leftPush(
                    Objects.requireNonNull(redisKey),
                    Objects.requireNonNull(normalizedEvent)
                );
                redisTemplate.opsForList().trim(Objects.requireNonNull(redisKey), 0, EVENT_WINDOW_SIZE - 1);

            log.info(
                    "Processed event for userId={} contentId={} topic={} redisKey={} windowSize={}",
                    event.getUserId(),
                    event.getContentId(),
                    topic,
                    redisKey,
                    EVENT_WINDOW_SIZE
            );
        } catch (Exception ex) {
            log.error("Failed to process Kafka message. payload={}", payload, ex);
        }
    }
}