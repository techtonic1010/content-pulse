package com.example.event_processor_service.utils;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public final class AffinityCalculator {

    private static final double MAX_AFFINITY = 1.0;
    private static final double MIN_AFFINITY = 0.0;
    private static final double DEFAULT_START_SCORE = 0.1;

    private AffinityCalculator() {
    }

    // current scores + genres + eventType + completionRatio
    public static Map<String, Double> updateAffinities(
            Map<String, Double> current,
            List<String> genres,
            String eventType,
            Double completionRatio) {

        Map<String, Double> base = current == null ? Collections.emptyMap() : current;
        // 👉 If current is null → use empty map
        // 👉 avoids null errors
        // 👉 Same for genres → ensure safe list
        List<String> targetGenres = genres == null ? Collections.emptyList() : genres;
        // 👉 Copy current scores → so original is not modified
        Map<String, Double> updated = new HashMap<>(base);
        // Compute score change based on event type and completion ratio
        double delta = calculateDelta(eventType, completionRatio);
        // Handle nulls (safe defaults)
        // Copy current map → updated
        // Compute delta (impact of event)
        // For each genre:
        // normalize (lowercase)
        // get current score (default 0.1)
        // add delta
        // clamp (0 to 1)
        // store back in updated   
        for (String genre : targetGenres) {
            if (genre == null || genre.isBlank()) {
                continue;
            }

            String normalizedGenre = genre.trim().toLowerCase(Locale.ROOT);
            double currentScore = updated.getOrDefault(normalizedGenre, DEFAULT_START_SCORE);

            double newScore = clamp(currentScore + delta);

            updated.put(normalizedGenre, newScore);
        }

        return updated;
    }

    private static double calculateDelta(String eventType, Double ratio) {
        String type = eventType == null ? "" : eventType.trim().toUpperCase(Locale.ROOT);
        double safeRatio = ratio == null ? 0.0 : Math.max(0.0, Math.min(1.0, ratio));

        return switch (type) {

            case "PLAY" -> {
                if (safeRatio > 0.7) {
                    yield 0.05 * safeRatio;
                }
                if (safeRatio > 0.3) {
                    yield 0.01;
                }
                yield -0.03;
            }

            case "LIKE" -> 0.08;
            case "DISLIKE" -> -0.10;
            case "SKIP" -> -0.02;

            default -> 0.0;
        };
    }

    private static double clamp(double value) {
        return Math.min(MAX_AFFINITY, Math.max(MIN_AFFINITY, value));
    }
}

// ==> This class calculates and updates genre affinity scores based on user events. 
// It takes current affinities, event genres, event type, and completion ratio to compute 
// new scores. The logic includes normalization, safe handling of nulls, and clamping scores 
// between 0 and 1.
// ABOUT => for (String genre : targetGenres) 
// 👉 Short + clear 👇

// for (String genre : targetGenres)

// 👉 Loop over each genre

// if (genre == null || genre.isBlank()) continue;

// 👉 Skip invalid values

// String normalizedGenre = genre.trim().toLowerCase(...)

// 👉 Clean + standardize (avoid duplicates like "Crime" vs "crime")

// double currentScore = updated.getOrDefault(..., 0.1);

// 👉 Get current score (default = 0.1 if new)

// double newScore = clamp(currentScore + delta);

// 👉 Update score safely (0 → 1 range)

// updated.put(normalizedGenre, newScore);

// 👉 Save updated value