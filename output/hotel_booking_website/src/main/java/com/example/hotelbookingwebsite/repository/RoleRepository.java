package com.example.hotelbookingwebsite.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;
import com.example.hotelbookingwebsite.entity.Role;

public interface RoleRepository extends JpaRepository<Role, Long> {
    Optional<Role> findByName(String name);
}
