package com.example.contact_management_website.controller;

import com.example.contact_management_website.entity.Group;
import com.example.contact_management_website.entity.User;
import com.example.contact_management_website.service.GroupService;
import com.example.contact_management_website.service.UserService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * REST controller for managing groups.
 */
@RestController
@RequestMapping("/api/groups")
class GroupController {

    private final GroupService groupService;
    private final UserService userService;

    public GroupController(GroupService groupService, UserService userService) {
        this.groupService = groupService;
        this.userService = userService;
    }

    private Long getCurrentUserId(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new IllegalStateException("Authentication information is missing");
        }
        Object principal = authentication.getPrincipal();
        String username;
        if (principal instanceof UserDetails userDetails) {
            username = userDetails.getUsername();
        } else {
            username = principal.toString();
        }
        Optional<User> optionalUser = userService.findByUsername(username);
        User user = optionalUser.orElseThrow(() -> new IllegalStateException("User not found"));
        return user.getId();
    }

    @GetMapping
    public ResponseEntity<List<GroupDto>> getAllGroups(Authentication authentication) {
        Long userId = getCurrentUserId(authentication);
        List<GroupDto> groups = groupService.getAllGroups(userId)
                .stream()
                .map(g -> new GroupDto(g.getId(), g.getName(), userId))
                .collect(Collectors.toList());
        return ResponseEntity.ok(groups);
    }

    @PostMapping
    public ResponseEntity<GroupDto> createGroup(@RequestBody @Valid GroupDto groupDto,
                                                Authentication authentication) {
        Long userId = getCurrentUserId(authentication);
        Group group = new Group();
        group.setName(groupDto.getName());
        Group created = groupService.createGroup(userId, group);
        GroupDto responseDto = new GroupDto(created.getId(), created.getName(), userId);
        return ResponseEntity.status(HttpStatus.CREATED).body(responseDto);
    }

    @GetMapping("/{id}")
    public ResponseEntity<GroupDto> getGroupById(@PathVariable Long id,
                                                  Authentication authentication) {
        Long userId = getCurrentUserId(authentication);
        Group group = groupService.getGroupById(id, userId);
        GroupDto responseDto = new GroupDto(group.getId(), group.getName(), userId);
        return ResponseEntity.ok(responseDto);
    }

    @PutMapping("/{id}")
    public ResponseEntity<GroupDto> updateGroup(@PathVariable Long id,
                                                @RequestBody @Valid GroupDto groupDto,
                                                Authentication authentication) {
        Long userId = getCurrentUserId(authentication);
        Group group = new Group();
        group.setName(groupDto.getName());
        Group updated = groupService.updateGroup(id, group);
        GroupDto responseDto = new GroupDto(updated.getId(), updated.getName(), userId);
        return ResponseEntity.ok(responseDto);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteGroup(@PathVariable Long id,
                                            Authentication authentication) {
        Long userId = getCurrentUserId(authentication);
        groupService.deleteGroup(id, userId);
        return ResponseEntity.noContent().build();
    }

    /**
     * Simple DTO used for group data transfer.
     */
    public static class GroupDto {
        private Long id;
        private String name;
        private Long userId;

        public GroupDto() {}

        public GroupDto(Long id, String name, Long userId) {
            this.id = id;
            this.name = name;
            this.userId = userId;
        }

        public Long getId() {
            return id;
        }

        public void setId(Long id) {
            this.id = id;
        }

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }

        public Long getUserId() {
            return userId;
        }

        public void setUserId(Long userId) {
            this.userId = userId;
        }
    }
}