package com.example.contact_management_website.service;

import com.example.contact_management_website.entity.Contact;
import com.example.contact_management_website.repository.ContactRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class ContactService {

    private final ContactRepository contactRepository;

    public ContactService(ContactRepository contactRepository) {
        this.contactRepository = contactRepository;
    }

    /**
     * Retrieve all contacts belonging to a specific user.
     */
    @Transactional(readOnly = true)
    public List<Contact> getAllContacts(Long userId) {
        return StreamSupport.stream(contactRepository.findAll().spliterator(), false)
                .filter(contact -> contact.getUserId().equals(userId))
                .collect(Collectors.toList());
    }

    /**
     * Retrieve a single contact by its ID for the given user.
     */
    @Transactional(readOnly = true)
    public Contact getContactById(Long id, Long userId) {
        Optional<Contact> optional = contactRepository.findById(id);
        return optional.filter(contact -> contact.getUserId().equals(userId))
                .orElseThrow(() -> new IllegalArgumentException("Contact not found or does not belong to user"));
    }

    /**
     * Create a new contact for the given user.
     */
    @Transactional
    public Contact createContact(Contact contact, Long userId) {
        contact.setId(null); // ensure new entity
        contact.setUserId(userId);
        contact.setCreatedAt(LocalDateTime.now());
        return contactRepository.save(contact);
    }

    /**
     * Update an existing contact belonging to the given user.
     */
    @Transactional
    public Contact updateContact(Long id, Contact updatedContact, Long userId) {
        Contact existing = getContactById(id, userId);
        // Update mutable fields
        existing.setFirstName(updatedContact.getFirstName());
        existing.setLastName(updatedContact.getLastName());
        existing.setEmail(updatedContact.getEmail());
        existing.setPhone(updatedContact.getPhone());
        existing.setCompany(updatedContact.getCompany());
        existing.setTags(updatedContact.getTags());
        existing.setGroupId(updatedContact.getGroupId());
        // Note: createdAt and userId remain unchanged
        return contactRepository.save(existing);
    }

    /**
     * Delete a contact belonging to the given user.
     */
    @Transactional
    public void deleteContact(Long id, Long userId) {
        Contact existing = getContactById(id, userId);
        contactRepository.delete(existing);
    }

    /**
     * Search contacts for a user based on optional query parameters.
     * Supported keys: firstName, lastName, email, phone, company, tags, groupId
     */
    @Transactional(readOnly = true)
    public List<Contact> searchContacts(Long userId, Map<String, String> params) {
        List<Contact> contacts = getAllContacts(userId);
        return contacts.stream()
                .filter(contact -> {
                    boolean matches = true;
                    String firstName = params.get("firstName");
                    if (firstName != null && (contact.getFirstName() == null || !contact.getFirstName().toLowerCase().contains(firstName.toLowerCase()))) {
                        matches = false;
                    }
                    String lastName = params.get("lastName");
                    if (lastName != null && (contact.getLastName() == null || !contact.getLastName().toLowerCase().contains(lastName.toLowerCase()))) {
                        matches = false;
                    }
                    String email = params.get("email");
                    if (email != null && (contact.getEmail() == null || !contact.getEmail().toLowerCase().contains(email.toLowerCase()))) {
                        matches = false;
                    }
                    String phone = params.get("phone");
                    if (phone != null && (contact.getPhone() == null || !contact.getPhone().toLowerCase().contains(phone.toLowerCase()))) {
                        matches = false;
                    }
                    String company = params.get("company");
                    if (company != null && (contact.getCompany() == null || !contact.getCompany().toLowerCase().contains(company.toLowerCase()))) {
                        matches = false;
                    }
                    String tags = params.get("tags");
                    if (tags != null && (contact.getTags() == null || !contact.getTags().toLowerCase().contains(tags.toLowerCase()))) {
                        matches = false;
                    }
                    String groupIdStr = params.get("groupId");
                    if (groupIdStr != null) {
                        try {
                            Long groupId = Long.valueOf(groupIdStr);
                            if (!groupId.equals(contact.getGroupId())) {
                                matches = false;
                            }
                        } catch (NumberFormatException e) {
                            matches = false;
                        }
                    }
                    return matches;
                })
                .collect(Collectors.toList());
    }
}