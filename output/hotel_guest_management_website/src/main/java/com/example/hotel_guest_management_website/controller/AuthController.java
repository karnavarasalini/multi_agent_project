package com.example.hotel_guest_management_website.controller;

import com.example.hotel_guest_management_website.entity.Guest;
import com.example.hotel_guest_management_website.entity.Staff;
import com.example.hotel_guest_management_website.repository.GuestRepository;
import com.example.hotel_guest_management_website.repository.StaffRepository;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Optional;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final GuestRepository guestRepository;
    private final StaffRepository staffRepository;

    public AuthController(GuestRepository guestRepository, StaffRepository staffRepository) {
        this.guestRepository = guestRepository;
        this.staffRepository = staffRepository;
    }

    @PostMapping("/register")
    public ResponseEntity<Guest> register(@RequestBody @Valid RegisterRequest request) {
        Guest guest = new Guest();
        guest.setFirstName(request.getFirstName());
        guest.setLastName(request.getLastName());
        guest.setEmail(request.getEmail());
        guest.setPhone(request.getPhone());
        guest.setAddress(request.getAddress());
        guest.setPassword(request.getPassword()); // In a real app, encode the password
        guest.setEnabled(true);
        Guest saved = guestRepository.save(guest);
        return new ResponseEntity<>(saved, HttpStatus.CREATED);
    }

    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(@RequestBody @Valid LoginRequest request) {
        String role = request.getRole();
        if ("GUEST".equalsIgnoreCase(role)) {
            Optional<Guest> optGuest = guestRepository.findByEmail(request.getEmail());
            if (optGuest.isPresent() && optGuest.get().getPassword().equals(request.getPassword())) {
                return ResponseEntity.ok(new AuthResponse("dummy-token", "GUEST"));
            }
        } else if ("STAFF".equalsIgnoreCase(role)) {
            Optional<Staff> optStaff = staffRepository.findByEmail(request.getEmail());
            if (optStaff.isPresent() && optStaff.get().getPassword().equals(request.getPassword())) {
                return ResponseEntity.ok(new AuthResponse("dummy-token", "STAFF"));
            }
        }
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
    }

    // DTOs
    public static class RegisterRequest {
        @NotBlank
        private String firstName;
        @NotBlank
        private String lastName;
        @Email
        @NotBlank
        private String email;
        @NotBlank
        private String phone;
        @NotBlank
        private String address;
        @NotBlank
        @Size(min = 6)
        private String password;

        // getters and setters
        public String getFirstName() { return firstName; }
        public void setFirstName(String firstName) { this.firstName = firstName; }
        public String getLastName() { return lastName; }
        public void setLastName(String lastName) { this.lastName = lastName; }
        public String getEmail() { return email; }
        public void setEmail(String email) { this.email = email; }
        public String getPhone() { return phone; }
        public void setPhone(String phone) { this.phone = phone; }
        public String getAddress() { return address; }
        public void setAddress(String address) { this.address = address; }
        public String getPassword() { return password; }
        public void setPassword(String password) { this.password = password; }
    }

    public static class LoginRequest {
        @Email
        @NotBlank
        private String email;
        @NotBlank
        private String password;
        @NotBlank
        private String role; // GUEST or STAFF

        // getters and setters
        public String getEmail() { return email; }
        public void setEmail(String email) { this.email = email; }
        public String getPassword() { return password; }
        public void setPassword(String password) { this.password = password; }
        public String getRole() { return role; }
        public void setRole(String role) { this.role = role; }
    }

    public static class AuthResponse {
        private String token;
        private String role;

        public AuthResponse(String token, String role) {
            this.token = token;
            this.role = role;
        }
        public String getToken() { return token; }
        public void setToken(String token) { this.token = token; }
        public String getRole() { return role; }
        public void setRole(String role) { this.role = role; }
    }
}
