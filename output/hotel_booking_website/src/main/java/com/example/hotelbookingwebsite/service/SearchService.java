package com.example.hotelbookingwebsite.service;

import com.example.hotelbookingwebsite.entity.Amenity;
import com.example.hotelbookingwebsite.entity.Hotel;
import com.example.hotelbookingwebsite.entity.Room;
import com.example.hotelbookingwebsite.repository.HotelRepository;
import com.example.hotelbookingwebsite.repository.BookingRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class SearchService {

    private final HotelRepository hotelRepository;
    private final BookingRepository bookingRepository;

    public SearchService(HotelRepository hotelRepository, BookingRepository bookingRepository) {
        this.hotelRepository = hotelRepository;
        this.bookingRepository = bookingRepository;
    }

    /**
     * Search hotels based on location (city or country), desired stay dates and required amenities.
     *
     * @param city        city name (optional, can be null or empty)
     * @param country     country name (optional, can be null or empty)
     * @param checkIn     desired check‑in date (must not be null)
     * @param checkOut    desired check‑out date (must not be null and after checkIn)
     * @param amenityNames set of amenity names that the hotel must provide (optional, can be empty)
     * @return list of hotels that satisfy all criteria and have at least one available room for the period
     */
    @Transactional(readOnly = true)
    public List<Hotel> search(String city, String country, LocalDate checkIn, LocalDate checkOut, Set<String> amenityNames) {
        // Basic validation
        if (checkIn == null || checkOut == null || !checkOut.isAfter(checkIn)) {
            throw new IllegalArgumentException("Invalid check‑in/check‑out dates");
        }

        // 1. Retrieve hotels matching location criteria
        List<Hotel> hotels;
        if ((city == null || city.isBlank()) && (country == null || country.isBlank())) {
            hotels = hotelRepository.findAll();
        } else if (city != null && !city.isBlank() && (country == null || country.isBlank())) {
            hotels = hotelRepository.findByCityIgnoreCase(city);
        } else if ((city == null || city.isBlank()) && country != null && !country.isBlank()) {
            hotels = hotelRepository.findByCountryIgnoreCase(country);
        } else {
            hotels = hotelRepository.findByCityIgnoreCaseAndCountryIgnoreCase(city, country);
        }

        // 2. Filter by required amenities (hotel must contain all requested amenities)
        if (amenityNames != null && !amenityNames.isEmpty()) {
            hotels = hotels.stream()
                    .filter(hotel -> {
                        Set<String> hotelAmenityNames = hotel.getAmenities().stream()
                                .map(Amenity::getName)
                                .map(String::toLowerCase)
                                .collect(Collectors.toSet());
                        return amenityNames.stream()
                                .allMatch(req -> hotelAmenityNames.contains(req.toLowerCase()));
                    })
                    .collect(Collectors.toList());
        }

        // 3. Keep only hotels that have at least one room available for the whole period
        return hotels.stream()
                .filter(hotel -> hotel.getRooms().stream().anyMatch(room -> isRoomAvailable(room.getId(), checkIn, checkOut)))
                .collect(Collectors.toList());
    }

    /**
     * Checks whether a specific room is free for the given date range.
     * The room is considered unavailable if there exists a booking with overlapping dates and a status that is not CANCELLED.
     */
    private boolean isRoomAvailable(Long roomId, LocalDate checkIn, LocalDate checkOut) {
        // The BookingRepository is expected to expose a method that returns count of overlapping bookings.
        // If such method does not exist, a derived query can be added:
        // long count = bookingRepository.countByRoomIdAndStatusNotAndCheckInBeforeAndCheckOutAfter(roomId, BookingStatus.CANCELLED, checkOut, checkIn);
        // For this implementation we use a generic method assuming it returns true when count == 0.
        return bookingRepository.isRoomAvailable(roomId, checkIn, checkOut);
    }
}
