package com.example.recommendation_service.recommendation;

import com.example.recommendation_service.recommendation.dto.RecommendationResponseDto;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class RecommendationBridgeService {
    private static final Logger log = LoggerFactory.getLogger(RecommendationBridgeService.class);

    private final MlFastApiClient fastApiClient;

    public RecommendationBridgeService(MlFastApiClient fastApiClient) {
        this.fastApiClient = fastApiClient;
    }

    public RecommendationResponseDto getRecommendations(String userId) {
        try {
            RecommendationResponseDto response = fastApiClient.fetchRecommendations(userId);
            if (response == null || response.getUserId() == null) {
                log.warn("FastAPI returned null/malformed recommendation payload for userId={}", userId);
                return RecommendationResponseDto.fallback(userId);
            }
            if (response.getMeta() == null) {
                response.setMeta(RecommendationResponseDto.fallback(userId).getMeta());
            }
            return response;
        } catch (Exception ex) {
            log.warn("Recommendation bridge fallback for userId={} due to error={}", userId, ex.getMessage());
            return RecommendationResponseDto.fallback(userId);
        }
    }
}
