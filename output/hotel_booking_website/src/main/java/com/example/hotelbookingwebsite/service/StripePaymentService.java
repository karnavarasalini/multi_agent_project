package com.example.hotelbookingwebsite.service;

import com.example.hotelbookingwebsite.entity.Booking;
import com.example.hotelbookingwebsite.entity.Payment;
import com.example.hotelbookingwebsite.entity.PaymentStatus;
import com.example.hotelbookingwebsite.repository.BookingRepository;
import com.example.hotelbookingwebsite.repository.PaymentRepository;
import com.stripe.Stripe;
import com.stripe.exception.StripeException;
import com.stripe.model.PaymentIntent;
import com.stripe.param.PaymentIntentCreateParams;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import jakarta.annotation.PostConstruct;
import jakarta.transaction.Transactional;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;

@Service
public class StripePaymentService {

    private final PaymentRepository paymentRepository;
    private final BookingRepository bookingRepository;

    @Value("${stripe.api.key}")
    private String stripeApiKey;

    public StripePaymentService(PaymentRepository paymentRepository, BookingRepository bookingRepository) {
        this.paymentRepository = paymentRepository;
        this.bookingRepository = bookingRepository;
    }

    @PostConstruct
    public void init() {
        Stripe.apiKey = stripeApiKey;
    }

    @Transactional
    public String createPaymentIntent(Long bookingId) {
        Booking booking = bookingRepository.findById(bookingId)
                .orElseThrow(() -> new IllegalArgumentException("Booking not found"));
        long amountInCents = booking.getTotalPrice()
                .multiply(BigDecimal.valueOf(100))
                .longValue();
        PaymentIntentCreateParams params = PaymentIntentCreateParams.builder()
                .setAmount(amountInCents)
                .setCurrency("usd")
                .putMetadata("booking_id", bookingId.toString())
                .build();
        try {
            PaymentIntent intent = PaymentIntent.create(params);
            Payment payment = new Payment();
            payment.setBooking(booking);
            payment.setStripeChargeId(intent.getId());
            payment.setAmount(booking.getTotalPrice());
            payment.setStatus(PaymentStatus.PENDING);
            payment.setTimestamp(Instant.now());
            paymentRepository.save(payment);
            return intent.getClientSecret();
        } catch (StripeException e) {
            throw new RuntimeException("Failed to create Stripe PaymentIntent", e);
        }
    }

    @Transactional
    public Payment confirmPayment(String paymentIntentId) {
        try {
            PaymentIntent intent = PaymentIntent.retrieve(paymentIntentId);
            Payment payment = paymentRepository.findByStripeChargeId(paymentIntentId)
                    .orElseThrow(() -> new IllegalArgumentException("Payment not found"));
            if ("succeeded".equals(intent.getStatus())) {
                payment.setStatus(PaymentStatus.COMPLETED);
            } else {
                payment.setStatus(PaymentStatus.FAILED);
            }
            paymentRepository.save(payment);
            return payment;
        } catch (StripeException e) {
            throw new RuntimeException("Failed to confirm Stripe PaymentIntent", e);
        }
    }
}
