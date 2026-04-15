package com.example.event_processor_service.service;

import com.example.event_processor_service.model.Content;
import com.example.event_processor_service.repository.ContentRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

@Service
public class ContentEnrichmentService {
    private static final Logger log = LoggerFactory.getLogger(ContentEnrichmentService.class);
    private static final int CACHE_TTL_HOURS = 6;

    private final ContentRepository contentRepository;
    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;

    public ContentEnrichmentService(ContentRepository contentRepository,
                                    RedisTemplate<String, String> redisTemplate,
                                    ObjectMapper objectMapper) {
        this.contentRepository = contentRepository;
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }
    public GenreLookupResult getGenresForContent(String contentId) {
        if (contentId == null || contentId.isBlank()) {
            return new GenreLookupResult(Collections.emptyList(), "NONE");
        }

        String normalizedContentId = contentId.trim();
        String cacheKey = "content:meta:" + normalizedContentId;

        List<String> cachedGenres = readGenresFromCache(cacheKey);
        if (!cachedGenres.isEmpty()) {
            return new GenreLookupResult(cachedGenres, "REDIS");
        }

        List<String> dbGenres = readGenresFromDatabase(normalizedContentId);
        if (!dbGenres.isEmpty()) {
            cacheGenres(cacheKey, dbGenres);
            return new GenreLookupResult(dbGenres, "POSTGRES");
        }

        return new GenreLookupResult(Collections.emptyList(), "NONE");
    }
    private List<String> readGenresFromCache(String cacheKey) {
        try {
            String cached = redisTemplate.opsForValue().get(Objects.requireNonNull(cacheKey));
            if (cached == null || cached.isBlank()) {
                return Collections.emptyList();
            }

            List<String> genres = objectMapper.readValue(cached, new TypeReference<List<String>>() {
            });
            return genres == null ? Collections.emptyList() : genres;
        } catch (Exception e) {
            log.warn("Redis cache read failed for key={}. Falling back to DB.", cacheKey, e);
            return Collections.emptyList();
        }
    }
    private List<String> readGenresFromDatabase(String contentId) {
        try {
            return contentRepository.findByContentId(contentId)
                    .map(Content::getGenres)
                    .orElse(Collections.emptyList());
        } catch (Exception e) {
            log.error("Database lookup failed for contentId={}", contentId, e);
            return Collections.emptyList();
        }
    }

    private void cacheGenres(String cacheKey, List<String> genres) {
        try {
            redisTemplate.opsForValue().set(
                    Objects.requireNonNull(cacheKey),
                    Objects.requireNonNull(objectMapper.writeValueAsString(genres)),
                    CACHE_TTL_HOURS,
                    TimeUnit.HOURS
            );
        } catch (Exception e) {
            log.warn("Failed to cache genres in Redis for key={}", cacheKey, e);
        }
    }

    public record GenreLookupResult(List<String> genres, String source) {
    }
}