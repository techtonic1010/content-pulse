package com.example.event_processor_service.repository;
import org.springframework.data.jpa.repository.JpaRepository;

import com.example.event_processor_service.model.AppUser;

public interface UserRepository extends JpaRepository<AppUser, String> {
}
