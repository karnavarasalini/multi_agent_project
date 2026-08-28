package com.example.health_management_3.controller;

import com.example.health_management_3.entity.Medication;
import com.example.health_management_3.service.MedicationService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/medications")
@Validated
public class MedicationController {

    private final MedicationService medicationService;

    public MedicationController(MedicationService medicationService) {
        this.medicationService = medicationService;
    }

    @GetMapping
    public ResponseEntity<List<Medication>> getAllMedications() {
        List<Medication> medications = medicationService.getAllMedications();
        return ResponseEntity.ok(medications);
    }

    @PostMapping
    public ResponseEntity<Medication> createMedication(@RequestBody @Valid Medication medication) {
        Medication created = medicationService.createMedication(medication);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Medication> getMedicationById(@PathVariable Long id) {
        Medication medication = medicationService.getMedicationById(id);
        return ResponseEntity.ok(medication);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Medication> updateMedication(@PathVariable Long id,
                                                         @RequestBody @Valid Medication medication) {
        Medication updated = medicationService.updateMedication(id, medication);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteMedication(@PathVariable Long id) {
        medicationService.deleteMedication(id);
        return ResponseEntity.noContent().build();
    }
}
