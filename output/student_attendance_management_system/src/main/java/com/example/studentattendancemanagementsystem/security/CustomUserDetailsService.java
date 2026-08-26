package com.example.studentattendancemanagementsystem.security;

import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.core.userdetails.User;
import org.springframework.stereotype.Service;
import java.util.Map;
import java.util.HashMap;

/**
 * Stub implementation of {@link UserDetailsService} that loads user details from an
 * in‑memory source. In a real application this would delegate to a repository or
 * external identity provider.
 */
@Service
public class CustomUserDetailsService implements UserDetailsService {

    private static final Map<String, UserDetails> USERS = new HashMap<>();

    static {
        // Passwords are stored with {noop} encoder for simplicity in this stub.
        USERS.put("admin", User.builder()
                .username("admin")
                .password("{noop}adminpass")
                .roles("ADMIN")
                .build());
        USERS.put("user", User.builder()
                .username("user")
                .password("{noop}userpass")
                .roles("USER")
                .build());
    }

    @Override
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        UserDetails user = USERS.get(username);
        if (user == null) {
            throw new UsernameNotFoundException("User not found: " + username);
        }
        return user;
    }
}
