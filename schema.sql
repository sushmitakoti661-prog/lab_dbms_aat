CREATE DATABASE IF NOT EXISTS smart_lab_db;
USE smart_lab_db;

-- Users Table
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'student', 'technician') NOT NULL
);

-- Labs Table
CREATE TABLE labs (
    lab_id INT AUTO_INCREMENT PRIMARY KEY,
    lab_name VARCHAR(100) NOT NULL,
    location VARCHAR(100) NOT NULL
);

-- Equipments Table
CREATE TABLE equipments (
    equipment_id INT AUTO_INCREMENT PRIMARY KEY,
    lab_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    status ENUM('working', 'damaged', 'under_repair') DEFAULT 'working',
    FOREIGN KEY (lab_id) REFERENCES labs(lab_id) ON DELETE CASCADE
);

-- Complaints Table
CREATE TABLE complaints (
    complaint_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    equipment_id INT NOT NULL,
    description TEXT NOT NULL,
    status ENUM('open', 'assigned', 'resolved') DEFAULT 'open',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (equipment_id) REFERENCES equipments(equipment_id) ON DELETE CASCADE
);

-- Technicians Table
CREATE TABLE technicians (
    technician_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    specialization VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Maintenance Requests Table
CREATE TABLE maintenance_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id INT NOT NULL,
    technician_id INT NOT NULL,
    status ENUM('pending', 'in_progress', 'completed') DEFAULT 'pending',
    remarks TEXT,
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    FOREIGN KEY (technician_id) REFERENCES technicians(technician_id) ON DELETE CASCADE
);

-- Sample Data
INSERT INTO users (name, email, password, role) VALUES
('Admin User', 'admin@lab.com', 'pbkdf2:sha256:260000$placeholder', 'admin'),
('John Student', 'student@lab.com', 'pbkdf2:sha256:260000$placeholder', 'student'),
('Mike Tech', 'tech@lab.com', 'pbkdf2:sha256:260000$placeholder', 'technician');

INSERT INTO labs (lab_name, location) VALUES
('CS Lab 1', 'Block A, Floor 1'),
('CS Lab 2', 'Block A, Floor 2'),
('Electronics Lab', 'Block B, Floor 1');

INSERT INTO equipments (lab_id, name, type, status) VALUES
(1, 'Dell Laptop 01', 'Laptop', 'working'),
(1, 'Dell Laptop 02', 'Laptop', 'damaged'),
(1, 'Projector', 'Projector', 'working'),
(2, 'HP Desktop 01', 'Desktop', 'under_repair'),
(2, 'HP Desktop 02', 'Desktop', 'working'),
(3, 'Oscilloscope', 'Instrument', 'working'),
(3, 'Function Generator', 'Instrument', 'damaged');