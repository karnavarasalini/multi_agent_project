package com.example.hotelbookingwebsite.service;

import com.example.hotelbookingwebsite.entity.Booking;
import com.example.hotelbookingwebsite.entity.Room;
import com.example.hotelbookingwebsite.repository.BookingRepository;
import com.example.hotelbookingwebsite.repository.RoomRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.Optional;

@Service
public class BookingServiceImpl implements BookingService {

    private final BookingRepository bookingRepository;
    private final RoomRepository roomRepository;

    public BookingServiceImpl(BookingRepository bookingRepository, RoomRepository roomRepository) {
        this.bookingRepository = bookingRepository;
        this.roomRepository = roomRepository;
    }

    @Override
    @Transactional
    public Booking createBooking(Booking booking) {
        // Validate room existence
        Room room = roomRepository.findById(booking.getRoom().getId())
                .orElseThrow(() -> new IllegalArgumentException("Room not found"));
        // Calculate total price based on number of nights (inclusive)
        long days = ChronoUnit.DAYS.between(booking.getStartDate(), booking.getEndDate()) + 1;
        if (days <= 0) {
            throw new IllegalArgumentException("End date must be after start date");
        }
        BigDecimal totalPrice = room.getPrice().multiply(BigDecimal.valueOf(days));
        booking.setTotalPrice(totalPrice);
        booking.setStatus("CONFIRMED");
        booking.setCreatedAt(new Timestamp(System.currentTimeMillis()));
        // Ensure the relationship is set correctly
        booking.setRoom(room);
        return bookingRepository.save(booking);
    }

    @Override
    @Transactional
    public Booking modifyBooking(Long bookingId, Booking updatedBooking) {
        Booking existing = bookingRepository.findById(bookingId)
                .orElseThrow(() -> new IllegalArgumentException("Booking not found"));
        // Update mutable fields
        LocalDate newStart = updatedBooking.getStartDate();
        LocalDate newEnd = updatedBooking.getEndDate();
        if (newStart != null && newEnd != null) {
            long days = ChronoUnit.DAYS.between(newStart, newEnd) + 1;
            if (days <= 0) {
                throw new IllegalArgumentException("End date must be after start date");
            }
            existing.setStartDate(newStart);
            existing.setEndDate(newEnd);
            // Recalculate total price using the existing room price
            BigDecimal newTotal = existing.getRoom().getPrice().multiply(BigDecimal.valueOf(days));
            existing.setTotalPrice(newTotal);
        }
        // Other fields like status can be updated if needed (omitted for brevity)
        return bookingRepository.save(existing);
    }

    @Override
    @Transactional
    public Booking cancelBooking(Long bookingId) {
        Booking existing = bookingRepository.findById(bookingId)
                .orElseThrow(() -> new IllegalArgumentException("Booking not found"));
        existing.setStatus("CANCELLED");
        return bookingRepository.save(existing);
    }
}
