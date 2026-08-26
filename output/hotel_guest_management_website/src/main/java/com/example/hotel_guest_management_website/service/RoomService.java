package com.example.hotel_guest_management_website.service;

import com.example.hotel_guest_management_website.entity.Room;
import com.example.hotel_guest_management_website.repository.RoomRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@Transactional
public class RoomService {

    private final RoomRepository roomRepository;

    public RoomService(RoomRepository roomRepository) {
        this.roomRepository = roomRepository;
    }

    public List<Room> getAllRooms() {
        return roomRepository.findAll();
    }

    public Room getRoomById(Long id) {
        return roomRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Room not found with id: " + id));
    }

    public Room createRoom(Room room) {
        room.setActive(true);
        return roomRepository.save(room);
    }

    public Room updateRoom(Long id, Room updatedRoom) {
        Room existing = getRoomById(id);
        existing.setRoomNumber(updatedRoom.getRoomNumber());
        existing.setType(updatedRoom.getType());
        existing.setDescription(updatedRoom.getDescription());
        existing.setPricePerNight(updatedRoom.getPricePerNight());
        existing.setCapacity(updatedRoom.getCapacity());
        existing.setActive(updatedRoom.getActive());
        return roomRepository.save(existing);
    }

    public void deactivateRoom(Long id) {
        Room room = getRoomById(id);
        room.setActive(false);
        roomRepository.save(room);
    }

    public List<Room> searchRooms(String type, Integer capacity, Boolean active) {
        List<Room> rooms = roomRepository.findAll();
        return rooms.stream()
                .filter(r -> type == null || r.getType().equalsIgnoreCase(type))
                .filter(r -> capacity == null || r.getCapacity().equals(capacity))
                .filter(r -> active == null || r.getActive().equals(active))
                .collect(Collectors.toList());
    }
}
