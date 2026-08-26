package com.example.alarmapplication.alarm.service.impl;

import com.example.alarmapplication.alarm.entity.Alarm;
import com.example.alarmapplication.alarm.entity.AlarmTriggerLog;
import com.example.alarmapplication.alarm.repository.AlarmRepository;
import com.example.alarmapplication.alarm.repository.AlarmTriggerLogRepository;
import com.example.alarmapplication.alarm.scheduler.AlarmSchedulerService;
import com.example.alarmapplication.alarm.service.AlarmTriggerLogService;
import com.example.alarmapplication.exception.ResourceNotFoundException;
import com.example.alarmapplication.notification.service.PushNotificationService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

@Service
public class AlarmTriggerLogServiceImpl implements AlarmTriggerLogService {

    private final AlarmRepository alarmRepository;
    private final AlarmTriggerLogRepository alarmTriggerLogRepository;
    private final AlarmSchedulerService alarmSchedulerService;
    private final PushNotificationService pushNotificationService;

    public AlarmTriggerLogServiceImpl(
            AlarmRepository alarmRepository,
            AlarmTriggerLogRepository alarmTriggerLogRepository,
            AlarmSchedulerService alarmSchedulerService,
            PushNotificationService pushNotificationService) {
        this.alarmRepository = alarmRepository;
        this.alarmTriggerLogRepository = alarmTriggerLogRepository;
        this.alarmSchedulerService = alarmSchedulerService;
        this.pushNotificationService = pushNotificationService;
    }

    @Override
    @Transactional
    public AlarmTriggerLog snoozeAlarm(Long alarmId, int durationMinutes) {
        Alarm alarm = alarmRepository.findById(alarmId)
                .orElseThrow(() -> new ResourceNotFoundException("Alarm not found with id: " + alarmId));

        Instant now = Instant.now();
        Instant snoozedUntil = now.plus(durationMinutes, ChronoUnit.MINUTES);

        AlarmTriggerLog triggerLog = alarmTriggerLogRepository.findTopByAlarmIdOrderByTriggeredAtDesc(alarmId)
                .orElseGet(() -> {
                    AlarmTriggerLog newLog = new AlarmTriggerLog();
                    newLog.setAlarmId(alarmId);
                    newLog.setScheduledTime(now);
                    return newLog;
                });

        triggerLog.setTriggeredAt(now);
        triggerLog.setStatus("SNOOZED");
        triggerLog.setSnoozedUntil(snoozedUntil);

        AlarmTriggerLog savedLog = alarmTriggerLogRepository.save(triggerLog);

        alarmSchedulerService.scheduleSnooze(alarm, snoozedUntil);
        pushNotificationService.sendSilentPushNotification(alarm.getUserId(), alarmId, "SNOOZED", snoozedUntil);

        return savedLog;
    }

    @Override
    @Transactional
    public AlarmTriggerLog dismissAlarm(Long alarmId) {
        Alarm alarm = alarmRepository.findById(alarmId)
                .orElseThrow(() -> new ResourceNotFoundException("Alarm not found with id: " + alarmId));

        Instant now = Instant.now();

        AlarmTriggerLog triggerLog = alarmTriggerLogRepository.findTopByAlarmIdOrderByTriggeredAtDesc(alarmId)
                .orElseGet(() -> {
                    AlarmTriggerLog newLog = new AlarmTriggerLog();
                    newLog.setAlarmId(alarmId);
                    newLog.setScheduledTime(now);
                    return newLog;
                });

        triggerLog.setTriggeredAt(now);
        triggerLog.setStatus("DISMISSED");
        triggerLog.setSnoozedUntil(null);

        AlarmTriggerLog savedLog = alarmTriggerLogRepository.save(triggerLog);

        alarmSchedulerService.cancelSnooze(alarmId);
        pushNotificationService.sendSilentPushNotification(alarm.getUserId(), alarmId, "DISMISSED", null);

        return savedLog;
    }
}
