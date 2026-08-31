package com.example.attendance.controller;

import com.example.attendance.entity.Attendance;
import com.example.attendance.entity.Student;
import com.example.attendance.service.AttendanceServiceImpl;
import com.example.attendance.service.StudentServiceImpl;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/students")
@RequiredArgsConstructor
public class StudentController {

    private final StudentServiceImpl studentService;
    private final AttendanceServiceImpl attendanceService;

    // -------------------- Admin CRUD --------------------
    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<List<Student>> getAllStudents() {
        List<Student> students = studentService.findAll();
        return ResponseEntity.ok(students);
    }

    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Student> createStudent(@RequestBody Student student) {
        Student saved = studentService.save(student);
        return ResponseEntity.ok(saved);
    }

    @GetMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Student> getStudentById(@PathVariable Long id) {
        Optional<Student> opt = studentService.findById(id);
        return opt.map(ResponseEntity::ok).orElseGet(() -> ResponseEntity.notFound().build());
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Student> updateStudent(@PathVariable Long id, @RequestBody Student student) {
        Optional<Student> existing = studentService.findById(id);
        if (!existing.isPresent()) {
            return ResponseEntity.notFound().build();
        }
        Student toUpdate = existing.get();
        toUpdate.setFirstName(student.getFirstName());
        toUpdate.setLastName(student.getLastName());
        toUpdate.setEmail(student.getEmail());
        toUpdate.setUser(student.getUser());
        Student saved = studentService.save(toUpdate);
        return ResponseEntity.ok(saved);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> deleteStudent(@PathVariable Long id) {
        if (!studentService.findById(id).isPresent()) {
            return ResponseEntity.notFound().build();
        }
        studentService.deleteById(id);
        return ResponseEntity.noContent().build();
    }

    // -------------------- Student own attendance --------------------
    @GetMapping("/me/attendance")
    @PreAuthorize("hasRole('STUDENT')")
    public ResponseEntity<List<Attendance>> getOwnAttendance() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        String username = auth.getName();
        Optional<Student> studentOpt = studentService.findByUsername(username);
        if (!studentOpt.isPresent()) {
            return ResponseEntity.notFound().build();
        }
        List<Attendance> attendance = attendanceService.findByStudentId(studentOpt.get().getId());
        return ResponseEntity.ok(attendance);
    }

    // -------------------- Admin view attendance of any student --------------------
    @GetMapping("/{id}/attendance")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<List<Attendance>> getAttendanceByStudent(@PathVariable Long id) {
        if (!studentService.findById(id).isPresent()) {
            return ResponseEntity.notFound().build();
        }
        List<Attendance> attendance = attendanceService.findByStudentId(id);
        return ResponseEntity.ok(attendance);
    }

    // -------------------- Attendance report for a student --------------------
    @GetMapping("/{id}/attendance/report")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<List<Attendance>> getAttendanceReportForStudent(
            @PathVariable Long id,
            @RequestParam("start") String startDateStr,
            @RequestParam("end") String endDateStr) {
        if (!studentService.findById(id).isPresent()) {
            return ResponseEntity.notFound().build();
        }
        LocalDate start = LocalDate.parse(startDateStr);
        LocalDate end = LocalDate.parse(endDateStr);
        List<Attendance> report = attendanceService.getReportForStudent(id, start, end);
        return ResponseEntity.ok(report);
    }
}
