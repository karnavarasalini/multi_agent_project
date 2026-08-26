package com.example.alarmapplication.notification.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@Service
public class PushNotificationService {

    private static final Logger log = LoggerFactory.getLogger(PushNotificationService.class);

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    @Value("${app.fcm.api-url:https://fcm.googleapis.com/v1/projects/alarm-app/messages:send}")
    private String fcmApiUrl;

    @Value("${app.fcm.server-key:mock-server-key}")
    private String serverKey;

    public PushNotificationService(ObjectMapper objectMapper) {
        this.restTemplate = new RestTemplate();
        this.objectMapper = objectMapper;
    }

    public void sendAlarmTriggerNotification(String deviceToken, Long alarmId, String label, String soundName, Integer volume) {
        log.info("Preparing high-priority FCM/APNs silent push for alarmId: {} to token: {}", alarmId, deviceToken);

        Map<String, Object> payload = buildFcmPayload(deviceToken, alarmId, label, soundName, volume);

        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + serverKey);

            String jsonPayload = objectMapper.writeValueAsString(payload);
            HttpEntity<String> entity = new HttpEntity<>(jsonPayload, headers);

            log.debug("Sending FCM payload: {}", jsonPayload);

            if ("mock-server-key".equals(serverKey)) {
                log.info("FCM Server key not set. Simulated successful push dispatch for alarmId: {}", alarmId);
                return;
            }

            ResponseEntity<String> response = restTemplate.postForEntity(fcmApiUrl, entity, String.class);
            if (response.getStatusCode().is2xxSuccessful()) {
                log.info("Successfully dispatched high-priority notification for alarmId: {}", alarmId);
            } else {
                log.warn("FCM push returned non-2xx response: {} - {}", response.getStatusCode(), response.getBody());
            }
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize FCM notification payload for alarmId: {}", alarmId, e);
        } catch (Exception e) {
            log.error("Error occurred while sending push notification for alarmId: {}", alarmId, e);
        }
    }

    private Map<String, Object> buildFcmPayload(String deviceToken, Long alarmId, String label, String soundName, Integer volume) {
        Map<String, Object> message = new HashMap<>();
        message.put("token", deviceToken);

        // Data payload for background processing / wake up lock-screen
        Map<String, String> data = new HashMap<>();
        data.put("alarmId", String.valueOf(alarmId));
        data.put("label", label != null ? label : "Alarm");
        data.put("soundName", soundName != null ? soundName : "default");
        data.put("volume", String.valueOf(volume != null ? volume : 100));
        data.put("type", "ALARM_TRIGGER");
        data.put("timestamp", String.valueOf(System.currentTimeMillis()));

        message.put("data", data);

        // Android high priority configuration
        Map<String, Object> android = new HashMap<>();
        android.put("priority", "HIGH");
        Map<String, Object> androidNotification = new HashMap<>();
        androidNotification.put("channel_id", "alarm_high_priority_channel");
        androidNotification.put("sound", soundName != null ? soundName : "default");
        android.put("notification", androidNotification);

        message.put("android", android);

        // APNs high priority payload for lock-screen wake up
        Map<String, Object> apns = new HashMap<>();
        Map<String, Object> headers = new HashMap<>();
        headers.put("apns-priority", "10");
        headers.put("apns-push-type", "background");
        apns.put("headers", headers);

        Map<String, Object> payload = new HashMap<>();
        Map<String, Object> aps = new HashMap<>();
        aps.put("content-available", 1);
        aps.put("sound", soundName != null ? soundName : "default");
        payload.put("aps", aps);
        apns.put("payload", payload);

        message.put("apns", apns);

        Map<String, Object> root = new HashMap<>();
        root.put("message", message);
        return root;
    }
}
