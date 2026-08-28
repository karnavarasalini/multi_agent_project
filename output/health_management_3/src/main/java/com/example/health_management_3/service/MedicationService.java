package com.example.health_management_3.service;

import com.example.health_management_3.entity.Medication;
import com.example.health_management_3.repository.MedicationRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class MedicationService {

    private final MedicationRepository medicationRepository;

    public MedicationService(MedicationRepository medicationRepository) {
        this.medicationRepository = medicationRepository;
    }

    public List<Medication> findAll() {
        return medicationRepository.findAll();
    }

    public Medication getById(Long id) {
        return medicationRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Medication not found with id " + id));
    }

    public Medication create(Medication medication) {
        return medicationRepository.save(medication);
    }

    @Transactional
    public Medication update(Long id, Medication medication) {
        Medication existing = medicationRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Medication not found with id " + id));
        existing.setPatientId(medication.getPatientId());
        existing.setName(medication.getName());
        existing.setDosage(medication.getDosage());
        existing.setFrequency(medication.getFrequency());
        existing.setStartDate(medication.getStartDate());
        existing.setEndDate(medication.getEndDate());
        return existing;
    }

    public void delete(Long id) {
        if (!medicationRepository.existsById(id)) {
            throw new IllegalArgumentException("Medication not found with id " + id);
        }
        medicationRepository.deleteById(id);
    }
}
