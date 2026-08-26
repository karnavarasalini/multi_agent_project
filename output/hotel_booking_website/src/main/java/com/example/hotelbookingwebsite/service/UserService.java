package com.example.hotelbookingwebsite.service;

import com.example.hotelbookingwebsite.entity.Role;
import com.example.hotelbookingwebsite.entity.User;
import com.example.hotelbookingwebsite.repository.RoleRepository;
import com.example.hotelbookingwebsite.repository.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Collections;
import java.util.Optional;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final RoleRepository roleRepository;
    private final PasswordEncoder passwordEncoder;

    public UserService(UserRepository userRepository,
                       RoleRepository roleRepository,
                       PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.roleRepository = roleRepository;
        this.passwordEncoder = passwordEncoder;
    }

    /**
     * Registers a new user. The raw password is encoded, and the default ROLE_USER is assigned.
     *
     * @param user the user entity containing raw password and other details
     * @return the persisted user with encoded password and assigned role
     */
    @Transactional
    public User registerUser(User user) {
        if (userRepository.findByEmail(user.getEmail()).isPresent()) {
            throw new IllegalArgumentException("Email already in use");
        }
        // Encode password
        String encodedPassword = passwordEncoder.encode(user.getPassword());
        user.setPassword(encodedPassword);
        // Assign default role USER
        Role userRole = roleRepository.findByName("ROLE_USER")
                .orElseThrow(() -> new IllegalStateException("Default role USER not found"));
        user.setRoles(Collections.singleton(userRole));
        return userRepository.save(user);
    }

    /**
     * Retrieves a user by its identifier.
     *
     * @param id the user id
     * @return Optional containing the user if found
     */
    @Transactional(readOnly = true)
    public Optional<User> findById(Long id) {
        return userRepository.findById(id);
    }

    /**
     * Retrieves a user by email.
     *
     * @param email the user's email
     * @return Optional containing the user if found
     */
    @Transactional(readOnly = true)
    public Optional<User> findByEmail(String email) {
        return userRepository.findByEmail(email);
    }
}
