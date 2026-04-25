package com.example.recommendation_service.recommendation.dto;

import java.util.ArrayList;
import java.util.List;

public class RecommendationResponseDto {
    private String userId;
    private List<TopGenreDto> topGenres = new ArrayList<>();
    private List<MoviesByGenreDto> moviesByGenre = new ArrayList<>();
    private MetaDto meta = new MetaDto();

    public static RecommendationResponseDto fallback(String userId) {
        RecommendationResponseDto response = new RecommendationResponseDto();
        response.setUserId(userId);
        response.setTopGenres(new ArrayList<>());
        response.setMoviesByGenre(new ArrayList<>());

        MetaDto fallbackMeta = new MetaDto();
        fallbackMeta.setCandidatesRetrieved(0);
        fallbackMeta.setCandidatesUsed(0);
        fallbackMeta.setFallback(true);
        response.setMeta(fallbackMeta);

        return response;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public List<TopGenreDto> getTopGenres() {
        return topGenres;
    }

    public void setTopGenres(List<TopGenreDto> topGenres) {
        this.topGenres = topGenres;
    }

    public List<MoviesByGenreDto> getMoviesByGenre() {
        return moviesByGenre;
    }

    public void setMoviesByGenre(List<MoviesByGenreDto> moviesByGenre) {
        this.moviesByGenre = moviesByGenre;
    }

    public MetaDto getMeta() {
        return meta;
    }

    public void setMeta(MetaDto meta) {
        this.meta = meta;
    }

    public static class TopGenreDto {
        private String genre;
        private double score;
        private String reason;

        public String getGenre() {
            return genre;
        }

        public void setGenre(String genre) {
            this.genre = genre;
        }

        public double getScore() {
            return score;
        }

        public void setScore(double score) {
            this.score = score;
        }

        public String getReason() {
            return reason;
        }

        public void setReason(String reason) {
            this.reason = reason;
        }
    }

    public static class MoviesByGenreDto {
        private String genre;
        private List<MovieDto> movies = new ArrayList<>();

        public String getGenre() {
            return genre;
        }

        public void setGenre(String genre) {
            this.genre = genre;
        }

        public List<MovieDto> getMovies() {
            return movies;
        }

        public void setMovies(List<MovieDto> movies) {
            this.movies = movies;
        }
    }

    public static class MovieDto {
        private String movieId;
        private String title;
        private double score;
        private Integer year;

        public String getMovieId() {
            return movieId;
        }

        public void setMovieId(String movieId) {
            this.movieId = movieId;
        }

        public String getTitle() {
            return title;
        }

        public void setTitle(String title) {
            this.title = title;
        }

        public double getScore() {
            return score;
        }

        public void setScore(double score) {
            this.score = score;
        }

        public Integer getYear() {
            return year;
        }

        public void setYear(Integer year) {
            this.year = year;
        }
    }

    public static class MetaDto {
        private int candidatesRetrieved;
        private int candidatesUsed;
        private boolean isFallback;

        public int getCandidatesRetrieved() {
            return candidatesRetrieved;
        }

        public void setCandidatesRetrieved(int candidatesRetrieved) {
            this.candidatesRetrieved = candidatesRetrieved;
        }

        public int getCandidatesUsed() {
            return candidatesUsed;
        }

        public void setCandidatesUsed(int candidatesUsed) {
            this.candidatesUsed = candidatesUsed;
        }

        public boolean isFallback() {
            return isFallback;
        }

        public void setFallback(boolean fallback) {
            isFallback = fallback;
        }
    }
}
