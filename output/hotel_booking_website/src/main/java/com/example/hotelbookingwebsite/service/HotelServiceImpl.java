package com.example.hotelbookingwebsite.service;

import com.example.hotelbookingwebsite.entity.Hotel;
import com.example.hotelbookingwebsite.repository.HotelRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

@Service
public class HotelServiceImpl {

    private final HotelRepository hotelRepository;

    public HotelServiceImpl(HotelRepository hotelRepository) {
        this.hotelRepository = hotelRepository;
    }

    /**
     * Search hotels by optional city and minimum rating.
     * If a parameter is null, it is ignored.
     *
     * @param city       the city to filter by (optional)
     * @param minRating  the minimum rating (optional)
     * @return list of hotels matching the criteria
     */
    @Transactional(readOnly = true)
    public List<Hotel> searchHotels(String city, Double minRating) {
        List<Hotel> allHotels = hotelRepository.findAll();
        return allHotels.stream()
                .filter(h -> city == null || Objects.equals(h.getCity(), city))
                .filter(h -> minRating == null || h.getRating() != null && h.getRating() >= minRating)
                .collect(Collectors.toList());
    }

    /**
     * Retrieve detailed information for a specific hotel.
     *
     * @param hotelId the id of the hotel
     * @return the Hotel entity if found
     * @throws javax.persistence.EntityNotFoundException if the hotel does not exist
     */
    @Transactional(readOnly = true)
    public Hotel getHotelDetails(Long hotelId) {
        return hotelRepository.findById(hotelId)
                .orElseThrow(() -> new javax.persistence.EntityNotFoundException("Hotel not found with id: " + hotelId));
    }
}
