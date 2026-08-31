package com.example.hotel_guest_management_website.service;

import com.example.hotel_guest_management_website.entity.Invoice;
import com.example.hotel_guest_management_website.entity.Reservation;
import com.example.hotel_guest_management_website.repository.InvoiceRepository;
import com.example.hotel_guest_management_website.repository.ReservationRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;

@Service
public class InvoiceService {

    private final InvoiceRepository invoiceRepository;
    private final ReservationRepository reservationRepository;

    public InvoiceService(InvoiceRepository invoiceRepository, ReservationRepository reservationRepository) {
        this.invoiceRepository = invoiceRepository;
        this.reservationRepository = reservationRepository;
    }

    /**
     * Retrieve all invoices.
     *
     * @return list of invoices
     */
    @Transactional(readOnly = true)
    public List<Invoice> getAllInvoices() {
        return invoiceRepository.findAll();
    }

    /**
     * Retrieve a single invoice by its ID.
     *
     * @param id invoice identifier
     * @return the invoice
     * @throws IllegalArgumentException if invoice does not exist
     */
    @Transactional(readOnly = true)
    public Invoice getInvoiceById(Long id) {
        return invoiceRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Invoice not found with id " + id));
    }

    /**
     * Generate and persist an invoice for a given reservation.
     *
     * @param reservationId reservation identifier
     * @return the created invoice
     * @throws IllegalArgumentException if reservation does not exist
     */
    @Transactional
    public Invoice generateInvoice(Long reservationId) {
        Reservation reservation = reservationRepository.findById(reservationId)
                .orElseThrow(() -> new IllegalArgumentException("Reservation not found with id " + reservationId));

        Invoice invoice = new Invoice();
        invoice.setReservation(reservation);
        invoice.setAmount(reservation.getTotalAmount());
        invoice.setIssuedDate(LocalDate.now());
        invoice.setPaid(false);

        return invoiceRepository.save(invoice);
    }
}