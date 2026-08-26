package com.example.hotelbookingwebsite.service;

import com.example.hotelbookingwebsite.entity.BookingStatus;
import com.example.hotelbookingwebsite.entity.Room;
import com.example.hotelbookingwebsite.repository.BookingRepository;
import com.example.hotelbookingwebsite.repository.RoomRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class AvailabilityService {

    private final RoomRepository roomRepository;
    private final BookingRepository bookingRepository;

    public AvailabilityService(RoomRepository roomRepository, BookingRepository bookingRepository) {
        this.roomRepository = roomRepository;
        this.bookingRepository = bookingRepository;
    }

    /**
     * Returns a list of rooms for the given hotel that are available between the supplied dates.
     * A room is considered unavailable if there exists a booking (not cancelled) that overlaps
     * with the requested period.
     *
     * @param hotelId the hotel identifier
     * @param checkIn  the desired check‑in date (inclusive)
     * @param checkOut the desired check‑out date (exclusive)
     * @return list of available rooms
     */
    @Transactional(readOnly = true)
    public List<Room> getAvailableRooms(Long hotelId, LocalDate checkIn, LocalDate checkOut) {
        // Fetch all rooms belonging to the hotel
        List<Room> hotelRooms = roomRepository.findByHotelId(hotelId);

        // Filter out rooms that have conflicting bookings
        return hotelRooms.stream()
                .filter(room -> !bookingRepository.existsByRoomIdAndStatusNotAndCheckInLessThanAndCheckOutGreaterThan(
                        room.getId(),
                        BookingStatus.CANCELLED,
                        checkOut,
                        checkIn))
                .collect(Collectors.toList());
    }
}
