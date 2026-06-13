-- ==========================================
-- FILE: seed.sql
-- PURPOSE: Data Manipulation, Resets, and Testing (DML)
-- ==========================================

USE sentinel_db;

-- ─── SECTION 1: SYSTEM INITIALIZATION  ───

INSERT IGNORE INTO monitoring_targets (location_name, state) VALUES 
('Kolkata', 'West Bengal'),
('South 24 Parganas', 'West Bengal'),
('Howrah', 'West Bengal'),
('Mumbai', 'Maharashtra'),
('Guwahati', 'Assam'),
('Bengaluru', 'Karnataka');


INSERT IGNORE INTO ngo_access (ngo_id, ngo_name, governed_location_id) VALUES 
('NGO_KOL_01', 'Kolkata Safety Watch', 1);


-- ─── SECTION 2: THE EMERGENCY RESCUE SWITCHES (Run as needed) ───

-- SWITCH A
UPDATE safety_signals SET category = 'Unclassified', is_relevant = 1 WHERE category = 'Unclassified';

-- SWITCH B:
-- SET FOREIGN_KEY_CHECKS = 0;
-- TRUNCATE TABLE safety_signals;
-- TRUNCATE TABLE monitoring_targets;
-- TRUNCATE TABLE ngo_access;
-- SET FOREIGN_KEY_CHECKS = 1;

TRUNCATE safety_signals;
DELETE FROM monitoring_targets WHERE location_name NOT IN ('Kolkata', 'Howrah');
SELECT * FROM monitoring_targets;
INSERT IGNORE INTO monitoring_targets (location_name, state) VALUES ('Howrah', 'West Bengal');
UPDATE safety_signals 
SET is_relevant = FLOOR(RAND()*2),
    is_regional = FLOOR(RAND()*2),
    category = ELT(FLOOR(RAND()*7)+1, 'Fire', 'Accident', 'Protest', 'Crime', 'Disaster', 'Infrastructure Failure', 'Human Security Issue')
WHERE category = 'Unclassified';
SELECT * FROM safety_signals;

USE sentinel_db;

-- 1. UPGRADE SCHEMA FOR STAGE 4 MATH
ALTER TABLE safety_signals ADD COLUMN sentiment_negative FLOAT AFTER compound_score;

-- 2. WIPE ARCHITECTURE DATA (Safely bypassing foreign key blocks)
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE safety_signals;
TRUNCATE TABLE ngo_access;
TRUNCATE TABLE monitoring_targets;
SET FOREIGN_KEY_CHECKS = 1;

-- 3. REPOPULATE PRISTINE WORKSPACE TARGETS
INSERT INTO monitoring_targets (id, location_name, state) VALUES 
(1, 'Kolkata', 'West Bengal'),
(2, 'Howrah', 'West Bengal');

INSERT IGNORE INTO ngo_access (ngo_id, ngo_name, governed_location_id) VALUES 
('NGO_KOL_01', 'Kolkata Safety Watch', 1);

-- 4. VERIFY LOGISTICAL TARGETS ARE LIVE
SELECT * FROM monitoring_targets;

-- ========================================================
-- TARGET FILE: seed.sql
-- EXECUTION: Run inside your VSCode Local Host Connection
-- ========================================================
CREATE DATABASE IF NOT EXISTS sentinel_db;
USE sentinel_db;

-- 1. Safe complete purge of any existing tables
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS predicted_safety_scores;
DROP TABLE IF EXISTS ngo_access;
DROP TABLE IF EXISTS safety_signals;
DROP TABLE IF EXISTS monitoring_targets;
SET FOREIGN_KEY_CHECKS = 1;

-- 2. Create the scalable multi-location structure
CREATE TABLE monitoring_targets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    location_name VARCHAR(100) UNIQUE NOT NULL,
    state VARCHAR(50) NOT NULL,
    latitude DECIMAL(10, 8) NULL,
    longitude DECIMAL(11, 8) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ngo_access (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ngo_id VARCHAR(50) NOT NULL,
    ngo_name VARCHAR(100) NOT NULL,
    governed_location_id INT NOT NULL,
    FOREIGN KEY (governed_location_id) REFERENCES monitoring_targets(id) ON DELETE CASCADE,
    UNIQUE KEY unique_ngo_loc (ngo_id, governed_location_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE safety_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(550) NOT NULL,
    source VARCHAR(150),
    timestamp DATETIME NOT NULL,
    location_id INT NOT NULL,
    compound_score FLOAT DEFAULT 0.0,
    sentiment_negative FLOAT DEFAULT 0.0,
    category VARCHAR(50) DEFAULT 'Unclassified',
    is_relevant TINYINT DEFAULT 1,
    is_regional TINYINT DEFAULT 0,
    FOREIGN KEY (location_id) REFERENCES monitoring_targets(id) ON DELETE CASCADE,
    UNIQUE KEY unique_title_loc (title(255), location_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE predicted_safety_scores (
    location_id INT PRIMARY KEY,
    current_hazard_index FLOAT NOT NULL,
    severity_tier VARCHAR(20) NOT NULL,
    active_signals_count INT DEFAULT 0,
    trajectory VARCHAR(50) NOT NULL,
    primary_threat_distribution TEXT NOT NULL, 
    tactical_action_steps TEXT NOT NULL,
    last_updated DATETIME NOT NULL,
    FOREIGN KEY (location_id) REFERENCES monitoring_targets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Ingest Pristine Demo Targets 
INSERT INTO monitoring_targets (id, location_name, state, latitude, longitude) VALUES 
(1, 'Kolkata', 'West Bengal', 22.572646, 88.363895),
(2, 'Howrah', 'West Bengal', 22.595770, 88.263640);

-- 4. Map your hardcoded test user (NGO_KOL_01) to BOTH jurisdictions
INSERT INTO ngo_access (ngo_id, ngo_name, governed_location_id) VALUES 
('NGO_KOL_01', 'Kolkata Safety Watch', 1),
('NGO_KOL_01', 'Kolkata Safety Watch', 2);

-- 5. Verification Print statement
SELECT mt.location_name, na.ngo_id FROM monitoring_targets mt 
JOIN ngo_access na ON mt.id = na.governed_location_id;