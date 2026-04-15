package com.example.event_processor_service.model;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.util.Map;
import java.util.HashMap;
import java.util.List;
import java.util.ArrayList;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserProfile {

    private String userId;

    private Map<String, Double> genreAffinities = new HashMap<>();

    private List<String> recentlyWatched = new ArrayList<>();

    private int totalWatchEvents = 0;

    private boolean isNewUser = true;

    private String lastUpdated;
}
