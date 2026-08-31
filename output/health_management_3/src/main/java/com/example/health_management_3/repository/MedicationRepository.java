package com.example.health_management_3.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import com.example.health_management_3.entity.Medication;

@Repository
public interface MedicationRepository extends JpaRepository<Medication, Long> {
}
