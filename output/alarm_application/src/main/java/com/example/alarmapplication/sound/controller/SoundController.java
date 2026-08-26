package com.example.alarmapplication.sound.controller;

import com.example.alarmapplication.sound.dto.SoundResponseDto;
import com.example.alarmapplication.sound.service.SoundService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/sounds")
public class SoundController {

    private final SoundService soundService;

    public SoundController(SoundService soundService) {
        this.soundService = soundService;
    }

    @GetMapping
    public ResponseEntity<List<SoundResponseDto>> getAllSounds() {
        return ResponseEntity.ok(soundService.getAllSounds());
    }
}
