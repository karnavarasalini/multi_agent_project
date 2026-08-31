package com.example.attendance.controller;

import com.example.attendance.entity.Attendance;
import com.example.attendance.service.AttendanceService;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class AttendanceController {

    private final AttendanceService attendanceService;

    // ---------------------------------------------------------------------
    // CRUD endpoints (Admin only)
    // ---------------------------------------------------------------------
    @PostMapping("/attendance")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Attendance> createAttendance(@RequestBody Attendance attendance) {
        Attendance saved = attendanceService.save(attendance);
        return new ResponseEntity<>(saved, HttpStatus.CREATED);
    }

    @GetMapping("/attendance/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Attendance> getAttendance(@PathVariable Long id) {
        Attendance found = attendanceService.findById(id);
        return ResponseEntity.ok(found);
    }

    @PutMapping("/attendance/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Attendance> updateAttendance(@PathVariable Long id, @RequestBody Attendance attendance) {
        Attendance updated = attendanceService.update(id, attendance);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/attendance/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> deleteAttendance(@PathVariable Long id) {
        attendanceService.deleteById(id);
        return ResponseEntity.noContent().build();
    }

    // ---------------------------------------------------------------------
    // Reporting endpoints (Admin only)
    // ---------------------------------------------------------------------
    @GetMapping("/attendance/report")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<List<Attendance>> getAttendanceReport(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate start,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate end) {
        List<Attendance> report = attendanceService.report(start, end);
        return ResponseEntity.ok(report);
    }

    @GetMapping("/students/{studentId}/attendance/report")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<List<Attendance>> getStudentAttendanceReport(
            @PathVariable Long studentId,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate start,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate end) {
        List<Attendance> report = attendanceService.reportByStudent(studentId, start, end);
        return ResponseEntity.ok(report);
    }

    // ---------------------------------------------------------------------
    // Student specific views (Student role)
    // ---------------------------------------------------------------------
    @GetMapping("/students/me/attendance")
    @PreAuthorize("hasRole('STUDENT')")
    public ResponseEntity<List<Attendance>> getOwnAttendance(Authentication authentication) {
        String username = authentication.getName();
        List<Attendance> attendances = attendanceService.findByUsername(username);
        return ResponseEntity.ok(attendances);
    }

    @GetMapping("/students/{studentId}/attendance")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<List<Attendance>> getAttendanceByStudent(@PathVariable Long studentId) {
        List<Attendance> attendances = attendanceService.findByStudentId(studentId);
        return ResponseEntity.ok(attendances);
    }
}
