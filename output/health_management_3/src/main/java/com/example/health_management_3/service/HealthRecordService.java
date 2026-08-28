package com.example.health_management_3.service;

import com.example.health_management_3.entity.HealthRecord;
import com.example.health_management_3.repository.HealthRecordRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import java.util.List;

@Service
public class HealthRecordService {

    private final HealthRecordRepository healthRecordRepository;

    @Autowired
    public HealthRecordService(HealthRecordRepository healthRecordRepository) {
        this.healthRecordRepository = healthRecordRepository;
    }

    public List<HealthRecord> getAll() {
        return healthRecordRepository.findAll();
    }

    public HealthRecord getById(Long id) {
        return healthRecordRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "HealthRecord not found"));
    }

    public HealthRecord create(HealthRecord healthRecord) {
        return healthRecordRepository.save(healthRecord);
    }

    @Transactional
    public HealthRecord update(Long id, HealthRecord updatedRecord) {
        HealthRecord existingRecord = getById(id);
        existingRecord.setPatientId(updatedRecord.getPatientId());
        existingRecord.setRecordDate(updatedRecord.getRecordDate());
        existingRecord.setType(updatedRecord.getType());
        existingRecord.setDescription(updatedRecord.getDescription());
        return healthRecordRepository.save(existingRecord);
    }

    @Transactional
    public void delete(Long id) {
        HealthRecord existingRecord = getById(id);
        healthRecordRepository.delete(existingRecord);
    }
}
