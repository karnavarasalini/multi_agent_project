package com.example.health_management_3.controller;

import com.example.health_management_3.dto.HealthRecordDto;
import com.example.health_management_3.entity.HealthRecord;
import com.example.health_management_3.service.HealthRecordService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/healthrecords")
public class HealthRecordController {

    private final HealthRecordService healthRecordService;

    public HealthRecordController(HealthRecordService healthRecordService) {
        this.healthRecordService = healthRecordService;
    }

    @GetMapping
    public ResponseEntity<List<HealthRecord>> getAll() {
        return ResponseEntity.ok(healthRecordService.findAll());
    }

    @PostMapping
    public ResponseEntity<HealthRecord> create(@RequestBody @Valid HealthRecordDto dto) {
        HealthRecord created = healthRecordService.create(dto);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @GetMapping("/{id}")
    public ResponseEntity<HealthRecord> getById(@PathVariable Long id) {
        return ResponseEntity.ok(healthRecordService.findById(id));
    }

    @PutMapping("/{id}")
    public ResponseEntity<HealthRecord> update(@PathVariable Long id, @RequestBody @Valid HealthRecordDto dto) {
        HealthRecord updated = healthRecordService.update(id, dto);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        healthRecordService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
