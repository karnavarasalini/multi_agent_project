package com.example.contact_management_website.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "contacts")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Contact {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long userId;

    private String firstName;

    private String lastName;

    private String email;

    private String phone;

    private String company;

    private String tags;

    private Long groupId;

    @CreationTimestamp
    private LocalDateTime createdAt;
}