package com.example.recommendation_service.recommendation.dto;

public class FastApiRecommendationRequest {
    private String userId;

    public FastApiRecommendationRequest() {
    }

    public FastApiRecommendationRequest(String userId) {
        this.userId = userId;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }
}
