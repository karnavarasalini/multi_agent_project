package com.example.mini_calculator.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import com.example.mini_calculator.entity.Calculation;

import java.util.Optional;

@Repository
public interface CalculationRepository extends JpaRepository<Calculation, Long> {
    Optional<Calculation> findById(Long id);
}
