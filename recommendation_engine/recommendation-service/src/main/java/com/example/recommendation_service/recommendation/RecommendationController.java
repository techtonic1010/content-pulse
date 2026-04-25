package com.example.recommendation_service.recommendation;

import com.example.recommendation_service.recommendation.dto.RecommendationResponseDto;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/recommendations")
public class RecommendationController {
    private final RecommendationBridgeService recommendationBridgeService;

    public RecommendationController(RecommendationBridgeService recommendationBridgeService) {
        this.recommendationBridgeService = recommendationBridgeService;
    }

    @GetMapping("/{userId}")
    public ResponseEntity<RecommendationResponseDto> getRecommendations(@PathVariable String userId) {
        if (userId == null || userId.trim().isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "userId must not be empty");
        }

        try {
            RecommendationResponseDto response = recommendationBridgeService.getRecommendations(userId.trim());
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            // Return fallback response on any error (timeout, malformed response, etc)
            RecommendationResponseDto fallback = RecommendationResponseDto.fallback(userId.trim());
            return ResponseEntity.ok(fallback);
        }
    }
}
