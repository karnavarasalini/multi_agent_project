package com.example.hotel_guest_management_website.service;

import com.example.hotel_guest_management_website.entity.Reservation;
import com.example.hotel_guest_management_website.repository.ReservationRepository;
import jakarta.persistence.EntityNotFoundException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class ReservationService {

    private final ReservationRepository reservationRepository;

    public ReservationService(ReservationRepository reservationRepository) {
        this.reservationRepository = reservationRepository;
    }

    public List<Reservation> findAll() {
        return reservationRepository.findAll();
    }

    public Reservation findById(Long id) {
        return reservationRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Reservation not found with id: " + id));
    }

    @Transactional
    public Reservation create(Reservation reservation) {
        reservation.setCreatedAt(LocalDateTime.now());
        reservation.setUpdatedAt(LocalDateTime.now());
        reservation.setStatus("PENDING");
        return reservationRepository.save(reservation);
    }

    @Transactional
    public Reservation update(Long id, Reservation updatedReservation) {
        Reservation existing = findById(id);
        existing.setCheckInDate(updatedReservation.getCheckInDate());
        existing.setCheckOutDate(updatedReservation.getCheckOutDate());
        existing.setRoom(updatedReservation.getRoom());
        existing.setGuest(updatedReservation.getGuest());
        existing.setStatus(updatedReservation.getStatus());
        existing.setTotalAmount(updatedReservation.getTotalAmount());
        existing.setUpdatedAt(LocalDateTime.now());
        return reservationRepository.save(existing);
    }

    @Transactional
    public void delete(Long id) {
        Reservation reservation = findById(id);
        reservationRepository.delete(reservation);
    }

    @Transactional
    public Reservation checkIn(Long id) {
        Reservation reservation = findById(id);
        reservation.setStatus("CHECKED_IN");
        reservation.setUpdatedAt(LocalDateTime.now());
        return reservationRepository.save(reservation);
    }

    @Transactional
    public Reservation checkOut(Long id) {
        Reservation reservation = findById(id);
        reservation.setStatus("CHECKED_OUT");
        reservation.setUpdatedAt(LocalDateTime.now());
        return reservationRepository.save(reservation);
    }

    @Transactional
    public Reservation generateInvoice(Long id) {
        Reservation reservation = findById(id);
        reservation.setStatus("INVOICED");
        reservation.setUpdatedAt(LocalDateTime.now());
        return reservationRepository.save(reservation);
    }
}
