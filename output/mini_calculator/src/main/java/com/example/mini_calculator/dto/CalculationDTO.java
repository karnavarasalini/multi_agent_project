package com.example.mini_calculator.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

/**
 * Data Transfer Object for Calculation requests and responses.
 */
public class CalculationDTO {

    private Long id; // optional for response

    @NotNull(message = "Operand1 is required")
    private Double operand1;

    @NotNull(message = "Operand2 is required")
    private Double operand2;

    @NotBlank(message = "Operation is required")
    private String operation;

    private Double result; // optional for response

    public CalculationDTO() {
    }

    public CalculationDTO(Long id, Double operand1, Double operand2, String operation, Double result) {
        this.id = id;
        this.operand1 = operand1;
        this.operand2 = operand2;
        this.operation = operation;
        this.result = result;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Double getOperand1() {
        return operand1;
    }

    public void setOperand1(Double operand1) {
        this.operand1 = operand1;
    }

    public Double getOperand2() {
        return operand2;
    }

    public void setOperand2(Double operand2) {
        this.operand2 = operand2;
    }

    public String getOperation() {
        return operation;
    }

    public void setOperation(String operation) {
        this.operation = operation;
    }

    public Double getResult() {
        return result;
    }

    public void setResult(Double result) {
        this.result = result;
    }
}