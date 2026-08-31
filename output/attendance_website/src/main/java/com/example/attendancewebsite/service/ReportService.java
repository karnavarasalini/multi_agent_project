package com.example.attendancewebsite.service;

import com.example.attendancewebsite.entity.AttendanceRecord;
import com.example.attendancewebsite.entity.Report;
import com.example.attendancewebsite.repository.AttendanceRepository;
import com.example.attendancewebsite.repository.ReportRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class ReportService {

    private final AttendanceRepository attendanceRepository;
    private final ReportRepository reportRepository;

    /**
     * Generates a report for the given date range and format.
     *
     * @param startDate the start date (inclusive)
     * @param endDate   the end date (inclusive)
     * @param format    the desired format (e.g., "CSV" or "PDF")
     * @return the persisted {@link Report} entity
     */
    public Report generateReport(LocalDate startDate, LocalDate endDate, String format) {
        // Retrieve attendance records within the range
        List<AttendanceRecord> records = attendanceRepository.findByDateBetween(startDate, endDate);
        // Additional aggregation logic can be placed here (e.g., totals per user)
        Report report = new Report();
        report.setStartDate(startDate);
        report.setEndDate(endDate);
        report.setGeneratedAt(LocalDateTime.now());
        report.setFormat(format);
        // Persist the report metadata
        return reportRepository.save(report);
    }
}
