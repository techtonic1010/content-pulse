package com.example.recommendation_service.recommendation;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "ml.fastapi")
public class MlFastApiProperties {
    private String baseUrl = "http://localhost:8090";
    private String recommendationPath = "/recommendations";
    private long timeoutMs = 3000;
    private int retryCount = 1;

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    public String getRecommendationPath() {
        return recommendationPath;
    }

    public void setRecommendationPath(String recommendationPath) {
        this.recommendationPath = recommendationPath;
    }

    public long getTimeoutMs() {
        return timeoutMs;
    }

    public void setTimeoutMs(long timeoutMs) {
        this.timeoutMs = timeoutMs;
    }

    public int getRetryCount() {
        return retryCount;
    }

    public void setRetryCount(int retryCount) {
        this.retryCount = retryCount;
    }
}
