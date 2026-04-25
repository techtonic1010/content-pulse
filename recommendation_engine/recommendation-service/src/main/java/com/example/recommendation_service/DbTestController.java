package com.example.recommendation_service;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

// DISABLED: Requires JdbcTemplate which needs DB connection
// This is a test controller only, not needed for recommendation service
//
// @RestController
// public class DbTestController {
//
//     private final JdbcTemplate jdbcTemplate;
//
//     public DbTestController(JdbcTemplate jdbcTemplate) {
//         this.jdbcTemplate = jdbcTemplate;
//     }
//
//     @GetMapping("/test/db")
//     public String testDb() {
//         Integer result = jdbcTemplate.queryForObject("SELECT 1", Integer.class);
//         return (result != null && result == 1) ? "connected" : "failed";
//     }
// }
//
public class DbTestController {
}