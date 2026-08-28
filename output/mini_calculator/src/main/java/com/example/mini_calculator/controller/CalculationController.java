package com.example.mini_calculator.controller;

import com.example.mini_calculator.dto.CalculationDto;
import com.example.mini_calculator.entity.Calculation;
import com.example.mini_calculator.service.CalculationService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/calculations")
public class CalculationController {

    private final CalculationService calculationService;

    public CalculationController(CalculationService calculationService) {
        this.calculationService = calculationService;
    }

    @PostMapping
    public ResponseEntity<Calculation> createCalculation(@RequestBody @Valid CalculationDto dto) {
        Calculation created = calculationService.createCalculation(dto);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Calculation> getCalculation(@PathVariable Long id) {
        Calculation calc = calculationService.getCalculationById(id);
        return ResponseEntity.ok(calc);
    }

    @GetMapping
    public ResponseEntity<List<Calculation>> getAllCalculations() {
        List<Calculation> list = calculationService.getAllCalculations();
        return ResponseEntity.ok(list);
    }
}
