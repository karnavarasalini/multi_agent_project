package com.example.health_management_3.service;

import com.example.health_management_3.entity.Patient;
import com.example.health_management_3.repository.PatientRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
public class PatientService {

    private final PatientRepository patientRepository;

    public PatientService(PatientRepository patientRepository) {
        this.patientRepository = patientRepository;
    }

    public List<Patient> findAll() {
        return patientRepository.findAll();
    }

    public Patient findById(Long id) {
        return patientRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Patient not found with id: " + id));
    }

    public Patient create(Patient patient) {
        return patientRepository.save(patient);
    }

    @Transactional
    public Patient update(Long id, Patient patient) {
        Patient existing = patientRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Patient not found with id: " + id));
        existing.setFirstName(patient.getFirstName());
        existing.setLastName(patient.getLastName());
        existing.setEmail(patient.getEmail());
        existing.setDateOfBirth(patient.getDateOfBirth());
        existing.setPhoneNumber(patient.getPhoneNumber());
        return existing;
    }

    public void delete(Long id) {
        if (!patientRepository.existsById(id)) {
            throw new IllegalArgumentException("Patient not found with id: " + id);
        }
        patientRepository.deleteById(id);
    }
}
