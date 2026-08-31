package com.example.attendancewebsite.service;

import com.example.attendancewebsite.entity.AttendanceRecord;
import com.example.attendancewebsite.entity.User;
import com.example.attendancewebsite.repository.AttendanceRecordRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class AttendanceService {

    private final AttendanceRecordRepository attendanceRecordRepository;
    private final UserService userService;

    private User getAuthenticatedUser() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new IllegalStateException("User is not authenticated");
        }
        String username = authentication.getName();
        return userService.findByUsername(username)
                .orElseThrow(() -> new IllegalStateException("Authenticated user not found"));
    }

    @Transactional
    public AttendanceRecord checkIn() {
        User user = getAuthenticatedUser();
        LocalDate today = LocalDate.now();
        // Ensure no existing check‑in for today
        boolean alreadyCheckedIn = attendanceRecordRepository
                .existsByUserIdAndDate(user.getId(), today);
        if (alreadyCheckedIn) {
            throw new IllegalStateException("User has already checked in today");
        }
        AttendanceRecord record = new AttendanceRecord();
        record.setUser(user);
        record.setDate(today);
        record.setCheckInTime(LocalDateTime.now());
        return attendanceRecordRepository.save(record);
    }

    @Transactional
    public AttendanceRecord checkOut() {
        User user = getAuthenticatedUser();
        LocalDate today = LocalDate.now();
        AttendanceRecord record = attendanceRecordRepository
                .findByUserIdAndDate(user.getId(), today)
                .orElseThrow(() -> new IllegalStateException("No check‑in record found for today"));
        if (record.getCheckOutTime() != null) {
            throw new IllegalStateException("User has already checked out today");
        }
        record.setCheckOutTime(LocalDateTime.now());
        return attendanceRecordRepository.save(record);
    }

    @Transactional(readOnly = true)
    public List<AttendanceRecord> getTodayRecords() {
        LocalDate today = LocalDate.now();
        return attendanceRecordRepository.findAllByDate(today);
    }
}
