package com.example.hotelbookingwebsite.service;

import com.example.hotelbookingwebsite.entity.Booking;
import com.example.hotelbookingwebsite.entity.Payment;
import com.example.hotelbookingwebsite.repository.BookingRepository;
import com.example.hotelbookingwebsite.repository.PaymentRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.sql.Timestamp;
import java.util.HashMap;
import java.util.Map;

@Service
public class PaymentServiceImpl {

    private final PaymentRepository paymentRepository;
    private final BookingRepository bookingRepository;
    private final RestTemplate restTemplate;
    private final String paymentGatewayUrl;

    public PaymentServiceImpl(PaymentRepository paymentRepository,
                              BookingRepository bookingRepository,
                              RestTemplate restTemplate,
                              @Value("${payment.gateway.url}") String paymentGatewayUrl) {
        this.paymentRepository = paymentRepository;
        this.bookingRepository = bookingRepository;
        this.restTemplate = restTemplate;
        this.paymentGatewayUrl = paymentGatewayUrl;
    }

    @Transactional
    public Payment processPayment(Long bookingId, BigDecimal amount) {
        Booking booking = bookingRepository.findById(bookingId)
                .orElseThrow(() -> new IllegalArgumentException("Booking not found with id: " + bookingId));

        // Prepare request payload for external payment gateway
        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("bookingId", bookingId);
        requestBody.put("amount", amount);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> requestEntity = new HttpEntity<>(requestBody, headers);

        // Call external payment gateway
        ResponseEntity<Map> response = restTemplate.postForEntity(paymentGatewayUrl, requestEntity, Map.class);
        if (!response.getStatusCode().is2xxSuccessful() || response.getBody() == null) {
            throw new RuntimeException("Failed to process payment with external gateway");
        }
        Map<String, Object> responseBody = response.getBody();
        String transactionId = (String) responseBody.get("transactionId");
        String status = (String) responseBody.getOrDefault("status", "FAILED");

        // Persist payment record
        Payment payment = new Payment();
        payment.setBooking(booking);
        payment.setAmount(amount);
        payment.setTransactionId(transactionId);
        payment.setStatus(status);
        payment.setPaidAt(new Timestamp(System.currentTimeMillis()));

        return paymentRepository.save(payment);
    }
}
