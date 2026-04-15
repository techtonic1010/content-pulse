package com.example.event_processor_service.repository;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;
import com.example.event_processor_service.model.Content;   

public interface ContentRepository extends JpaRepository<Content, String> {

    List<Content> findTop20ByOrderByReleaseYearDesc();

    List<Content> findByContentIdIn(List<String> contentIds);

    Optional<Content> findByContentId(String contentId);
}