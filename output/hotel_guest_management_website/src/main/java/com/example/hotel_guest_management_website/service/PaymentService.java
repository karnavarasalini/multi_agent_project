package com.example.hotel_guest_management_website.service;

import com.example.hotel_guest_management_website.entity.Payment;
import com.example.hotel_guest_management_website.repository.PaymentRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
import java.util.Optional;

@Service
public class PaymentService {

    private final PaymentRepository paymentRepository;

    public PaymentService(PaymentRepository paymentRepository) {
        this.paymentRepository = paymentRepository;
    }

    @Transactional(readOnly = true)
    public List<Payment> getAllPayments() {
        return paymentRepository.findAll();
    }

    @Transactional(readOnly = true)
    public Payment getPaymentById(Long id) {
        Optional<Payment> optional = paymentRepository.findById(id);
        return optional.orElseThrow(() -> new RuntimeException("Payment not found with id " + id));
    }

    @Transactional
    public Payment createPayment(Payment payment) {
        // Additional business logic such as validation can be added here
        return paymentRepository.save(payment);
    }

    @Transactional
    public Payment updatePayment(Long id, Payment updatedPayment) {
        Payment existing = getPaymentById(id);
        existing.setReservation(updatedPayment.getReservation());
        existing.setPaymentMethod(updatedPayment.getPaymentMethod());
        existing.setTransactionId(updatedPayment.getTransactionId());
        existing.setAmount(updatedPayment.getAmount());
        existing.setPaymentDate(updatedPayment.getPaymentDate());
        return paymentRepository.save(existing);
    }

    @Transactional
    public void deletePayment(Long id) {
        Payment existing = getPaymentById(id);
        paymentRepository.delete(existing);
    }
}
