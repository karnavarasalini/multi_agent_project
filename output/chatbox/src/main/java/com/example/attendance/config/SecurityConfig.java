package com.example.attendance.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.util.matcher.AntPathRequestMatcher;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            // Disable CSRF for simplicity; WebSocket messages are not vulnerable when using STOMP over SockJS with authentication.
            .csrf(csrf -> csrf.disable())
            // Enforce HTTPS (TLS) for every request.
            .requiresChannel(channel -> channel.anyRequest().requiresSecure())
            // HSTS header to instruct browsers to always use HTTPS.
            .headers(headers -> headers
                .httpStrictTransportSecurity(hsts -> hsts
                    .includeSubDomains(true)
                    .maxAgeInSeconds(31536000)))
            // Authorize HTTP endpoints.
            .authorizeHttpRequests(auth -> auth
                // Public authentication endpoints could be added here, e.g., "/api/auth/**"
                .requestMatchers(new AntPathRequestMatcher("/api/auth/**")).permitAll()
                // Allow unauthenticated access to the SockJS handshake endpoint (the HTTP part of the WebSocket).
                .requestMatchers(new AntPathRequestMatcher("/ws/**")).authenticated()
                // All other API endpoints require authentication.
                .anyRequest().authenticated())
            // Stateless session management – suitable for JWT or other token‑based auth.
            .sessionManagement(sess -> sess.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            // Enable HTTP Basic for quick testing (replace with JWT filter in production).
            .httpBasic(Customizer.withDefaults());
        return http.build();
    }
}
