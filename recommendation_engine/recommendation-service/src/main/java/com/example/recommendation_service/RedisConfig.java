package com.example.recommendation_service;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.StringRedisSerializer;

@Configuration
public class RedisConfig {
    @Bean
    public RedisTemplate<String, String> redisTemplate(RedisConnectionFactory factory) {
         // create RedisTemplate (main class used to interact with Redis)
    RedisTemplate<String, String> template = new RedisTemplate<>();

    // sets the connection to Redis server (provided by Spring automatically)
    template.setConnectionFactory(factory);

    // defines how keys are stored → as plain readable strings
    template.setKeySerializer(new StringRedisSerializer());

    // defines how values are stored → as plain strings (JSON in our case)
    template.setValueSerializer(new StringRedisSerializer());

    // return configured template to Spring container
    return template;
    }
}
