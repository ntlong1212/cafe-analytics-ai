package com.cafe.analytics;

import jakarta.annotation.PostConstruct;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import java.util.TimeZone;

@SpringBootApplication
public class BackendServiceApplication {

    @PostConstruct
    public void init() {
        // Force JVM to use standard Vietnam time to avoid issues with Postgres TIMESTAMP column
        TimeZone.setDefault(TimeZone.getTimeZone("Asia/Ho_Chi_Minh"));
    }

    public static void main(String[] args) {
        SpringApplication.run(BackendServiceApplication.class, args);
    }

}
