package com.example.hotelbookingwebsite.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import com.example.hotelbookingwebsite.entity.Booking;
import com.example.hotelbookingwebsite.entity.Hotel;
import com.example.hotelbookingwebsite.entity.Room;
import com.example.hotelbookingwebsite.entity.User;

import javax.mail.MessagingException;
import javax.mail.internet.MimeMessage;
import java.time.format.DateTimeFormatter;

@Service
public class EmailService {

    private final JavaMailSender mailSender;

    @Value("${spring.mail.username}")
    private String fromAddress;

    public EmailService(JavaMailSender mailSender) {
        this.mailSender = mailSender;
    }

    @Async
    public void sendBookingConfirmation(Booking booking) {
        User user = booking.getUser();
        Room room = booking.getRoom();
        Hotel hotel = room.getHotel();

        String subject = "Booking Confirmation - " + hotel.getName();
        String to = user.getEmail();
        String content = buildEmailContent(booking, hotel, room);

        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true);
            helper.setFrom(fromAddress);
            helper.setTo(to);
            helper.setSubject(subject);
            helper.setText(content, true); // true = HTML
            mailSender.send(message);
        } catch (MessagingException e) {
            // Simple error handling; replace with proper logging in production
            e.printStackTrace();
        }
    }

    private String buildEmailContent(Booking booking, Hotel hotel, Room room) {
        DateTimeFormatter dateFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd");
        StringBuilder sb = new StringBuilder();
        sb.append("<p>Dear ")
          .append(booking.getUser().getFirstName())
          .append(",</p>");
        sb.append("<p>Thank you for your reservation. Here are your booking details:</p>");
        sb.append("<ul>");
        sb.append("<li>Hotel: ").append(hotel.getName()).append("</li>");
        sb.append("<li>Address: ")
          .append(hotel.getAddress()).append(", ")
          .append(hotel.getCity()).append(", ")
          .append(hotel.getCountry()).append("</li>");
        sb.append("<li>Room Type: ").append(room.getType()).append("</li>");
        sb.append("<li>Check‑in: ")
          .append(booking.getCheckIn().format(dateFormatter)).append("</li>");
        sb.append("<li>Check‑out: ")
          .append(booking.getCheckOut().format(dateFormatter)).append("</li>");
        sb.append("<li>Total Price: $").append(booking.getTotalPrice()).append("</li>");
        sb.append("</ul>");
        sb.append("<p>We look forward to hosting you!</p>");
        sb.append("<p>Best regards,<br/>Hotel Booking Team</p>");
        return sb.toString();
    }
}
