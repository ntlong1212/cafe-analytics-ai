package com.cafe.analytics.service;

import com.cafe.analytics.dto.RecognitionResult;
import com.cafe.analytics.model.Customer;
import com.cafe.analytics.model.Staff;
import com.cafe.analytics.repository.CustomerRepository;
import com.cafe.analytics.repository.StaffRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class FaceRecognitionService {

    private final CustomerRepository customerRepository;
    private final StaffRepository staffRepository;
    
    // Thresholds for Cosine Similarity
    private static final double STAFF_SIMILARITY_THRESHOLD = 0.76; // Giảm xuống 0.76 cho góc quay từ trên xuống của camera an ninh
    private static final double CUSTOMER_SIMILARITY_THRESHOLD = 0.70;

    /**
     * Finds identifying old customer/staff or registers a new customer based on Face Embeddings array
     * Uses Two-Tier Scanning: Staff First -> Then Customers
     */
    @Transactional
    public RecognitionResult processFaceVector(double[] faceVector, String gender, String ageRange) {
        if (faceVector == null || faceVector.length == 0) {
            return null; // No face data provided
        }

        // TIER 1: Scan Staff table first
        List<Staff> allStaff = staffRepository.findAll();
        Staff matchedStaff = null;
        double maxStaffSimilarity = -1.0;

        for (Staff staff : allStaff) {
            // Only compare against active staff
            if (staff.getIsActive() != null && staff.getIsActive()) {
                double[] oldVector = staff.getFaceVector();
                if (oldVector != null && oldVector.length == faceVector.length) {
                    double similarity = calculateCosineSimilarity(faceVector, oldVector);
                    if (similarity > maxStaffSimilarity && similarity >= STAFF_SIMILARITY_THRESHOLD) {
                        maxStaffSimilarity = similarity;
                        matchedStaff = staff;
                    }
                }
            }
        }

        if (matchedStaff != null) {
            log.info("Recognized Employee: [ID: {}, Role: {}] with similarity {}%", 
                matchedStaff.getId(), matchedStaff.getRole(), String.format("%.2f", maxStaffSimilarity * 100));
            return RecognitionResult.asStaff(matchedStaff.getId());
        }

        // TIER 2: Not a Staff, Scan Customers table
        List<Customer> allCustomers = customerRepository.findAll();
        Customer matchedCustomer = null;
        double maxCustomerSimilarity = -1.0;

        for (Customer oldCustomer : allCustomers) {
            double[] oldVector = oldCustomer.getFaceVector();
            if (oldVector != null && oldVector.length == faceVector.length) {
                double similarity = calculateCosineSimilarity(faceVector, oldVector);
                if (similarity > maxCustomerSimilarity && similarity >= CUSTOMER_SIMILARITY_THRESHOLD) {
                    maxCustomerSimilarity = similarity;
                    matchedCustomer = oldCustomer;
                }
            }
        }

        if (matchedCustomer != null) {
            log.info("Recognized returning customer ID: {} with similarity {}%", 
                matchedCustomer.getId(), String.format("%.2f", maxCustomerSimilarity * 100));
            matchedCustomer.setVisitCount(matchedCustomer.getVisitCount() + 1);
            if (gender != null && !gender.equals("Unknown")) {
               matchedCustomer.setPredictedGender(gender);
            }
            if (ageRange != null && !ageRange.equals("Unknown")) {
               matchedCustomer.setPredictedAgeRange(ageRange);
            }
            return RecognitionResult.asCustomer(customerRepository.save(matchedCustomer).getId());
        } else {
            log.info("New customer detected. Saving to database.");
            Customer newCustomer = new Customer();
            newCustomer.setFaceVector(faceVector);
            newCustomer.setPredictedGender(gender);
            newCustomer.setPredictedAgeRange(ageRange);
            newCustomer.setVisitCount(1);
            return RecognitionResult.asCustomer(customerRepository.save(newCustomer).getId());
        }
    }

    /**
     * Compute Cosine Similarity between two arrays.
     */
    private double calculateCosineSimilarity(double[] vectorA, double[] vectorB) {
        double dotProduct = 0.0;
        double normA = 0.0;
        double normB = 0.0;
        for (int i = 0; i < vectorA.length; i++) {
            dotProduct += vectorA[i] * vectorB[i];
            normA += Math.pow(vectorA[i], 2);
            normB += Math.pow(vectorB[i], 2);
        }
        
        if (normA == 0.0 || normB == 0.0) {
            return 0.0;
        }
        return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
    }
}
