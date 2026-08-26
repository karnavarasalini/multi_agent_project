package com.example.alarmapplication.alarm.controller;

import com.example.alarmapplication.alarm.dto.AlarmRequestDto;
import com.example.alarmapplication.alarm.dto.AlarmResponseDto;
import com.example.alarmapplication.alarm.dto.SnoozeRequestDto;
import com.example.alarmapplication.alarm.service.AlarmService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/alarms")
public class AlarmController {

    private final AlarmService alarmService;

    public AlarmController(AlarmService alarmService) {
        this.alarmService = alarmService;
    }

    @PostMapping
    public ResponseEntity<AlarmResponseDto> createAlarm(
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId,
            @Valid @RequestBody AlarmRequestDto requestDto) {
        AlarmResponseDto createdAlarm = alarmService.createAlarm(userId, requestDto);
        return ResponseEntity.status(HttpStatus.CREATED).body(createdAlarm);
    }

    @GetMapping
    public ResponseEntity<List<AlarmResponseDto>> getAllAlarms(
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId) {
        List<AlarmResponseDto> alarms = alarmService.getAlarmsByUserId(userId);
        return ResponseEntity.ok(alarms);
    }

    @GetMapping("/{id}")
    public ResponseEntity<AlarmResponseDto> getAlarmById(
            @PathVariable Long id,
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId) {
        AlarmResponseDto alarm = alarmService.getAlarmById(id, userId);
        return ResponseEntity.ok(alarm);
    }

    @PutMapping("/{id}")
    public ResponseEntity<AlarmResponseDto> updateAlarm(
            @PathVariable Long id,
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId,
            @Valid @RequestBody AlarmRequestDto requestDto) {
        AlarmResponseDto updatedAlarm = alarmService.updateAlarm(id, userId, requestDto);
        return ResponseEntity.ok(updatedAlarm);
    }

    @PatchMapping("/{id}/toggle")
    public ResponseEntity<AlarmResponseDto> toggleAlarm(
            @PathVariable Long id,
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId) {
        AlarmResponseDto toggledAlarm = alarmService.toggleAlarm(id, userId);
        return ResponseEntity.ok(toggledAlarm);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteAlarm(
            @PathVariable Long id,
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId) {
        alarmService.deleteAlarm(id, userId);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/{id}/snooze")
    public ResponseEntity<AlarmResponseDto> snoozeAlarm(
            @PathVariable Long id,
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId,
            @Valid @RequestBody(required = false) SnoozeRequestDto snoozeRequestDto) {
        int durationMinutes = (snoozeRequestDto != null && snoozeRequestDto.getDurationMinutes() != null)
                ? snoozeRequestDto.getDurationMinutes()
                : 10;
        AlarmResponseDto snoozedAlarm = alarmService.snoozeAlarm(id, userId, durationMinutes);
        return ResponseEntity.ok(snoozedAlarm);
    }

    @PostMapping("/{id}/dismiss")
    public ResponseEntity<AlarmResponseDto> dismissAlarm(
            @PathVariable Long id,
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId) {
        AlarmResponseDto dismissedAlarm = alarmService.dismissAlarm(id, userId);
        return ResponseEntity.ok(dismissedAlarm);
    }
}
