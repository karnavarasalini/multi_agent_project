package com.example.studentattendancemanagementsystem.dto;

import lombok.Data;
import javax.validation.constraints.Email;
import javax.validation.constraints.NotBlank;

/**
 * Data Transfer Object for creating/updating a Student.
 * Bean Validation annotations ensure required fields are provided and valid.
 */
@Data
public class StudentDto {

    @NotBlank(message = "First name is required")
    private String firstName;

    @NotBlank(message = "Last name is required")
    private String lastName;

    @NotBlank(message = "Email is required")
    @Email(message = "Email should be valid")
    private String email;

    @NotBlank(message = "Enrollment number is required")
    private String enrollmentNumber;
}
