package com.example.mini_calculator.service;

import com.example.mini_calculator.entity.Calculation;
import com.example.mini_calculator.repository.CalculationRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Service
public class CalculationService {

    private final CalculationRepository calculationRepository;

    public CalculationService(CalculationRepository calculationRepository) {
        this.calculationRepository = calculationRepository;
    }

    /**
     * Creates a new calculation based on the provided operands and operator.
     * The expression is stored as a string like "5 + 3" and the result is persisted.
     *
     * @param operand1 first operand
     * @param operand2 second operand
     * @param operator one of "+", "-", "*", "/"
     * @return the persisted {@link Calculation}
     */
    @Transactional
    public Calculation createCalculation(BigDecimal operand1, BigDecimal operand2, String operator) {
        BigDecimal result = evaluate(operand1, operand2, operator);
        String expression = operand1.stripTrailingZeros().toPlainString() + " " + operator + " " + operand2.stripTrailingZeros().toPlainString();
        Calculation calculation = new Calculation();
        calculation.setExpression(expression);
        calculation.setResult(result);
        calculation.setTimestamp(LocalDateTime.now());
        return calculationRepository.save(calculation);
    }

    private BigDecimal evaluate(BigDecimal op1, BigDecimal op2, String operator) {
        return switch (operator) {
            case "+" -> op1.add(op2);
            case "-" -> op1.subtract(op2);
            case "*" -> op1.multiply(op2);
            case "/" -> {
                if (op2.compareTo(BigDecimal.ZERO) == 0) {
                    throw new IllegalArgumentException("Division by zero is not allowed");
                }
                yield op1.divide(op2, 10, BigDecimal.ROUND_HALF_UP);
            }
            default -> throw new IllegalArgumentException("Unsupported operator: " + operator);
        };
    }

    /**
     * Retrieves a calculation by its id.
     */
    @Transactional(readOnly = true)
    public Optional<Calculation> getCalculation(Long id) {
        return calculationRepository.findById(id);
    }

    /**
     * Returns all stored calculations.
     */
    @Transactional(readOnly = true)
    public List<Calculation> getAllCalculations() {
        return calculationRepository.findAll();
    }
}
