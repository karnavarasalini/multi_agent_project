package com.example.hospital_billing_website.entity;

import jakarta.persistence.*;
import java.time.LocalDate;

@Entity
@Table(name = "insurance_claims")
public class InsuranceClaim {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "invoice_id", nullable = false)
    private Invoice invoice;

    @Column(name = "claim_number", nullable = false, unique = true)
    private String claimNumber;

    @Column(nullable = false)
    private String status;

    @Column(name = "submitted_date")
    private LocalDate submittedDate;

    @Column(name = "resolved_date")
    private LocalDate resolvedDate;

    public InsuranceClaim() {
    }

    public InsuranceClaim(Long id, Invoice invoice, String claimNumber, String status, LocalDate submittedDate, LocalDate resolvedDate) {
        this.id = id;
        this.invoice = invoice;
        this.claimNumber = claimNumber;
        this.status = status;
        this.submittedDate = submittedDate;
        this.resolvedDate = resolvedDate;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Invoice getInvoice() {
        return invoice;
    }

    public void setInvoice(Invoice invoice) {
        this.invoice = invoice;
    }

    public String getClaimNumber() {
        return claimNumber;
    }

    public void setClaimNumber(String claimNumber) {
        this.claimNumber = claimNumber;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public LocalDate getSubmittedDate() {
        return submittedDate;
    }

    public void setSubmittedDate(LocalDate submittedDate) {
        this.submittedDate = submittedDate;
    }

    public LocalDate getResolvedDate() {
        return resolvedDate;
    }

    public void setResolvedDate(LocalDate resolvedDate) {
        this.resolvedDate = resolvedDate;
    }
}
