package com.example.attendancewebsite.controller;

import com.example.attendancewebsite.entity.AttendanceRecord;
import com.example.attendancewebsite.service.AttendanceService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/attendance")
public class AttendanceController {

    private final AttendanceService attendanceService;

    public AttendanceController(AttendanceService attendanceService) {
        this.attendanceService = attendanceService;
    }

    @PostMapping("/checkin")
    public ResponseEntity<AttendanceRecord> checkIn() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        String username = auth.getName();
        AttendanceRecord record = attendanceService.checkIn(username);
        return new ResponseEntity<>(record, HttpStatus.CREATED);
    }

    @PostMapping("/checkout")
    public ResponseEntity<AttendanceRecord> checkOut() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        String username = auth.getName();
        AttendanceRecord record = attendanceService.checkOut(username);
        return new ResponseEntity<>(record, HttpStatus.OK);
    }

    @GetMapping("/daily")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<List<AttendanceRecord>> getDaily() {
        List<AttendanceRecord> records = attendanceService.getTodayRecords();
        return ResponseEntity.ok(records);
    }
}
