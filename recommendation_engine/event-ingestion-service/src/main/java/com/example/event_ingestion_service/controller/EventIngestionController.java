package com.example.event_ingestion_service.controller;

import com.example.event_ingestion_service.model.UserEvent;
import com.example.event_ingestion_service.service.BulkEventProducerService;
import com.example.event_ingestion_service.service.EventProducerService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/events")
public class EventIngestionController {
    private final EventProducerService producerService;
    private final BulkEventProducerService bulkEventProducerService;

    public EventIngestionController(
            EventProducerService producerService,
            BulkEventProducerService bulkEventProducerService
    ) {
        this.producerService = producerService;
        this.bulkEventProducerService = bulkEventProducerService;
    }

    @PostMapping
    public ResponseEntity<Map<String, String>> ingestEvent(@Valid @RequestBody UserEvent event) {
        producerService.send(event);
        return ResponseEntity.accepted().body(Map.of("status", "Event accepted"));
    }

    @PostMapping("/bulk")
    public ResponseEntity<Map<String, Object>> ingestBulkSimulation() {
        BulkEventProducerService.BulkProductionResult result = bulkEventProducerService.produceForUserPool();
        return ResponseEntity.accepted().body(Map.of(
                "status", "Bulk simulation accepted",
                "mode", "rotating-user-pool",
                "producedCount", result.producedCount(),
                "userPoolSize", result.userPoolSize(),
                "gapSeconds", result.gapSeconds()
        ));
    }

    @PostMapping("/bulk/{userId}")
    public ResponseEntity<Map<String, Object>> ingestBulkForUser(@PathVariable String userId) {
        int producedCount = bulkEventProducerService.produceForUser(userId);
        return ResponseEntity.accepted().body(Map.of(
                "status", "Bulk events accepted",
                "userId", userId,
                "producedCount", producedCount,
                "gapSeconds", 2
        ));
    }
}