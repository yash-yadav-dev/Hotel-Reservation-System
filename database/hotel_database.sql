-- Hotel Reservation Database Management System
-- Run this entire file in MySQL Workbench.

CREATE DATABASE IF NOT EXISTS HotelReservationDB;
USE HotelReservationDB;

-- Drop child tables first so this script can be safely rerun.
DROP TABLE IF EXISTS Payments;
DROP TABLE IF EXISTS Reservations;
DROP TABLE IF EXISTS Rooms;
DROP TABLE IF EXISTS Guests;

CREATE TABLE Guests (
    guest_id INT AUTO_INCREMENT PRIMARY KEY,
    guest_name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    email VARCHAR(100) UNIQUE,
    address VARCHAR(200)
);

CREATE TABLE Rooms (
    room_id INT AUTO_INCREMENT PRIMARY KEY,
    room_number VARCHAR(10) NOT NULL UNIQUE,
    room_type VARCHAR(30) NOT NULL,
    price_per_night DECIMAL(10,2) NOT NULL,
    room_status VARCHAR(20) NOT NULL DEFAULT 'Available',
    CONSTRAINT chk_room_price CHECK (price_per_night > 0),
    CONSTRAINT chk_room_status CHECK (room_status IN ('Available', 'Maintenance'))
);

CREATE TABLE Reservations (
    reservation_id INT AUTO_INCREMENT PRIMARY KEY,
    guest_id INT NOT NULL,
    room_id INT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    booking_status VARCHAR(20) NOT NULL DEFAULT 'Confirmed',
    CONSTRAINT fk_res_guest FOREIGN KEY (guest_id)
        REFERENCES Guests(guest_id),
    CONSTRAINT fk_res_room FOREIGN KEY (room_id)
        REFERENCES Rooms(room_id),
    CONSTRAINT chk_res_dates CHECK (check_out > check_in),
    CONSTRAINT chk_booking_status CHECK (booking_status IN ('Confirmed', 'Cancelled', 'Completed'))
);

CREATE TABLE Payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    reservation_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_date DATE NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'Paid',
    CONSTRAINT fk_payment_reservation FOREIGN KEY (reservation_id)
        REFERENCES Reservations(reservation_id),
    CONSTRAINT chk_payment_amount CHECK (amount > 0),
    CONSTRAINT chk_payment_method CHECK (payment_method IN ('Cash', 'Card', 'UPI', 'Net Banking')),
    CONSTRAINT chk_payment_status CHECK (payment_status IN ('Paid', 'Pending', 'Refunded'))
);

-- Sample guests
INSERT INTO Guests (guest_name, phone, email, address) VALUES
('Aarav Sharma', '9876543210', 'aarav@example.com', 'Chandigarh'),
('Meera Singh', '9876501234', 'meera@example.com', 'Delhi'),
('Kabir Verma', '9812345670', 'kabir@example.com', 'Jaipur'),
('Ananya Das', '9898765432', 'ananya@example.com', 'Guwahati'),
('Rohan Kapoor', '9123456780', 'rohan@example.com', 'Mohali');

-- Sample rooms
INSERT INTO Rooms (room_number, room_type, price_per_night, room_status) VALUES
('101', 'Single', 1800.00, 'Available'),
('102', 'Double', 2500.00, 'Available'),
('103', 'Deluxe', 3500.00, 'Available'),
('201', 'Double', 2700.00, 'Available'),
('202', 'Suite', 5500.00, 'Available'),
('203', 'Deluxe', 3800.00, 'Maintenance');

-- Sample reservations (dates are examples; edit them if desired)
INSERT INTO Reservations (guest_id, room_id, check_in, check_out, booking_status) VALUES
(1, 2, '2026-11-10', '2026-11-13', 'Confirmed'),
(2, 3, '2026-11-12', '2026-11-15', 'Confirmed'),
(3, 1, '2026-10-20', '2026-10-22', 'Completed'),
(4, 5, '2026-11-18', '2026-11-20', 'Confirmed');

-- Sample payments
INSERT INTO Payments (reservation_id, amount, payment_date, payment_method, payment_status) VALUES
(1, 2500.00, '2026-11-03', 'UPI', 'Paid'),
(1, 5000.00, '2026-11-03', 'Card', 'Pending'),
(2, 10500.00, '2026-11-03', 'UPI', 'Paid'),
(3, 3600.00, '2026-10-20', 'Cash', 'Paid');

-- Useful demonstration queries
-- 1. Show reservations with guest and room details.
SELECT r.reservation_id, g.guest_name, rm.room_number, rm.room_type,
       r.check_in, r.check_out, r.booking_status
FROM Reservations r
JOIN Guests g ON r.guest_id = g.guest_id
JOIN Rooms rm ON r.room_id = rm.room_id;

-- 2. Total amount paid per reservation.
SELECT reservation_id, SUM(amount) AS total_payment
FROM Payments
WHERE payment_status = 'Paid'
GROUP BY reservation_id;

-- 3. Number of rooms in each category.
SELECT room_type, COUNT(*) AS total_rooms
FROM Rooms
GROUP BY room_type;

-- 4. Total paid revenue.
SELECT SUM(amount) AS total_revenue
FROM Payments
WHERE payment_status = 'Paid';
