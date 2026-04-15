package com.example.event_processor_service.model;
import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.ArrayList; 
@Entity
@Table(name = "content")
@Data
@NoArgsConstructor
public class Content {

    @Id
    private String contentId;

    private String title;
    private String description;
    private Integer durationMins;
    private Integer releaseYear;
    private String language;
    private String contentType;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "content_genres",
            joinColumns = @JoinColumn(name = "content_id"))
    @Column(name = "genre")
    private List<String> genres = new ArrayList<>();
}
