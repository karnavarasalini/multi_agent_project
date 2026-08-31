package com.example.attendance.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.filter.CommonsRequestLoggingFilter;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

/**
 * Configuration for request logging and global error handling.
 *
 * <p>The {@link CommonsRequestLoggingFilter} logs incoming HTTP requests at INFO level.
 * The {@link GlobalExceptionHandler} captures uncaught exceptions from controllers,
 * logs them at ERROR level and returns a generic error response.
 */
@Configuration
@Slf4j
public class LoggingConfig {

    /**
     * Registers a {@link CommonsRequestLoggingFilter} bean that logs request details.
     *
     * @return the configured filter
     */
    @Bean
    public CommonsRequestLoggingFilter requestLoggingFilter() {
        CommonsRequestLoggingFilter loggingFilter = new CommonsRequestLoggingFilter();
        loggingFilter.setIncludeClientInfo(true);
        loggingFilter.setIncludeQueryString(true);
        loggingFilter.setIncludeHeaders(true);
        loggingFilter.setIncludePayload(true);
        loggingFilter.setMaxPayloadLength(10000);
        loggingFilter.setAfterMessagePrefix("[REQUEST] ");
        return loggingFilter;
    }
}

/**
 * Global exception handler that logs exceptions and returns a consistent error response.
 */
@ControllerAdvice
@Slf4j
class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Object> handleAllExceptions(Exception ex) {
        log.error("Unhandled exception occurred", ex);
        // You can customize the error body as needed
        return new ResponseEntity<>("An unexpected error occurred.", HttpStatus.INTERNAL_SERVER_ERROR);
    }
}
