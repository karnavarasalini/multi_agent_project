package com.example.hotelbookingwebsite.controller;

import com.example.hotelbookingwebsite.entity.Payment;
import com.example.hotelbookingwebsite.service.StripePaymentService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import javax.validation.constraints.NotNull;
import java.math.BigDecimal;

@RestController
@RequestMapping("/api/payments")
@Validated
public class PaymentController {

    private final StripePaymentService stripePaymentService;

    public PaymentController(StripePaymentService stripePaymentService) {
        this.stripePaymentService = stripePaymentService;
    }

    @PostMapping
    public ResponseEntity<PaymentResponse> processPayment(@RequestBody @Valid PaymentRequest request) {
        Payment payment = stripePaymentService.processPayment(request.getBookingId(), request.getStripeToken());
        PaymentResponse response = new PaymentResponse(
                payment.getId(),
                payment.getStatus().name(),
                payment.getAmount()
        );
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    public static class PaymentRequest {

        @NotNull
        private Long bookingId;

        @NotNull
        private String stripeToken;

        public Long getBookingId() {
            return bookingId;
        }

        public void setBookingId(Long bookingId) {
            this.bookingId = bookingId;
        }

        public String getStripeToken() {
            return stripeToken;
        }

        public void setStripeToken(String stripeToken) {
            this.stripeToken = stripeToken;
        }
    }

    public static class PaymentResponse {

        private Long paymentId;
        private String status;
        private BigDecimal amount;

        public PaymentResponse(Long paymentId, String status, BigDecimal amount) {
            this.paymentId = paymentId;
            this.status = status;
            this.amount = amount;
        }

        public Long getPaymentId() {
            return paymentId;
        }

        public void setPaymentId(Long paymentId) {
            this.paymentId = paymentId;
        }

        public String getStatus() {
            return status;
        }

        public void setStatus(String status) {
            this.status = status;
        }

        public BigDecimal getAmount() {
            return amount;
        }

        public void setAmount(BigDecimal amount) {
            this.amount = amount;
        }
    }
}
