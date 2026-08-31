package com.example.studentattendancemanagementsystem.specification;

import com.example.studentattendancemanagementsystem.entity.Student;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.util.StringUtils;

public class StudentSpecification {

    public static Specification<Student> withFilters(String firstName, String lastName, String email) {
        return (root, query, criteriaBuilder) -> {
            var predicate = criteriaBuilder.conjunction();
            if (StringUtils.hasText(firstName)) {
                predicate.getExpressions().add(
                    criteriaBuilder.like(
                        criteriaBuilder.lower(root.get("firstName")),
                        "%" + firstName.toLowerCase() + "%"
                    )
                );
            }
            if (StringUtils.hasText(lastName)) {
                predicate.getExpressions().add(
                    criteriaBuilder.like(
                        criteriaBuilder.lower(root.get("lastName")),
                        "%" + lastName.toLowerCase() + "%"
                    )
                );
            }
            if (StringUtils.hasText(email)) {
                predicate.getExpressions().add(
                    criteriaBuilder.like(
                        criteriaBuilder.lower(root.get("email")),
                        "%" + email.toLowerCase() + "%"
                    )
                );
            }
            return predicate;
        };
    }
}
