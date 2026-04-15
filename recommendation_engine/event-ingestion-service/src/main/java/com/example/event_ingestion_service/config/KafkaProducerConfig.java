package com.example.event_ingestion_service.config;

import com.example.event_ingestion_service.model.UserEvent;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;
import org.springframework.kafka.support.serializer.JsonSerializer;

import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

@Configuration
public class KafkaProducerConfig {

    @Bean
    public ProducerFactory<String, UserEvent> producerFactory(
            @Value("${spring.kafka.bootstrap-servers}") String bootstrapServers
    ) {
        Map<String, Object> props = new HashMap<>();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, JsonSerializer.class);
        return new DefaultKafkaProducerFactory<>(props);
    }

    @Bean
    public KafkaTemplate<String, UserEvent> kafkaTemplate(ProducerFactory<String, UserEvent> producerFactory) {
        return new KafkaTemplate<>(Objects.requireNonNull(producerFactory));
    }
}
// ProducerFactory → creates Kafka producers
// KafkaTemplate → uses those producers to send messages
// ⚙️ What ProducerFactory does

// 👉 It defines:

// which Kafka server
// how to serialize key
// how to serialize value (JSON)
// props.put(BOOTSTRAP_SERVERS_CONFIG, ...)
// props.put(KEY_SERIALIZER_CLASS_CONFIG, ...)
// props.put(VALUE_SERIALIZER_CLASS_CONFIG, ...)

// 👉 Basically:

// “How should messages be built and sent?”