package com.example.contact_management_website.service;

import com.example.contact_management_website.entity.User;
import com.example.contact_management_website.repository.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.NoSuchElementException;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public UserService(UserRepository userRepository, PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    /**
     * Registers a new user. The password is encoded, the account is enabled, and the creation timestamp is set.
     *
     * @param user the user entity containing raw password and other details
     * @return the persisted user
     * @throws IllegalArgumentException if a user with the same username already exists
     */
    public User register(User user) {
        if (userRepository.findByUsername(user.getUsername()).isPresent()) {
            throw new IllegalArgumentException("Username already exists");
        }
        user.setPassword(passwordEncoder.encode(user.getPassword()));
        user.setEnabled(true);
        user.setCreatedAt(LocalDateTime.now());
        return userRepository.save(user);
    }

    /**
     * Retrieves a user by username.
     *
     * @param username the username to search for
     * @return the user entity
     * @throws NoSuchElementException if no user with the given username exists
     */
    public User findByUsername(String username) {
        return userRepository.findByUsername(username)
                .orElseThrow(() -> new NoSuchElementException("User not found with username " + username));
    }

    public User getById(Long id) {
        return userRepository.findById(id)
                .orElseThrow(() -> new NoSuchElementException("User not found with id " + id));
    }

    public List<User> getAll() {
        return userRepository.findAll();
    }
}