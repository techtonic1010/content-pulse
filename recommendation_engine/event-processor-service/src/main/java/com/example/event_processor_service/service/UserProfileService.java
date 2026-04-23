package com.example.event_processor_service.service;

import com.example.event_processor_service.model.UserEvent;
import com.example.event_processor_service.model.UserProfile;
import com.example.event_processor_service.utils.AffinityCalculator;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

@Service
public class UserProfileService {

    private static final String PROFILE_KEY_PREFIX = "profile:";
    private static final int RECENTLY_WATCHED_LIMIT = 50;

    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;

    public UserProfileService(RedisTemplate<String, String> redisTemplate, ObjectMapper objectMapper) {
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }

    public UserProfile getProfile(String userId) {
        try {
            String key = PROFILE_KEY_PREFIX + userId;
            String json = redisTemplate.opsForValue().get(key);
            if (json == null || json.isBlank()) {
                return createDefaultProfile(userId);
            }
            return objectMapper.readValue(json, UserProfile.class);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to fetch user profile from Redis", e);
        }
    }

    public void saveProfile(UserProfile profile) {
        try {
            String key = PROFILE_KEY_PREFIX + profile.getUserId();
            String json = objectMapper.writeValueAsString(profile);
            redisTemplate.opsForValue().set(Objects.requireNonNull(key), Objects.requireNonNull(json));
        } catch (Exception e) {
            throw new IllegalStateException("Failed to save user profile to Redis", e);
        }
    }

    public UserProfile processEvent(UserEvent event, List<String> enrichedGenres) {
        UserProfile profile = getProfile(event.getUserId());

        List<String> targetGenres = (enrichedGenres == null || enrichedGenres.isEmpty())
                ? Collections.singletonList(resolveFallbackGenre(event))
                : enrichedGenres;

        profile.setGenreAffinities(
                AffinityCalculator.updateAffinities(
                        profile.getGenreAffinities(),
                        targetGenres,
                        event.getEventType(),
                        event.getCompletionRatio()
                )
        );

        profile.getRecentlyWatched().removeIf(contentId -> Objects.equals(contentId, event.getContentId()));
        profile.getRecentlyWatched().add(0, event.getContentId());
        if (profile.getRecentlyWatched().size() > RECENTLY_WATCHED_LIMIT) {
            profile.getRecentlyWatched().subList(RECENTLY_WATCHED_LIMIT, profile.getRecentlyWatched().size()).clear();
        }

        profile.setTotalWatchEvents(profile.getTotalWatchEvents() + 1);
        profile.setNewUser(false);
        profile.setLastUpdated(Instant.now().toString());

        saveProfile(profile);
        return profile;
    }

    private UserProfile createDefaultProfile(String userId) {
        UserProfile profile = new UserProfile();
        profile.setUserId(userId);
        profile.setNewUser(true);
        profile.setLastUpdated(Instant.now().toString());
        return profile;
    }

    private String resolveFallbackGenre(UserEvent event) {
        if (event.getSource() != null && !event.getSource().isBlank()) {
            return event.getSource().trim().toLowerCase();
        }
        return "general";
    }
}
