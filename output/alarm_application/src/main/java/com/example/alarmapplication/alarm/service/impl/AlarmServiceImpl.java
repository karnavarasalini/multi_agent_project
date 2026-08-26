package com.example.alarmapplication.alarm.service.impl;

import com.example.alarmapplication.alarm.dto.AlarmRequestDto;
import com.example.alarmapplication.alarm.dto.AlarmResponseDto;
import com.example.alarmapplication.alarm.entity.Alarm;
import com.example.alarmapplication.alarm.entity.AlarmTriggerLog;
import com.example.alarmapplication.alarm.repository.AlarmRepository;
import com.example.alarmapplication.alarm.repository.AlarmTriggerLogRepository;
import com.example.alarmapplication.alarm.service.AlarmService;
import com.example.alarmapplication.user.entity.User;
import com.example.alarmapplication.user.repository.UserRepository;
import org.quartz.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.*;
import java.util.*;

@Service
@Transactional
public class AlarmServiceImpl implements AlarmService {

    private static final Logger log = LoggerFactory.getLogger(AlarmServiceImpl.class);

    private final AlarmRepository alarmRepository;
    private final AlarmTriggerLogRepository triggerLogRepository;
    private final UserRepository userRepository;
    private final Scheduler scheduler;

    public AlarmServiceImpl(AlarmRepository alarmRepository,
                            AlarmTriggerLogRepository triggerLogRepository,
                            UserRepository userRepository,
                            Scheduler scheduler) {
        this.alarmRepository = alarmRepository;
        this.triggerLogRepository = triggerLogRepository;
        this.userRepository = userRepository;
        this.scheduler = scheduler;
    }

    @Override
    public AlarmResponseDto createAlarm(Long userId, AlarmRequestDto requestDto) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found with id: " + userId));

        Alarm alarm = new Alarm();
        alarm.setUserId(user.getId());
        alarm.setLabel(requestDto.getLabel());
        alarm.setAlarmTime(requestDto.getAlarmTime());
        alarm.setEnabled(requestDto.getEnabled() != null ? requestDto.getEnabled() : true);
        alarm.setRepeatDays(requestDto.getRepeatDays());
        alarm.setSoundId(requestDto.getSoundId());
        alarm.setVolume(requestDto.getVolume() != null ? requestDto.getVolume() : 80);
        alarm.setVibrate(requestDto.getVibrate() != null ? requestDto.getVibrate() : true);
        alarm.setCreatedAt(Instant.now());

        Alarm savedAlarm = alarmRepository.save(alarm);

        if (Boolean.TRUE.equals(savedAlarm.getEnabled())) {
            scheduleQuartzJob(savedAlarm, user.getTimezone());
        }

        return mapToResponseDto(savedAlarm, user.getTimezone());
    }

    @Override
    @Transactional(readOnly = true)
    public AlarmResponseDto getAlarmById(Long id, Long userId) {
        Alarm alarm = getAlarmAndVerifyOwner(id, userId);
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found with id: " + userId));
        return mapToResponseDto(alarm, user.getTimezone());
    }

    @Override
    @Transactional(readOnly = true)
    public List<AlarmResponseDto> getAlarmsByUserId(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found with id: " + userId));

        List<Alarm> alarms = alarmRepository.findByUserId(userId);
        List<AlarmResponseDto> responseList = new ArrayList<>();
        for (Alarm alarm : alarms) {
            responseList.add(mapToResponseDto(alarm, user.getTimezone()));
        }
        return responseList;
    }

    @Override
    public AlarmResponseDto updateAlarm(Long id, Long userId, AlarmRequestDto requestDto) {
        Alarm alarm = getAlarmAndVerifyOwner(id, userId);
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found with id: " + userId));

        alarm.setLabel(requestDto.getLabel());
        alarm.setAlarmTime(requestDto.getAlarmTime());
        alarm.setRepeatDays(requestDto.getRepeatDays());
        alarm.setSoundId(requestDto.getSoundId());
        if (requestDto.getVolume() != null) {
            alarm.setVolume(requestDto.getVolume());
        }
        if (requestDto.getVibrate() != null) {
            alarm.setVibrate(requestDto.getVibrate());
        }
        if (requestDto.getEnabled() != null) {
            alarm.setEnabled(requestDto.getEnabled());
        }

        Alarm updatedAlarm = alarmRepository.save(alarm);

        if (Boolean.TRUE.equals(updatedAlarm.getEnabled())) {
            scheduleQuartzJob(updatedAlarm, user.getTimezone());
        } else {
            unscheduleQuartzJob(updatedAlarm.getId());
        }

        return mapToResponseDto(updatedAlarm, user.getTimezone());
    }

    @Override
    public AlarmResponseDto toggleAlarm(Long id, Long userId) {
        Alarm alarm = getAlarmAndVerifyOwner(id, userId);
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found with id: " + userId));

        try {
            boolean newState = !Boolean.TRUE.equals(alarm.getEnabled());
            alarm.setEnabled(newState);
            Alarm savedAlarm = alarmRepository.save(alarm);

            if (newState) {
                scheduleQuartzJob(savedAlarm, user.getTimezone());
            } else {
                unscheduleQuartzJob(savedAlarm.getId());
            }

            return mapToResponseDto(savedAlarm, user.getTimezone());
        } catch (ObjectOptimisticLockingFailureException e) {
            log.warn("Optimistic locking failure during toggle for alarm id: {}", id);
            throw new IllegalStateException("Alarm state was modified concurrently. Please retry.", e);
        }
    }

    @Override
    public void deleteAlarm(Long id, Long userId) {
        Alarm alarm = getAlarmAndVerifyOwner(id, userId);
        unscheduleQuartzJob(alarm.getId());
        alarmRepository.delete(alarm);
    }

    @Override
    public AlarmResponseDto snoozeAlarm(Long id, Long userId, int snoozeMinutes) {
        Alarm alarm = getAlarmAndVerifyOwner(id, userId);
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found with id: " + userId));

        Instant snoozeUntil = Instant.now().plus(Duration.ofMinutes(snoozeMinutes));

        AlarmTriggerLog logEntry = new AlarmTriggerLog();
        logEntry.setAlarmId(alarm.getId());
        logEntry.setScheduledTime(Instant.now());
        logEntry.setTriggeredAt(Instant.now());
        logEntry.setStatus("SNOOZED");
        logEntry.setSnoozedUntil(snoozeUntil);
        triggerLogRepository.save(logEntry);

        scheduleSnoozeQuartzJob(alarm.getId(), snoozeUntil);

        AlarmResponseDto dto = mapToResponseDto(alarm, user.getTimezone());
        dto.setNextTriggerTime(snoozeUntil);
        return dto;
    }

    @Override
    public AlarmResponseDto dismissAlarm(Long id, Long userId) {
        Alarm alarm = getAlarmAndVerifyOwner(id, userId);
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found with id: " + userId));

        AlarmTriggerLog logEntry = new AlarmTriggerLog();
        logEntry.setAlarmId(alarm.getId());
        logEntry.setScheduledTime(Instant.now());
        logEntry.setTriggeredAt(Instant.now());
        logEntry.setStatus("DISMISSED");
        triggerLogRepository.save(logEntry);

        unscheduleSnoozeQuartzJob(alarm.getId());

        if (Boolean.TRUE.equals(alarm.getEnabled())) {
            scheduleQuartzJob(alarm, user.getTimezone());
        }

        return mapToResponseDto(alarm, user.getTimezone());
    }

    @Override
    public Instant calculateNextTriggerTime(LocalTime alarmTime, String repeatDays, String timezone) {
        ZoneId zoneId = ZoneId.of(timezone != null ? timezone : "UTC");
        ZonedDateTime now = ZonedDateTime.now(zoneId);

        if (repeatDays == null || repeatDays.trim().isEmpty()) {
            ZonedDateTime candidate = now.with(alarmTime);
            if (!candidate.isAfter(now)) {
                candidate = candidate.plusDays(1);
            }
            return candidate.toInstant();
        }

        Set<DayOfWeek> activeDays = parseRepeatDays(repeatDays);
        if (activeDays.isEmpty()) {
            ZonedDateTime candidate = now.with(alarmTime);
            if (!candidate.isAfter(now)) {
                candidate = candidate.plusDays(1);
            }
            return candidate.toInstant();
        }

        ZonedDateTime earliest = null;
        for (int i = 0; i < 8; i++) {
            ZonedDateTime candidate = now.plusDays(i).with(alarmTime);
            if (activeDays.contains(candidate.getDayOfWeek()) && candidate.isAfter(now)) {
                if (earliest == null || candidate.isBefore(earliest)) {
                    earliest = candidate;
                }
            }
        }

        if (earliest != null) {
            return earliest.toInstant();
        }

        return now.plusDays(1).with(alarmTime).toInstant();
    }

    private Alarm getAlarmAndVerifyOwner(Long alarmId, Long userId) {
        Alarm alarm = alarmRepository.findById(alarmId)
                .orElseThrow(() -> new IllegalArgumentException("Alarm not found with id: " + alarmId));
        if (!alarm.getUserId().equals(userId)) {
            throw new SecurityException("Unauthorized access to alarm id: " + alarmId);
        }
        return alarm;
    }

    private Set<DayOfWeek> parseRepeatDays(String repeatDays) {
        Set<DayOfWeek> days = EnumSet.noneOf(DayOfWeek.class);
        if (repeatDays == null || repeatDays.trim().isEmpty()) {
            return days;
        }

        String[] parts = repeatDays.split(",");
        for (String part : parts) {
            String trimmed = part.trim().toUpperCase();
            try {
                if (trimmed.matches("\\d+")) {
                    int bitmaskOrVal = Integer.parseInt(trimmed);
                    if (bitmaskOrVal >= 1 && bitmaskOrVal <= 7) {
                        days.add(DayOfWeek.of(bitmaskOrVal));
                    } else if (bitmaskOrVal > 7) {
                        for (DayOfWeek dow : DayOfWeek.values()) {
                            if ((bitmaskOrVal & (1 << (dow.getValue() - 1))) != 0) {
                                days.add(dow);
                            }
                        }
                    }
                } else {
                    days.add(DayOfWeek.valueOf(trimmed));
                }
            } catch (Exception e) {
                log.warn("Could not parse repeat day segment: {}", part);
            }
        }
        return days;
    }

    private AlarmResponseDto mapToResponseDto(Alarm alarm, String timezone) {
        AlarmResponseDto dto = new AlarmResponseDto();
        dto.setId(alarm.getId());
        dto.setUserId(alarm.getUserId());
        dto.setLabel(alarm.getLabel());
        dto.setAlarmTime(alarm.getAlarmTime());
        dto.setEnabled(alarm.getEnabled());
        dto.setRepeatDays(alarm.getRepeatDays());
        dto.setSoundId(alarm.getSoundId());
        dto.setVolume(alarm.getVolume());
        dto.setVibrate(alarm.getVibrate());
        dto.setCreatedAt(alarm.getCreatedAt());

        if (Boolean.TRUE.equals(alarm.getEnabled())) {
            dto.setNextTriggerTime(calculateNextTriggerTime(alarm.getAlarmTime(), alarm.getRepeatDays(), timezone));
        }

        dto.setSyncMetadata(generateSyncMetadata(alarm));
        return dto;
    }

    private String generateSyncMetadata(Alarm alarm) {
        try {
            String raw = alarm.getId() + ":" + alarm.getEnabled() + ":" + alarm.getAlarmTime() + ":" + alarm.getRepeatDays();
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(raw.getBytes(StandardCharsets.UTF_8));
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) hexString.append('0');
                hexString.append(hex);
            }
            return hexString.toString().substring(0, 16);
        } catch (NoSuchAlgorithmException e) {
            return UUID.randomUUID().toString().substring(0, 16);
        }
    }

    @SuppressWarnings("unchecked")
    private Class<? extends Job> getAlarmJobClass() {
        try {
            return (Class<? extends Job>) Class.forName("com.example.alarmapplication.alarm.job.AlarmExecutionJob");
        } catch (ClassNotFoundException e) {
            return Job.class;
        }
    }

    private void scheduleQuartzJob(Alarm alarm, String timezone) {
        try {
            JobKey jobKey = JobKey.jobKey("ALARM_JOB_" + alarm.getId(), "ALARMS");
            TriggerKey triggerKey = TriggerKey.triggerKey("ALARM_TRIGGER_" + alarm.getId(), "ALARMS");

            if (scheduler.checkExists(jobKey)) {
                scheduler.deleteJob(jobKey);
            }

            Instant nextTime = calculateNextTriggerTime(alarm.getAlarmTime(), alarm.getRepeatDays(), timezone);

            JobDataMap jobDataMap = new JobDataMap();
            jobDataMap.put("alarmId", alarm.getId());
            jobDataMap.put("userId", alarm.getUserId());
            jobDataMap.put("soundId", alarm.getSoundId());
            jobDataMap.put("highPriorityPush", true);

            JobDetail jobDetail = JobBuilder.newJob(getAlarmJobClass())
                    .withIdentity(jobKey)
                    .usingJobData(jobDataMap)
                    .storeDurably()
                    .build();

            Trigger trigger = TriggerBuilder.newTrigger()
                    .withIdentity(triggerKey)
                    .startAt(Date.from(nextTime))
                    .withSchedule(SimpleScheduleBuilder.simpleSchedule().withMisfireHandlingInstructionFireNow())
                    .build();

            scheduler.scheduleJob(jobDetail, trigger);
            log.info("Scheduled Quartz job for alarmId: {} at {}", alarm.getId(), nextTime);
        } catch (Exception e) {
            log.error("Failed to schedule Quartz job for alarmId: {}", alarm.getId(), e);
        }
    }

    private void unscheduleQuartzJob(Long alarmId) {
        try {
            JobKey jobKey = JobKey.jobKey("ALARM_JOB_" + alarmId, "ALARMS");
            if (scheduler.checkExists(jobKey)) {
                scheduler.deleteJob(jobKey);
                log.info("Unscheduled Quartz job for alarmId: {}", alarmId);
            }
        } catch (SchedulerException e) {
            log.error("Failed to unschedule Quartz job for alarmId: {}", alarmId, e);
        }
    }

    private void scheduleSnoozeQuartzJob(Long alarmId, Instant snoozeUntil) {
        try {
            TriggerKey triggerKey = TriggerKey.triggerKey("SNOOZE_TRIGGER_" + alarmId, "SNOOZE");
            JobKey jobKey = JobKey.jobKey("ALARM_JOB_" + alarmId, "ALARMS");

            Trigger trigger = TriggerBuilder.newTrigger()
                    .withIdentity(triggerKey)
                    .startAt(Date.from(snoozeUntil))
                    .forJob(jobKey)
                    .build();

            scheduler.scheduleJob(trigger);
            log.info("Scheduled snooze trigger for alarmId: {} until {}", alarmId, snoozeUntil);
        } catch (Exception e) {
            log.error("Failed to schedule snooze Quartz job for alarmId: {}", alarmId, e);
        }
    }

    private void unscheduleSnoozeQuartzJob(Long alarmId) {
        try {
            TriggerKey triggerKey = TriggerKey.triggerKey("SNOOZE_TRIGGER_" + alarmId, "SNOOZE");
            if (scheduler.checkExists(triggerKey)) {
                scheduler.unscheduleJob(triggerKey);
            }
        } catch (SchedulerException e) {
            log.error("Failed to unschedule snooze Quartz trigger for alarmId: {}", alarmId, e);
        }
    }
}
