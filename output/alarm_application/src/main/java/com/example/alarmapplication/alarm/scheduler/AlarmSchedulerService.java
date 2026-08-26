package com.example.alarmapplication.alarm.scheduler;

import com.example.alarmapplication.alarm.entity.Alarm;
import org.quartz.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.DayOfWeek;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.Arrays;
import java.util.Date;
import java.util.Set;
import java.util.stream.Collectors;

@Service;
public class AlarmSchedulerService {

    private static final Logger log = LoggerFactory.getLogger(AlarmSchedulerService.class);
    private static final String ALARM_GROUP = "ALARM_GROUP";

    private final Scheduler scheduler;

    public AlarmSchedulerService(Scheduler scheduler) {
        this.scheduler = scheduler;
    }

    public void scheduleAlarm(Alarm alarm, String timezone) {
        try {
            JobKey jobKey = getJobKey(alarm.getId());
            TriggerKey triggerKey = getTriggerKey(alarm.getId());

            if (!Boolean.TRUE.equals(alarm.getEnabled())) {
                cancelAlarm(alarm.getId());
                return;
            }

            ZoneId zoneId = (timezone != null && !timezone.isBlank()) ? ZoneId.of(timezone) : ZoneId.systemDefault();
            ZonedDateTime nextTrigger = calculateNextTriggerTime(alarm.getAlarmTime(), alarm.getRepeatDays(), zoneId);

            if (nextTrigger == null) {
                log.warn("Could not calculate next trigger time for alarm ID: {}", alarm.getId());
                return;
            }

            JobDetail jobDetail = JobBuilder.newJob(AlarmTriggerJob.class)
                    .withIdentity(jobKey)
                    .usingJobData("alarmId", alarm.getId())
                    .usingJobData("userId", alarm.getUserId())
                    .usingJobData("soundId", alarm.getSoundId() != null ? alarm.getSoundId() : -1L)
                    .usingJobData("volume", alarm.getVolume() != null ? alarm.getVolume() : 100)
                    .usingJobData("label", alarm.getLabel() != null ? alarm.getLabel() : "")
                    .requestRecovery(true)
                    .storeDurably()
                    .build();

            Trigger trigger = TriggerBuilder.newTrigger()
                    .withIdentity(triggerKey)
                    .startAt(Date.from(nextTrigger.toInstant()))
                    .withSchedule(SimpleScheduleBuilder.simpleSchedule()
                            .withMisfireHandlingInstructionFireNow())
                    .build();

            if (scheduler.checkExists(jobKey)) {
                scheduler.deleteJob(jobKey);
            }

            scheduler.scheduleJob(jobDetail, trigger);
            log.info("Successfully scheduled alarm ID {} for execution at {}", alarm.getId(), nextTrigger);
        } catch (SchedulerException e) {
            log.error("Failed to schedule alarm ID {}", alarm.getId(), e);
            throw new RuntimeException("Error scheduling alarm with Quartz engine", e);
        }
    }

    public void snoozeAlarm(Long alarmId, Long userId, int snoozeMinutes) {
        try {
            JobKey jobKey = new JobKey("SNOOZE_" + alarmId, ALARM_GROUP);
            TriggerKey triggerKey = new TriggerKey("SNOOZE_TRIGGER_" + alarmId, ALARM_GROUP);

            ZonedDateTime snoozeTime = ZonedDateTime.now().plusMinutes(snoozeMinutes);

            JobDetail jobDetail = JobBuilder.newJob(AlarmTriggerJob.class)
                    .withIdentity(jobKey)
                    .usingJobData("alarmId", alarmId)
                    .usingJobData("userId", userId)
                    .usingJobData("isSnooze", true)
                    .storeDurably()
                    .build();

            Trigger trigger = TriggerBuilder.newTrigger()
                    .withIdentity(triggerKey)
                    .startAt(Date.from(snoozeTime.toInstant()))
                    .build();

            if (scheduler.checkExists(jobKey)) {
                scheduler.deleteJob(jobKey);
            }

            scheduler.scheduleJob(jobDetail, trigger);
            log.info("Alarm ID {} snoozed for {} minutes until {}", alarmId, snoozeMinutes, snoozeTime);
        } catch (SchedulerException e) {
            log.error("Failed to snooze alarm ID {}", alarmId, e);
            throw new RuntimeException("Error snoozing alarm with Quartz engine", e);
        }
    }

    public void cancelAlarm(Long alarmId) {
        try {
            JobKey jobKey = getJobKey(alarmId);
            JobKey snoozeJobKey = new JobKey("SNOOZE_" + alarmId, ALARM_GROUP);

            if (scheduler.checkExists(jobKey)) {
                scheduler.deleteJob(jobKey);
                log.info("Cancelled primary job for alarm ID {}", alarmId);
            }

            if (scheduler.checkExists(snoozeJobKey)) {
                scheduler.deleteJob(snoozeJobKey);
                log.info("Cancelled snooze job for alarm ID {}", alarmId);
            }
        } catch (SchedulerException e) {
            log.error("Failed to cancel alarm ID {}", alarmId, e);
            throw new RuntimeException("Error cancelling alarm in Quartz engine", e);
        }
    }

    public ZonedDateTime calculateNextTriggerTime(LocalTime alarmTime, String repeatDays, ZoneId zoneId) {
        ZonedDateTime now = ZonedDateTime.now(zoneId);
        ZonedDateTime candidate = now.with(alarmTime).withNano(0);

        if (repeatDays == null || repeatDays.trim().isEmpty()) {
            if (!candidate.isAfter(now)) {
                candidate = candidate.plusDays(1);
            }
            return candidate;
        }

        Set<DayOfWeek> activeDays = Arrays.stream(repeatDays.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .map(String::toUpperCase)
                .map(DayOfWeek::valueOf)
                .collect(Collectors.toSet());

        if (activeDays.isEmpty()) {
            if (!candidate.isAfter(now)) {
                candidate = candidate.plusDays(1);
            }
            return candidate;
        }

        for (int i = 0; i <= 7; i++) {
            if (activeDays.contains(candidate.getDayOfWeek()) && candidate.isAfter(now)) {
                return candidate;
            }
            candidate = candidate.plusDays(1);
        }

        return candidate;
    }

    private JobKey getJobKey(Long alarmId) {
        return new JobKey("ALARM_JOB_" + alarmId, ALARM_GROUP);
    }

    private TriggerKey getTriggerKey(Long alarmId) {
        return new TriggerKey("ALARM_TRIGGER_" + alarmId, ALARM_GROUP);
    }

    @DisallowConcurrentExecution
    public static class AlarmTriggerJob implements Job {

        private static final Logger jobLog = LoggerFactory.getLogger(AlarmTriggerJob.class);

        @Override
        public void execute(JobExecutionContext context) throws JobExecutionException {
            JobDataMap dataMap = context.getMergedJobDataMap();
            Long alarmId = dataMap.getLong("alarmId");
            Long userId = dataMap.getLong("userId");
            boolean isSnooze = dataMap.containsKey("isSnooze") && dataMap.getBoolean("isSnooze");

            jobLog.info("Cluster-Safe Quartz Job Executing: alarmId={}, userId={}, isSnooze={}, scheduledTime={}",
                    alarmId, userId, isSnooze, context.getScheduledFireTime());
        }
    }
}
