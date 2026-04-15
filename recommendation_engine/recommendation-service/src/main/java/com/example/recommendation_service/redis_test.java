package com.example.recommendation_service;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class redis_test {
	private final StringRedisTemplate redisTemplate;
	public redis_test(StringRedisTemplate redisTemplate) {
		this.redisTemplate = redisTemplate;
	}
	@GetMapping("/test/redis")
	public String redisRoundTrip() {

        System.out.println("HIT");
		redisTemplate.opsForValue().set("test:ping", "pong");
		return redisTemplate.opsForValue().get("test:ping");
	}
}
