package com.example.event_ingestion_service.service;

import com.example.event_ingestion_service.model.UserEvent;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Objects;

@Service
public class EventProducerService {

    private final KafkaTemplate<String, UserEvent> kafkaTemplate;
    private final String topicName;

    public EventProducerService(
            KafkaTemplate<String, UserEvent> kafkaTemplate,
            @Value("${app.kafka.topic:user-events}") String topicName
    ) 
    {
        this.kafkaTemplate = kafkaTemplate;
        this.topicName = topicName;
    }

    public void send(UserEvent event) {
        if (event.getTimestamp() == null) {
            event.setTimestamp(Instant.now().getEpochSecond());
        }

        kafkaTemplate.send(
            Objects.requireNonNull(topicName),
            Objects.requireNonNull(event.getUserId()),
            event
        );
    }
}
// 👉 Your method:

// kafkaTemplate.send(topicName, event.getUserId(), event);

// 👉 does:

// takes your UserEvent
// converts it to JSON
// pushes it into Kafka

// 👉 Ho, almost barobar 👍 (thoda refine karto)

// 🧠 Flow (short)

// 👉
// Controller → Service → Kafka/DB → Response

// 🔁 Exact
// Controller la hit karto
// Controller → Service la call karto (object pass karto)
// Service → logic + Kafka/Redis handle karto
// Controller → response return karto