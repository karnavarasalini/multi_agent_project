package com.example.health_management_3.controller;

import com.example.health_management_3.dto.AppointmentDto;
import com.example.health_management_3.entity.Appointment;
import com.example.health_management_3.service.AppointmentService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/appointments")
public class AppointmentController {

    private final AppointmentService appointmentService;

    public AppointmentController(AppointmentService appointmentService) {
        this.appointmentService = appointmentService;
    }

    @GetMapping
    public ResponseEntity<List<Appointment>> getAllAppointments() {
        List<Appointment> appointments = appointmentService.findAll();
        return ResponseEntity.ok(appointments);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Appointment> getAppointmentById(@PathVariable Long id) {
        Appointment appointment = appointmentService.findById(id);
        return ResponseEntity.ok(appointment);
    }

    @PostMapping
    public ResponseEntity<Appointment> createAppointment(@RequestBody @Valid AppointmentDto appointmentDto) {
        Appointment created = appointmentService.create(appointmentDto);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Appointment> updateAppointment(@PathVariable Long id,
                                                         @RequestBody @Valid AppointmentDto appointmentDto) {
        Appointment updated = appointmentService.update(id, appointmentDto);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteAppointment(@PathVariable Long id) {
        appointmentService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
