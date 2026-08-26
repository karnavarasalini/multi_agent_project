package com.example.alarmapplication.alarm.dto;

import java.time.Instant;
import java.time.LocalTime;

public class AlarmResponseDto {

    private Long id;
    private Long userId;
    private String label;
    private LocalTime alarmTime;
    private Boolean enabled;
    private String repeatDays;
    private Long soundId;
    private Integer volume;
    private Boolean vibrate;
    private Long version;
    private Instant createdAt;
    private SyncMetadata syncMetadata;

    public AlarmResponseDto() {
    }

    public AlarmResponseDto(Long id, Long userId, String label, LocalTime alarmTime, Boolean enabled,
                            String repeatDays, Long soundId, Integer volume, Boolean vibrate,
                            Long version, Instant createdAt, SyncMetadata syncMetadata) {
        this.id = id;
        this.userId = userId;
        this.label = label;
        this.alarmTime = alarmTime;
        this.enabled = enabled;
        this.repeatDays = repeatDays;
        this.soundId = soundId;
        this.volume = volume;
        this.vibrate = vibrate;
        this.version = version;
        this.createdAt = createdAt;
        this.syncMetadata = syncMetadata;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public String getLabel() {
        return label;
    }

    public void setLabel(String label) {
        this.label = label;
    }

    public LocalTime getAlarmTime() {
        return alarmTime;
    }

    public void setAlarmTime(LocalTime alarmTime) {
        this.alarmTime = alarmTime;
    }

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }

    public String getRepeatDays() {
        return repeatDays;
    }

    public void setRepeatDays(String repeatDays) {
        this.repeatDays = repeatDays;
    }

    public Long getSoundId() {
        return soundId;
    }

    public void setSoundId(Long soundId) {
        this.soundId = soundId;
    }

    public Integer getVolume() {
        return volume;
    }

    public void setVolume(Integer volume) {
        this.volume = volume;
    }

    public Boolean getVibrate() {
        return vibrate;
    }

    public void setVibrate(Boolean vibrate) {
        this.vibrate = vibrate;
    }

    public Long getVersion() {
        return version;
    }

    public void setVersion(Long version) {
        this.version = version;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public SyncMetadata getSyncMetadata() {
        return syncMetadata;
    }

    public void setSyncMetadata(SyncMetadata syncMetadata) {
        this.syncMetadata = syncMetadata;
    }

    public static class SyncMetadata {
        private Long entityVersion;
        private Instant lastSyncedAt;
        private String syncChecksum;
        private Boolean offlineBackupEligible;

        public SyncMetadata() {
        }

        public SyncMetadata(Long entityVersion, Instant lastSyncedAt, String syncChecksum, Boolean offlineBackupEligible) {
            this.entityVersion = entityVersion;
            this.lastSyncedAt = lastSyncedAt;
            this.syncChecksum = syncChecksum;
            this.offlineBackupEligible = offlineBackupEligible;
        }

        public Long getEntityVersion() {
            return entityVersion;
        }

        public void setEntityVersion(Long entityVersion) {
            this.entityVersion = entityVersion;
        }

        public Instant getLastSyncedAt() {
            return lastSyncedAt;
        }

        public void setLastSyncedAt(Instant lastSyncedAt) {
            this.lastSyncedAt = lastSyncedAt;
        }

        public String getSyncChecksum() {
            return syncChecksum;
        }

        public void setSyncChecksum(String syncChecksum) {
            this.syncChecksum = syncChecksum;
        }

        public Boolean getOfflineBackupEligible() {
            return offlineBackupEligible;
        }

        public void setOfflineBackupEligible(Boolean offlineBackupEligible) {
            this.offlineBackupEligible = offlineBackupEligible;
        }
    }
}
