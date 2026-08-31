package com.example.attendancewebsite.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.Resource;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import com.example.attendancewebsite.service.ReportService;
import java.time.LocalDate;

@RestController
@RequestMapping("/api/reports")
@RequiredArgsConstructor
public class ReportController {

    private final ReportService reportService;

    @GetMapping(value="/csv",produces="text/csv")
    public ResponseEntity<Resource> exportCsv(@RequestParam @DateTimeFormat(iso=DateTimeFormat.ISO.DATE) LocalDate startDate,@RequestParam @DateTimeFormat(iso=DateTimeFormat.ISO.DATE) LocalDate endDate){byte[] data=reportService.generateCsvReport(startDate,endDate);ByteArrayResource resource=new ByteArrayResource(data);String filename=String.format("attendance_report_%s_to_%s.csv",startDate,endDate);return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION,"attachment; filename=\""+filename+"\"").contentLength(data.length).contentType(MediaType.parseMediaType("text/csv")).body(resource);} 

    @GetMapping(value="/pdf",produces="application/pdf")
    public ResponseEntity<Resource> exportPdf(@RequestParam @DateTimeFormat(iso=DateTimeFormat.ISO.DATE) LocalDate startDate,@RequestParam @DateTimeFormat(iso=DateTimeFormat.ISO.DATE) LocalDate endDate){byte[] data=reportService.generatePdfReport(startDate,endDate);ByteArrayResource resource=new ByteArrayResource(data);String filename=String.format("attendance_report_%s_to_%s.pdf",startDate,endDate);return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION,"attachment; filename=\""+filename+"\"").contentLength(data.length).contentType(MediaType.APPLICATION_PDF).body(resource);} 
}
