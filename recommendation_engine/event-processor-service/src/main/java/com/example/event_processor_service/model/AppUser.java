package com.example.event_processor_service.model;
import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;


@Entity
@Table(name = "users")
@Data
@NoArgsConstructor
public class AppUser {

    @Id
    private String userId;

    private String username;
    private String email;
    private String region;
    private String ageGroup;
}