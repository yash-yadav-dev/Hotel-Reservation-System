-- HOTEL RESERVATION DBMS - COMPLETE DATABASE UPGRADE
-- Target: MySQL 8.0+ (tested design for MySQL Community Server 8.0.46)
-- IMPORTANT: Run this against the EXISTING HotelReservationDB database.
-- This script does NOT drop tables or delete existing rows.

USE HotelReservationDB;

-- -----------------------------------------------------------------------------
-- 1. Supporting indexes (created only when not already present)
-- -----------------------------------------------------------------------------
SET @idx_exists = (SELECT COUNT(*) FROM information_schema.statistics
                   WHERE table_schema = DATABASE() AND table_name = 'Reservations'
                     AND index_name = 'idx_res_room_status_dates');
SET @ddl = IF(@idx_exists = 0,
  'CREATE INDEX idx_res_room_status_dates ON Reservations (room_id, booking_status, check_in, check_out)',
  'SELECT ''Index idx_res_room_status_dates already exists'' AS info');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @idx_exists = (SELECT COUNT(*) FROM information_schema.statistics
                   WHERE table_schema = DATABASE() AND table_name = 'Reservations'
                     AND index_name = 'idx_res_guest_checkin');
SET @ddl = IF(@idx_exists = 0,
  'CREATE INDEX idx_res_guest_checkin ON Reservations (guest_id, check_in)',
  'SELECT ''Index idx_res_guest_checkin already exists'' AS info');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @idx_exists = (SELECT COUNT(*) FROM information_schema.statistics
                   WHERE table_schema = DATABASE() AND table_name = 'Payments'
                     AND index_name = 'idx_pay_res_status_date');
SET @ddl = IF(@idx_exists = 0,
  'CREATE INDEX idx_pay_res_status_date ON Payments (reservation_id, payment_status, payment_date)',
  'SELECT ''Index idx_pay_res_status_date already exists'' AS info');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- -----------------------------------------------------------------------------
-- 2. Reporting views
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_reservation_details AS
SELECT r.reservation_id, g.guest_id, g.guest_name, g.phone, g.email,
       rm.room_id, rm.room_number, rm.room_type, rm.price_per_night,
       r.check_in, r.check_out, DATEDIFF(r.check_out, r.check_in) AS nights,
       (DATEDIFF(r.check_out, r.check_in) * rm.price_per_night) AS booking_total,
       r.booking_status
FROM Reservations r
JOIN Guests g ON g.guest_id = r.guest_id
JOIN Rooms rm ON rm.room_id = r.room_id;

CREATE OR REPLACE VIEW vw_payment_summary AS
SELECT r.reservation_id, g.guest_name, rm.room_number,
       COALESCE(SUM(CASE WHEN p.payment_status = 'Paid' THEN p.amount ELSE 0 END), 0) AS total_paid,
       COALESCE(SUM(CASE WHEN p.payment_status = 'Pending' THEN p.amount ELSE 0 END), 0) AS total_pending,
       COALESCE(SUM(CASE WHEN p.payment_status = 'Refunded' THEN p.amount ELSE 0 END), 0) AS total_refunded,
       (DATEDIFF(r.check_out, r.check_in) * rm.price_per_night) AS booking_total
FROM Reservations r
JOIN Guests g ON g.guest_id = r.guest_id
JOIN Rooms rm ON rm.room_id = r.room_id
LEFT JOIN Payments p ON p.reservation_id = r.reservation_id
GROUP BY r.reservation_id, g.guest_name, rm.room_number,
         r.check_in, r.check_out, rm.price_per_night;

CREATE OR REPLACE VIEW vw_room_current_status AS
SELECT rm.room_id, rm.room_number, rm.room_type, rm.price_per_night,
       CASE
         WHEN rm.room_status = 'Maintenance' THEN 'Maintenance'
         WHEN EXISTS (
           SELECT 1 FROM Reservations r
           WHERE r.room_id = rm.room_id
             AND r.booking_status = 'Confirmed'
             AND CURDATE() >= r.check_in AND CURDATE() < r.check_out
         ) THEN 'Occupied'
         ELSE 'Available'
       END AS current_status
FROM Rooms rm;

CREATE OR REPLACE VIEW vw_monthly_revenue AS
SELECT YEAR(payment_date) AS revenue_year,
       MONTH(payment_date) AS revenue_month,
       DATE_FORMAT(payment_date, '%Y-%m') AS revenue_period,
       SUM(CASE WHEN payment_status = 'Paid' THEN amount ELSE 0 END) AS paid_revenue,
       SUM(CASE WHEN payment_status = 'Pending' THEN amount ELSE 0 END) AS pending_amount,
       COUNT(CASE WHEN payment_status = 'Paid' THEN 1 END) AS paid_transactions
FROM Payments
GROUP BY YEAR(payment_date), MONTH(payment_date), DATE_FORMAT(payment_date, '%Y-%m');

-- -----------------------------------------------------------------------------
-- 3. Triggers: enforce booking rules even when SQL is entered outside the GUI
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_reservations_before_insert;
DROP TRIGGER IF EXISTS trg_reservations_before_update;

DELIMITER $$
CREATE TRIGGER trg_reservations_before_insert
BEFORE INSERT ON Reservations
FOR EACH ROW
BEGIN
    IF NEW.check_out <= NEW.check_in THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Check-out date must be later than check-in date.';
    END IF;

    IF NEW.booking_status = 'Confirmed' THEN
        IF EXISTS (SELECT 1 FROM Rooms
                   WHERE room_id = NEW.room_id AND room_status = 'Maintenance') THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'A room under maintenance cannot be booked.';
        END IF;

        IF EXISTS (SELECT 1 FROM Reservations
                   WHERE room_id = NEW.room_id
                     AND booking_status = 'Confirmed'
                     AND check_in < NEW.check_out
                     AND check_out > NEW.check_in) THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Room is already reserved for overlapping dates.';
        END IF;
    END IF;
END$$

CREATE TRIGGER trg_reservations_before_update
BEFORE UPDATE ON Reservations
FOR EACH ROW
BEGIN
    IF NEW.check_out <= NEW.check_in THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Check-out date must be later than check-in date.';
    END IF;

    IF NEW.booking_status = 'Confirmed' THEN
        IF EXISTS (SELECT 1 FROM Rooms
                   WHERE room_id = NEW.room_id AND room_status = 'Maintenance') THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'A room under maintenance cannot be booked.';
        END IF;

        IF EXISTS (SELECT 1 FROM Reservations
                   WHERE room_id = NEW.room_id
                     AND reservation_id <> NEW.reservation_id
                     AND booking_status = 'Confirmed'
                     AND check_in < NEW.check_out
                     AND check_out > NEW.check_in) THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Room is already reserved for overlapping dates.';
        END IF;
    END IF;
END$$
DELIMITER ;

-- -----------------------------------------------------------------------------
-- 4. Stored procedures: transactional booking and payment operations
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_create_reservation;
DROP PROCEDURE IF EXISTS sp_record_payment;
DROP PROCEDURE IF EXISTS sp_get_available_rooms;

DELIMITER $$
CREATE PROCEDURE sp_create_reservation(
    IN p_guest_id INT,
    IN p_room_id INT,
    IN p_check_in DATE,
    IN p_check_out DATE,
    IN p_booking_status VARCHAR(20),
    OUT p_reservation_id INT
)
BEGIN
    DECLARE v_room_status VARCHAR(20);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF p_check_out <= p_check_in THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Check-out date must be later than check-in date.';
    END IF;
    IF p_booking_status NOT IN ('Confirmed', 'Cancelled', 'Completed') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Invalid booking status.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM Guests WHERE guest_id = p_guest_id) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Selected guest does not exist.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM Rooms WHERE room_id = p_room_id) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Selected room does not exist.';
    END IF;

    START TRANSACTION;
    -- Serializes bookings for the same room through this procedure.
    SELECT room_status INTO v_room_status
    FROM Rooms WHERE room_id = p_room_id FOR UPDATE;

    IF p_booking_status = 'Confirmed' AND v_room_status <> 'Available' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Selected room is not available for booking.';
    END IF;

    IF p_booking_status = 'Confirmed' AND EXISTS (
        SELECT 1 FROM Reservations
        WHERE room_id = p_room_id
          AND booking_status = 'Confirmed'
          AND check_in < p_check_out
          AND check_out > p_check_in
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Room is already reserved for overlapping dates.';
    END IF;

    INSERT INTO Reservations (guest_id, room_id, check_in, check_out, booking_status)
    VALUES (p_guest_id, p_room_id, p_check_in, p_check_out, p_booking_status);
    SET p_reservation_id = LAST_INSERT_ID();
    COMMIT;
END$$

CREATE PROCEDURE sp_record_payment(
    IN p_reservation_id INT,
    IN p_amount DECIMAL(10,2),
    IN p_payment_date DATE,
    IN p_payment_method VARCHAR(30),
    IN p_payment_status VARCHAR(20)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF p_amount <= 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Payment amount must be greater than zero.';
    END IF;
    IF p_payment_method NOT IN ('Cash', 'Card', 'UPI', 'Net Banking') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Invalid payment method.';
    END IF;
    IF p_payment_status NOT IN ('Paid', 'Pending', 'Refunded') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Invalid payment status.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM Reservations WHERE reservation_id = p_reservation_id) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Selected reservation does not exist.';
    END IF;

    START TRANSACTION;
    INSERT INTO Payments (reservation_id, amount, payment_date, payment_method, payment_status)
    VALUES (p_reservation_id, p_amount, p_payment_date, p_payment_method, p_payment_status);
    COMMIT;
END$$

CREATE PROCEDURE sp_get_available_rooms(
    IN p_check_in DATE,
    IN p_check_out DATE
)
BEGIN
    IF p_check_out <= p_check_in THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Check-out date must be later than check-in date.';
    END IF;

    SELECT rm.room_id, rm.room_number, rm.room_type, rm.price_per_night
    FROM Rooms rm
    WHERE rm.room_status = 'Available'
      AND NOT EXISTS (
          SELECT 1 FROM Reservations r
          WHERE r.room_id = rm.room_id
            AND r.booking_status = 'Confirmed'
            AND r.check_in < p_check_out
            AND r.check_out > p_check_in
      )
    ORDER BY rm.room_number;
END$$
DELIMITER ;

-- -----------------------------------------------------------------------------
-- 5. Quick verification: these result sets should return objects/records
-- -----------------------------------------------------------------------------
SHOW FULL TABLES WHERE Table_type = 'VIEW';
SHOW TRIGGERS;
SHOW PROCEDURE STATUS WHERE Db = 'HotelReservationDB';
SELECT * FROM vw_room_current_status ORDER BY room_number;
SELECT * FROM vw_payment_summary ORDER BY reservation_id;
