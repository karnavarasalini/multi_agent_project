package com.example.hotel_guest_management_website.service;

import com.example.hotel_guest_management_website.entity.Staff;
import com.example.hotel_guest_management_website.repository.StaffRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
public class StaffService {

    private final StaffRepository staffRepository;

    public StaffService(StaffRepository staffRepository) {
        this.staffRepository = staffRepository;
    }

    /**
     * Retrieve all staff members.
     */
    @Transactional(readOnly = true)
    public List<Staff> getAllStaff() {
        return staffRepository.findAll();
    }

    /**
     * Retrieve a staff member by its ID.
     *
     * @param id the staff ID
     * @return the found Staff
     * @throws IllegalArgumentException if no staff with the given ID exists
     */
    @Transactional(readOnly = true)
    public Staff getStaffById(Long id) {
        Optional<Staff> optionalStaff = staffRepository.findById(id);
        return optionalStaff.orElseThrow(() -> new IllegalArgumentException("Staff not found with id: " + id));
    }

    /**
     * Create a new staff member.
     */
    @Transactional
    public Staff createStaff(Staff staff) {
        // Ensure the entity is new
        staff.setId(null);
        return staffRepository.save(staff);
    }

    /**
     * Update an existing staff member.
     *
     * @param id   the ID of the staff to update
     * @param staff the staff data to apply
     * @return the updated Staff
     * @throws IllegalArgumentException if the staff does not exist
     */
    @Transactional
    public Staff updateStaff(Long id, Staff staff) {
        Staff existing = getStaffById(id);
        existing.setFirstName(staff.getFirstName());
        existing.setLastName(staff.getLastName());
        existing.setEmail(staff.getEmail());
        existing.setPassword(staff.getPassword());
        existing.setRole(staff.getRole());
        existing.setEnabled(staff.getEnabled());
        return staffRepository.save(existing);
    }

    /**
     * Delete a staff member by ID.
     *
     * @param id the ID of the staff to delete
     * @throws IllegalArgumentException if the staff does not exist
     */
    @Transactional
    public void deleteStaff(Long id) {
        Staff existing = getStaffById(id);
        staffRepository.delete(existing);
    }
}
