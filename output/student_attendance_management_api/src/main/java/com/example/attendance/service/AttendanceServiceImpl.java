package com.example.attendance.service;

import com.example.attendance.entity.Attendance;
import com.example.attendance.entity.Student;
import com.example.attendance.exception.ResourceNotFoundException;
import com.example.attendance.repository.AttendanceRepository;
import com.example.attendance.repository.StudentRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
@Transactional
public class AttendanceServiceImpl implements AttendanceService {

    private final AttendanceRepository attendanceRepository;
    private final StudentRepository studentRepository;

    @Override
    public Attendance createAttendance(Attendance attendance) {
        // Ensure the referenced student exists
        Long studentId = attendance.getStudent().getId();
        Student student = studentRepository.findById(studentId)
                .orElseThrow(() -> new ResourceNotFoundException("Student not found with id " + studentId));
        attendance.setStudent(student);
        return attendanceRepository.save(attendance);
    }

    @Override
    @Transactional(readOnly = true)
    public Attendance getAttendanceById(Long id) {
        return attendanceRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Attendance not found with id " + id));
    }

    @Override
    public Attendance updateAttendance(Long id, Attendance updatedAttendance) {
        Attendance existing = attendanceRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Attendance not found with id " + id));
        // Update fields
        if (updatedAttendance.getStudent() != null) {
            Long newStudentId = updatedAttendance.getStudent().getId();
            Student newStudent = studentRepository.findById(newStudentId)
                    .orElseThrow(() -> new ResourceNotFoundException("Student not found with id " + newStudentId));
            existing.setStudent(newStudent);
        }
        if (updatedAttendance.getDate() != null) {
            existing.setDate(updatedAttendance.getDate());
        }
        if (updatedAttendance.getSessionId() != null) {
            existing.setSessionId(updatedAttendance.getSessionId());
        }
        if (updatedAttendance.getStatus() != null) {
            existing.setStatus(updatedAttendance.getStatus());
        }
        return attendanceRepository.save(existing);
    }

    @Override
    public void deleteAttendance(Long id) {
        Attendance existing = attendanceRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Attendance not found with id " + id));
        attendanceRepository.delete(existing);
    }

    @Override
    @Transactional(readOnly = true)
    public List<Attendance> getStudentAttendanceReport(Long studentId, LocalDate startDate, LocalDate endDate) {
        // Validate student existence
        studentRepository.findById(studentId)
                .orElseThrow(() -> new ResourceNotFoundException("Student not found with id " + studentId));
        return attendanceRepository.findAllByStudentIdAndDateBetween(studentId, startDate, endDate);
    }

    @Override
    @Transactional(readOnly = true)
    public List<Attendance> getAllAttendanceReport(LocalDate startDate, LocalDate endDate) {
        return attendanceRepository.findAllByDateBetween(startDate, endDate);
    }
}
