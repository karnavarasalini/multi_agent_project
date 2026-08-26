package com.example.studentattendancemanagementsystem.service;

import com.example.studentattendancemanagementsystem.entity.Attendance;
import com.example.studentattendancemanagementsystem.entity.Student;
import com.example.studentattendancemanagementsystem.exception.ResourceNotFoundException;
import com.example.studentattendancemanagementsystem.repository.AttendanceRepository;
import com.example.studentattendancemanagementsystem.repository.StudentRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.Optional;

@Service
@Transactional
public class AttendanceService {

    private final AttendanceRepository attendanceRepository;
    private final StudentRepository studentRepository;

    public AttendanceService(AttendanceRepository attendanceRepository, StudentRepository studentRepository) {
        this.attendanceRepository = attendanceRepository;
        this.studentRepository = studentRepository;
    }

    /**
     * Create a new attendance record for a given student.
     */
    public Attendance createAttendance(Long studentId, LocalDate date, Attendance.AttendanceStatus status) {
        Student student = studentRepository.findById(studentId)
                .orElseThrow(() -> new ResourceNotFoundException("Student not found with id: " + studentId));
        Attendance attendance = new Attendance();
        attendance.setStudent(student);
        attendance.setDate(date);
        attendance.setStatus(status);
        return attendanceRepository.save(attendance);
    }

    /**
     * Retrieve an attendance record by its id.
     */
    public Attendance getAttendanceById(Long id) {
        return attendanceRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Attendance not found with id: " + id));
    }

    /**
     * List all attendance records with pagination.
     */
    public Page<Attendance> getAllAttendances(Pageable pageable) {
        return attendanceRepository.findAll(pageable);
    }

    /**
     * Update an existing attendance record.
     */
    public Attendance updateAttendance(Long id, LocalDate date, Attendance.AttendanceStatus status) {
        Attendance attendance = attendanceRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Attendance not found with id: " + id));
        attendance.setDate(date);
        attendance.setStatus(status);
        return attendanceRepository.save(attendance);
    }

    /**
     * Delete an attendance record by its id.
     */
    public void deleteAttendance(Long id) {
        Attendance attendance = attendanceRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Attendance not found with id: " + id));
        attendanceRepository.delete(attendance);
    }

    /**
     * List attendance records for a specific student with pagination.
     */
    public Page<Attendance> getAttendancesByStudentId(Long studentId, Pageable pageable) {
        Student student = studentRepository.findById(studentId)
                .orElseThrow(() -> new ResourceNotFoundException("Student not found with id: " + studentId));
        return attendanceRepository.findByStudent(student, pageable);
    }
}
