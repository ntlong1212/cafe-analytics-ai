-- ==============================================================================
-- Cafe Analytics System - Database Initialization Script
-- Engine: PostgreSQL
-- ==============================================================================

-- 1. Create tables for master data
CREATE TABLE IF NOT EXISTS staff (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL, -- e.g., 'BARISTA', 'WAITER'
    face_encoding_id VARCHAR(255) UNIQUE, -- ID linking to vector database if needed
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    face_vector_id VARCHAR(255) UNIQUE, -- To recognize returning customers without storing real photos
    predicted_gender VARCHAR(10), -- 'MALE', 'FEMALE'
    predicted_age_range VARCHAR(20), -- e.g., '18-25', '26-35'
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    visit_count INT DEFAULT 1
);

-- 2. Define ENUMs (or check constraints) for Event Types to ensure data integrity
-- Types of events the AI Service can emit
CREATE TYPE event_category AS ENUM (
    'STAFF_ARRIVE', 'STAFF_LEAVE',
    'STAFF_PREPARE_DRINK', 'STAFF_CLEANING', 'STAFF_SERVING', 'STAFF_IDLE',
    'CUSTOMER_ENTER', 'CUSTOMER_EXIT', 'CUSTOMER_SIT_DOWN', 'CUSTOMER_ORDER'
);

-- 3. Create the main time-series event log table
CREATE TABLE IF NOT EXISTS ai_events_log (
    id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMP NOT NULL,
    event_type event_category NOT NULL,
    
    -- Polymorphic relationship (Event can belong to a staff or a customer)
    staff_id INT REFERENCES staff(id) ON DELETE SET NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    
    -- Location Context
    camera_id VARCHAR(50),      -- e.g., 'CAM_DOOR', 'CAM_BAR'
    zone_id VARCHAR(50),        -- e.g., 'TABLE_1', 'COUNTER'
    
    -- Additional metadata (JSON for flexibility)
    metadata JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance on time-series queries
CREATE INDEX idx_events_time ON ai_events_log(event_time);
CREATE INDEX idx_events_customer ON ai_events_log(customer_id);
CREATE INDEX idx_events_staff ON ai_events_log(staff_id);


-- 4. Daily Aggregation Table (populated by a background job or DB trigger later)
CREATE TABLE IF NOT EXISTS daily_staff_metrics (
    id SERIAL PRIMARY KEY,
    record_date DATE NOT NULL,
    staff_id INT REFERENCES staff(id),
    total_hours_worked NUMERIC(5,2) DEFAULT 0,
    time_spent_preparing_drinks NUMERIC(5,2) DEFAULT 0, -- in minutes
    time_spent_cleaning NUMERIC(5,2) DEFAULT 0,
    time_spent_serving NUMERIC(5,2) DEFAULT 0,
    time_spent_idle NUMERIC(5,2) DEFAULT 0,
    UNIQUE(record_date, staff_id)
);

CREATE TABLE IF NOT EXISTS daily_customer_metrics (
    id SERIAL PRIMARY KEY,
    record_date DATE UNIQUE NOT NULL,
    total_new_customers INT DEFAULT 0,
    total_returning_customers INT DEFAULT 0,
    avg_dwell_time_minutes NUMERIC(5,2) DEFAULT 0
);
