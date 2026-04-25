package com.example.recommendation_service.recommendation;

import com.example.recommendation_service.recommendation.dto.FastApiRecommendationRequest;
import com.example.recommendation_service.recommendation.dto.RecommendationResponseDto;
import java.time.Duration;
import java.util.Objects;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

@Component
public class MlFastApiClient {
    private static final Logger log = LoggerFactory.getLogger(MlFastApiClient.class);

    private final WebClient webClient;
    private final MlFastApiProperties properties;

    public MlFastApiClient(WebClient webClient, MlFastApiProperties properties) {
        this.webClient = webClient;
        this.properties = properties;
    }

    public RecommendationResponseDto fetchRecommendations(String userId) {
        FastApiRecommendationRequest request = new FastApiRecommendationRequest(userId);
        String recommendationPath = Objects.requireNonNull(
            properties.getRecommendationPath(),
            "ml.fastapi.recommendation-path must not be null"
        );
        int maxAttempts = Math.max(1, properties.getRetryCount() + 1);

        RuntimeException lastFailure = null;
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                return webClient.post()
                    .uri(recommendationPath)
                    .bodyValue(request)
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, response ->
                        response.bodyToMono(String.class).map(body ->
                            new IllegalStateException("FastAPI error: status=" + response.statusCode() + ", body=" + body)
                        )
                    )
                    .bodyToMono(RecommendationResponseDto.class)
                    .block(Duration.ofMillis(Math.max(1, properties.getTimeoutMs())));
            } catch (WebClientResponseException ex) {
                lastFailure = ex;
                log.warn("FastAPI responded with non-2xx on attempt {}/{}: status={}, body={}",
                    attempt, maxAttempts, ex.getStatusCode(), ex.getResponseBodyAsString());
            } catch (RuntimeException ex) {
                lastFailure = ex;
                log.warn("FastAPI request failed on attempt {}/{}: {}", attempt, maxAttempts, ex.getMessage());
            }
        }

        throw new IllegalStateException("FastAPI recommendation request failed after retries", lastFailure);
    }
}
