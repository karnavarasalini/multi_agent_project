package com.example.studentattendancemanagementsystem.controller;

import com.example.studentattendancemanagementsystem.dto.AttendanceDto;
import com.example.studentattendancemanagementsystem.service.AttendanceService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import javax.validation.Valid;

@RestController
@RequestMapping("/attendance")
@RequiredArgsConstructor
@Validated
public class AttendanceController {

    private final AttendanceService attendanceService;

    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<AttendanceDto> createAttendance(@RequestBody @Valid AttendanceDto attendanceDto) {
        AttendanceDto created = attendanceService.create(attendanceDto);
        return new ResponseEntity<>(created, HttpStatus.CREATED);
    }

    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Page<AttendanceDto>> getAllAttendances(Pageable pageable) {
        Page<AttendanceDto> page = attendanceService.findAll(pageable);
        return ResponseEntity.ok(page);
    }

    @GetMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<AttendanceDto> getAttendanceById(@PathVariable Long id) {
        AttendanceDto dto = attendanceService.findById(id);
        return ResponseEntity.ok(dto);
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<AttendanceDto> updateAttendance(@PathVariable Long id, @RequestBody @Valid AttendanceDto attendanceDto) {
        AttendanceDto updated = attendanceService.update(id, attendanceDto);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> deleteAttendance(@PathVariable Long id) {
        attendanceService.delete(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/students/{studentId}")
    @PreAuthorize("hasAnyRole('ADMIN','USER')")
    public ResponseEntity<Page<AttendanceDto>> getAttendanceByStudent(@PathVariable Long studentId, Pageable pageable) {
        Page<AttendanceDto> page = attendanceService.findByStudentId(studentId, pageable);
        return ResponseEntity.ok(page);
    }
}
