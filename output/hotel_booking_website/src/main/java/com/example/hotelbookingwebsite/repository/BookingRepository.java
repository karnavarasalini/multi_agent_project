package com.example.hotelbookingwebsite.repository;

import com.example.hotelbookingwebsite.entity.Booking;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;
import java.util.List;
import java.time.LocalDate;

@Repository
public interface BookingRepository extends JpaRepository<Booking, Long> {
    Optional<Booking> findById(Long id);
    List<Booking> findByUserId(Long userId);
    List<Booking> findByRoomHotelIdAndStartDateLessThanEqualAndEndDateGreaterThanEqual(Long hotelId, LocalDate endDate, LocalDate startDate);
}