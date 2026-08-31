package com.example.attendance.service;

import com.example.attendance.model.Message;
import com.example.attendance.repository.MessageRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class MessageServiceImpl implements MessageService {

    private final MessageRepository messageRepository;

    @Autowired
    public MessageServiceImpl(MessageRepository messageRepository) {
        this.messageRepository = messageRepository;
    }

    /**
     * Retrieves the most recent messages ordered by timestamp descending.
     * Limits the result to the latest 50 messages to avoid excessive payloads.
     *
     * @return a list of recent Message entities
     */
    @Override
    @Transactional(readOnly = true)
    public List<Message> getRecentMessages() {
        // Use a PageRequest to limit the number of records returned
        PageRequest pageRequest = PageRequest.of(0, 50, Sort.by(Sort.Direction.DESC, "timestamp"));
        return messageRepository.findAll(pageRequest).getContent();
    }

    /**
     * Persists a new message to the database.
     *
     * @param message the Message entity to save
     * @return the persisted Message with generated ID and timestamp
     */
    @Override
    @Transactional
    public Message saveMessage(Message message) {
        // Ensure the timestamp is set if not provided
        if (message.getTimestamp() == null) {
            message.setTimestamp(java.time.Instant.now());
        }
        return messageRepository.save(message);
    }
}
