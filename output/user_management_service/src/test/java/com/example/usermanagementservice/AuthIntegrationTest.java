package com.example.usermanagementservice;

import com.example.usermanagementservice.auth.AuthController;
import com.example.usermanagementservice.util.JwtUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class AuthIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private JwtUtil jwtUtil;

    @Test
    void testRegisterAndLoginSuccess() throws Exception {
        // Register a new user
        var registerRequest = new RegisterRequest("testuser", "test@example.com", "Password123!");
        mockMvc.perform(post("/api/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(registerRequest)))
                .andExpect(status().isOk());

        // Login with the newly created user
        var loginRequest = new LoginRequest("testuser", "Password123!");
        MvcResult result = mockMvc.perform(post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(loginRequest)))
                .andExpect(status().isOk())
                .andReturn();

        String responseBody = result.getResponse().getContentAsString();
        var tokenResponse = objectMapper.readValue(responseBody, TokenResponse.class);
        assertThat(tokenResponse.getToken()).isNotBlank();
        // Verify token can be parsed and contains expected username
        String username = jwtUtil.extractUsername(tokenResponse.getToken());
        assertThat(username).isEqualTo("testuser");
    }

    @Test
    void testLoginInvalidCredentials() throws Exception {
        var loginRequest = new LoginRequest("nonexistent", "wrongPassword");
        mockMvc.perform(post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(loginRequest)))
                .andExpect(status().isUnauthorized());
    }

    // Helper DTOs for request/response payloads used in tests
    static class RegisterRequest {
        private String username;
        private String email;
        private String password;
        public RegisterRequest() {}
        public RegisterRequest(String username, String email, String password) {
            this.username = username;
            this.email = email;
            this.password = password;
        }
        public String getUsername() { return username; }
        public void setUsername(String username) { this.username = username; }
        public String getEmail() { return email; }
        public void setEmail(String email) { this.email = email; }
        public String getPassword() { return password; }
        public void setPassword(String password) { this.password = password; }
    }

    static class LoginRequest {
        private String username;
        private String password;
        public LoginRequest() {}
        public LoginRequest(String username, String password) {
            this.username = username;
            this.password = password;
        }
        public String getUsername() { return username; }
        public void setUsername(String username) { this.username = username; }
        public String getPassword() { return password; }
        public void setPassword(String password) { this.password = password; }
    }

    static class TokenResponse {
        private String token;
        public TokenResponse() {}
        public String getToken() { return token; }
        public void setToken(String token) { this.token = token; }
    }
}
