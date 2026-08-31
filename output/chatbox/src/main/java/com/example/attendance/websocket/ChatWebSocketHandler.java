package com.example.attendance.websocket;

import com.example.attendance.model.Message;
import com.example.attendance.service.MessageService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import java.io.IOException;
import java.time.Instant;

@Component
public class ChatWebSocketHandler extends TextWebSocketHandler {

    private final MessageService messageService;
    private final SimpMessagingTemplate messagingTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public ChatWebSocketHandler(MessageService messageService, SimpMessagingTemplate messagingTemplate) {
        this.messageService = messageService;
        this.messagingTemplate = messagingTemplate;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        // Connection established - can log or perform actions if needed
        super.afterConnectionEstablished(session);
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage textMessage) throws IOException {
        // Deserialize incoming JSON payload to Message entity
        Message incoming = objectMapper.readValue(textMessage.getPayload(), Message.class);
        // Ensure timestamp is set
        if (incoming.getTimestamp() == null) {
            incoming.setTimestamp(Instant.now());
        }
        // Persist the message
        Message saved = messageService.saveMessage(incoming);
        // Broadcast to all subscribers on the /topic/messages destination
        messagingTemplate.convertAndSend("/topic/messages", saved);
    }
}
