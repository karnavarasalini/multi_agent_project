package com.example.hotel_guest_management_website.service;

import com.example.hotel_guest_management_website.entity.Guest;
import com.example.hotel_guest_management_website.repository.GuestRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
@Transactional(readOnly = true)
public class GuestService {

    private final GuestRepository guestRepository;

    public GuestService(GuestRepository guestRepository) {
        this.guestRepository = guestRepository;
    }

    public List<Guest> findAll() {
        return guestRepository.findAll();
    }

    public Guest findById(Long id) {
        return guestRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Guest not found with id: " + id));
    }

    @Transactional
    public Guest create(Guest guest) {
        guest.setEnabled(true);
        return guestRepository.save(guest);
    }

    @Transactional
    public Guest update(Long id, Guest updatedGuest) {
        Guest existing = findById(id);
        existing.setFirstName(updatedGuest.getFirstName());
        existing.setLastName(updatedGuest.getLastName());
        existing.setEmail(updatedGuest.getEmail());
        existing.setPhone(updatedGuest.getPhone());
        existing.setAddress(updatedGuest.getAddress());
        existing.setPassword(updatedGuest.getPassword());
        existing.setEnabled(updatedGuest.getEnabled());
        return guestRepository.save(existing);
    }

    @Transactional
    public void delete(Long id) {
        Guest guest = findById(id);
        guestRepository.delete(guest);
    }
}
