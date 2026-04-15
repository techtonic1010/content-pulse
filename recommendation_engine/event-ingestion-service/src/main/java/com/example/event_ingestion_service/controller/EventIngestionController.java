package com.example.event_ingestion_service.controller;

import com.example.event_ingestion_service.model.UserEvent;
import com.example.event_ingestion_service.service.EventProducerService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/events")
public class EventIngestionController {
    private final EventProducerService producerService;

    public EventIngestionController(EventProducerService producerService) {
        this.producerService = producerService;
    }

    @PostMapping
    public ResponseEntity<Map<String, String>> ingestEvent(@Valid @RequestBody UserEvent event) {
        producerService.send(event);
        return ResponseEntity.accepted().body(Map.of("status", "Event accepted"));
    }
}
// it send event to the kafka producer class to make an event
// controller → producerService.send(event) → KafkaTemplate → Kafka topic

// 👉 producerService internally uses:

// kafkaTemplate.send(...)
////////////////////////////////////////////////////////////////
// Controller → producerService.send(event)
//               ↓
// EventProducerService → kafkaTemplate.send(...)