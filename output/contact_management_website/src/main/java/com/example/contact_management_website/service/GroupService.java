package com.example.contact_management_website.service;

import com.example.contact_management_website.entity.Group;
import com.example.contact_management_website.repository.GroupRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class GroupService {

    private final GroupRepository groupRepository;

    public GroupService(GroupRepository groupRepository) {
        this.groupRepository = groupRepository;
    }

    public List<GroupDto> getAllGroups(Long userId) {
        List<Group> groups = groupRepository.findAllByUserId(userId);
        return groups.stream()
                .map(this::toDto)
                .collect(Collectors.toList());
    }

    public GroupDto getGroupById(Long userId, Long groupId) {
        Group group = groupRepository.findByIdAndUserId(groupId, userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Group not found"));
        return toDto(group);
    }

    @Transactional
    public GroupDto createGroup(Long userId, GroupDto groupDto) {
        Group group = toEntity(groupDto);
        // The caller should set any necessary user association and timestamps.
        Group saved = groupRepository.save(group);
        return toDto(saved);
    }

    @Transactional
    public GroupDto updateGroup(Long userId, Long groupId, GroupDto updatedGroupDto) {
        Group existing = groupRepository.findByIdAndUserId(groupId, userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Group not found"));
        existing.setName(updatedGroupDto.getName());
        existing.setDescription(updatedGroupDto.getDescription());
        // Add other field updates if needed
        Group saved = groupRepository.save(existing);
        return toDto(saved);
    }

    @Transactional
    public void deleteGroup(Long userId, Long groupId) {
        Group existing = groupRepository.findByIdAndUserId(groupId, userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Group not found"));
        groupRepository.delete(existing);
    }

    private GroupDto toDto(Group group) {
        GroupDto dto = new GroupDto();
        dto.setId(group.getId());
        dto.setName(group.getName());
        dto.setDescription(group.getDescription());
        // map other fields if needed
        return dto;
    }

    private Group toEntity(GroupDto dto) {
        Group group = new Group();
        group.setName(dto.getName());
        group.setDescription(dto.getDescription());
        // set other fields if needed
        return group;
    }

    // Simple DTO used within the service layer
    public static class GroupDto {
        private Long id;
        private String name;
        private String description;

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

        public String getDescription() {
            return description;
        }

        public void setDescription(String description) {
            this.description = description;
        }
    }
}