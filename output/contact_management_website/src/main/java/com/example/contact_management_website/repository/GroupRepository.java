package com.example.contact_management_website.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import com.example.contact_management_website.entity.Group;

@Repository
public interface GroupRepository extends JpaRepository<Group, Long> {
    // Additional query methods can be defined here
}
