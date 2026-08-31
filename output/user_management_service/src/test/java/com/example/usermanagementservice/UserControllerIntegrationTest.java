package com.example.usermanagementservice;

import com.example.usermanagementservice.entity.User;
import com.example.usermanagementservice.repository.UserRepository;
import com.example.usermanagementservice.util.JwtUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.web.servlet.MockMvc;

import java.util.HashMap;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class UserControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired
    private PasswordEncoder passwordEncoder;

    private String adminToken;
    private String userToken;
    private Long existingUserId;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @BeforeEach
    void setUp() {
        // Clean DB
        userRepository.deleteAll();

        // Create a regular user
        User user = new User();
        user.setUsername("user");
        user.setEmail("user@example.com");
        user.setPassword(passwordEncoder.encode("userpass"));
        user = userRepository.save(user);
        existingUserId = user.getId();
        userToken = jwtUtil.generateToken(user.getUsername());

        // Create an admin user (for simplicity we reuse the same entity, role handling is assumed inside JwtUtil)
        User admin = new User();
        admin.setUsername("admin");
        admin.setEmail("admin@example.com");
        admin.setPassword(passwordEncoder.encode("adminpass"));
        admin = userRepository.save(admin);
        adminToken = jwtUtil.generateToken(admin.getUsername());
    }

    @Test
    void whenGetCurrentUser_thenReturnUserInfo() throws Exception {
        mockMvc.perform(get("/api/users/me")
                .header("Authorization", "Bearer " + userToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("user"))
                .andExpect(jsonPath("$.email").value("user@example.com"));
    }

    @Test
    void whenAdminCreatesUser_thenUserIsCreated() throws Exception {
        Map<String, String> newUser = new HashMap<>();
        newUser.put("username", "newuser");
        newUser.put("email", "newuser@example.com");
        newUser.put("password", "newpass");

        mockMvc.perform(post("/api/users")
                .header("Authorization", "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(newUser)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.username").value("newuser"))
                .andExpect(jsonPath("$.email").value("newuser@example.com"));
    }

    @Test
    void whenGetUserById_thenReturnUser() throws Exception {
        mockMvc.perform(get("/api/users/{id}", existingUserId)
                .header("Authorization", "Bearer " + adminToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(existingUserId.intValue()))
                .andExpect(jsonPath("$.username").value("user"));
    }

    @Test
    void whenUpdateUser_thenUserIsUpdated() throws Exception {
        Map<String, String> updates = new HashMap<>();
        updates.put("email", "updated@example.com");

        mockMvc.perform(put("/api/users/{id}", existingUserId)
                .header("Authorization", "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(updates)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.email").value("updated@example.com"));
    }

    @Test
    void whenDeleteUser_thenStatusNoContent() throws Exception {
        mockMvc.perform(delete("/api/users/{id}", existingUserId)
                .header("Authorization", "Bearer " + adminToken))
                .andExpect(status().isNoContent());
    }

    @Test
    void whenListAllUsers_thenReturnList() throws Exception {
        // Ensure at least one user exists (admin created in setUp)
        mockMvc.perform(get("/api/users")
                .header("Authorization", "Bearer " + adminToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").exists())
                .andExpect(jsonPath("$[0].username").exists());
    }
}
