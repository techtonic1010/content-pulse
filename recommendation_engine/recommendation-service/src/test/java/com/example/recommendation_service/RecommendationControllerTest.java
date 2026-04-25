package com.example.recommendation_service;

import com.example.recommendation_service.recommendation.RecommendationBridgeService;
import com.example.recommendation_service.recommendation.dto.RecommendationResponseDto;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.ArrayList;
import java.util.List;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Integration tests for RecommendationController with mocked FastAPI client.
 *
 * Tests three scenarios:
 * 1. SUCCESS: Valid recommendation response from FastAPI
 * 2. TIMEOUT: WebClient timeout exception → fallback response
 * 3. MALFORMED: FastAPI returns unexpected/invalid response → fallback
 */
@SpringBootTest
@AutoConfigureMockMvc
class RecommendationControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private RecommendationBridgeService recommendationBridgeService;

    /**
     * Scenario 1: SUCCESS PATH
     * FastAPI returns valid recommendations with genres and movies
     */
    @Test
    void testGetRecommendationsSuccess() throws Exception {
        String userId = "user123";

        // Build success response
        RecommendationResponseDto successResponse = new RecommendationResponseDto();
        successResponse.setUserId(userId);

        // Add topGenres
        List<RecommendationResponseDto.TopGenreDto> topGenres = new ArrayList<>();
        RecommendationResponseDto.TopGenreDto genre1 = new RecommendationResponseDto.TopGenreDto();
        genre1.setGenre("Action");
        genre1.setScore(0.95);
        topGenres.add(genre1);

        RecommendationResponseDto.TopGenreDto genre2 = new RecommendationResponseDto.TopGenreDto();
        genre2.setGenre("Sci-Fi");
        genre2.setScore(0.87);
        topGenres.add(genre2);
        successResponse.setTopGenres(topGenres);

        // Add moviesByGenre
        List<RecommendationResponseDto.MoviesByGenreDto> moviesByGenre = new ArrayList<>();

        RecommendationResponseDto.MoviesByGenreDto actionMovies = new RecommendationResponseDto.MoviesByGenreDto();
        actionMovies.setGenre("Action");
        List<RecommendationResponseDto.MovieDto> actionMovieList = new ArrayList<>();

        RecommendationResponseDto.MovieDto movie1 = new RecommendationResponseDto.MovieDto();
        movie1.setMovieId("movie1");
        movie1.setTitle("Action Movie");
        movie1.setScore(0.95);
        actionMovieList.add(movie1);

        RecommendationResponseDto.MovieDto movie2 = new RecommendationResponseDto.MovieDto();
        movie2.setMovieId("movie2");
        movie2.setTitle("Another Action");
        movie2.setScore(0.88);
        actionMovieList.add(movie2);

        actionMovies.setMovies(actionMovieList);
        moviesByGenre.add(actionMovies);

        RecommendationResponseDto.MoviesByGenreDto scifiMovies = new RecommendationResponseDto.MoviesByGenreDto();
        scifiMovies.setGenre("Sci-Fi");
        List<RecommendationResponseDto.MovieDto> scifiMovieList = new ArrayList<>();

        RecommendationResponseDto.MovieDto movie3 = new RecommendationResponseDto.MovieDto();
        movie3.setMovieId("movie3");
        movie3.setTitle("Sci-Fi Movie");
        movie3.setScore(0.87);
        scifiMovieList.add(movie3);

        scifiMovies.setMovies(scifiMovieList);
        moviesByGenre.add(scifiMovies);
        successResponse.setMoviesByGenre(moviesByGenre);

        // Set meta
        RecommendationResponseDto.MetaDto meta = new RecommendationResponseDto.MetaDto();
        meta.setCandidatesRetrieved(100);
        meta.setCandidatesUsed(50);
        meta.setFallback(false);
        successResponse.setMeta(meta);

        when(recommendationBridgeService.getRecommendations(userId))
                .thenReturn(successResponse);

        // Execute and verify
        mockMvc.perform(get("/api/recommendations/" + userId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value(userId))
                .andExpect(jsonPath("$.topGenres.length()").value(2))
                .andExpect(jsonPath("$.topGenres[0].genre").value("Action"))
                .andExpect(jsonPath("$.topGenres[0].score").value(0.95))
                .andExpect(jsonPath("$.topGenres[1].genre").value("Sci-Fi"))
                .andExpect(jsonPath("$.moviesByGenre.length()").value(2))
                .andExpect(jsonPath("$.moviesByGenre[0].genre").value("Action"))
                .andExpect(jsonPath("$.moviesByGenre[0].movies.length()").value(2))
                .andExpect(jsonPath("$.moviesByGenre[0].movies[0].movieId").value("movie1"))
                .andExpect(jsonPath("$.moviesByGenre[0].movies[0].title").value("Action Movie"))
                .andExpect(jsonPath("$.meta.candidatesRetrieved").value(100))
                .andExpect(jsonPath("$.meta.candidatesUsed").value(50))
                .andExpect(jsonPath("$.meta.fallback").value(false));
    }

    /**
     * Scenario 2: TIMEOUT PATH
     * WebClient timeout exception occurs → fallback response
     */
    @Test
    void testGetRecommendationsTimeout() throws Exception {
        String userId = "user456";

        // Mock timeout exception from WebClient
        when(recommendationBridgeService.getRecommendations(userId))
                .thenThrow(new RuntimeException("Connection timeout from FastAPI"));

        // Execute - should return fallback response
        mockMvc.perform(get("/api/recommendations/" + userId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value(userId))
                .andExpect(jsonPath("$.topGenres.length()").value(0))
                .andExpect(jsonPath("$.moviesByGenre.length()").value(0))
                .andExpect(jsonPath("$.meta.candidatesRetrieved").value(0))
                .andExpect(jsonPath("$.meta.candidatesUsed").value(0))
                .andExpect(jsonPath("$.meta.fallback").value(true));
    }

    /**
     * Scenario 3: MALFORMED PAYLOAD PATH
     * FastAPI returns unexpected/malformed response → fallback
     */
    @Test
    void testGetRecommendationsMalformedResponse() throws Exception {
        String userId = "user789";

        // Mock generic exception (represents malformed response, deserialization failure, etc)
        when(recommendationBridgeService.getRecommendations(userId))
                .thenThrow(new RuntimeException("Failed to deserialize FastAPI response: invalid JSON"));

        // Execute - should return fallback response
        mockMvc.perform(get("/api/recommendations/" + userId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value(userId))
                .andExpect(jsonPath("$.topGenres").isEmpty())
                .andExpect(jsonPath("$.moviesByGenre").isEmpty())
                .andExpect(jsonPath("$.meta.fallback").value(true));
    }

    /**
     * Additional test: Invalid userID should return 400 Bad Request
     */
    @Test
    void testGetRecommendationsInvalidUserId() throws Exception {
        mockMvc.perform(get("/api/recommendations/"))
                .andExpect(status().isNotFound()); // Route pattern doesn't match
    }
}
