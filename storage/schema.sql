
-- ==========================================
-- FILE: schema.sql
-- PURPOSE: Pure Database Structural Blueprint (DDL)
-- ==========================================

CREATE DATABASE IF NOT EXISTS sentinel_db;
USE sentinel_db;

-- 1. Create Monitoring Targets Table
CREATE TABLE IF NOT EXISTS monitoring_targets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    location_name VARCHAR(100) UNIQUE NOT NULL,
    state VARCHAR(50) DEFAULT 'West Bengal',
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8)
);

-- 2. Create Safety Signals (News/Articles) Table
CREATE TABLE IF NOT EXISTS safety_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) UNIQUE,
    source VARCHAR(100),
    timestamp DATETIME,
    location_id INT,
    compound_score FLOAT,
    category VARCHAR(50) DEFAULT 'Unclassified',
    is_relevant TINYINT DEFAULT 1,
    is_regional TINYINT DEFAULT 0,
    FOREIGN KEY (location_id) REFERENCES monitoring_targets(id)
);

-- 3. Create NGO Access Table (For the Streamlit UI dashboard)
CREATE TABLE IF NOT EXISTS ngo_access (
    ngo_id VARCHAR(20) PRIMARY KEY,
    ngo_name VARCHAR(100),
    governed_location_id INT,
    FOREIGN KEY (governed_location_id) REFERENCES monitoring_targets(id)
);

