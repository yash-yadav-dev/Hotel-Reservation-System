USE HotelReservationDB;

-- 1. Full reservation report (JOIN view)
SELECT * FROM vw_reservation_details ORDER BY reservation_id;

-- 2. Payment totals and outstanding/pending amounts
SELECT * FROM vw_payment_summary ORDER BY reservation_id;

-- 3. Current room status (Available / Occupied / Maintenance)
SELECT * FROM vw_room_current_status ORDER BY room_number;

-- 4. Monthly revenue report (only Paid amounts count as revenue)
SELECT * FROM vw_monthly_revenue ORDER BY revenue_year, revenue_month;

-- 5. Find rooms free for a chosen date range (change dates as needed)
CALL sp_get_available_rooms('2026-11-10', '2026-11-13');

-- 6. GROUP BY + HAVING: guests with more than one reservation
SELECT g.guest_id, g.guest_name, COUNT(r.reservation_id) AS booking_count
FROM Guests g
JOIN Reservations r ON r.guest_id = g.guest_id
GROUP BY g.guest_id, g.guest_name
HAVING COUNT(r.reservation_id) > 1;

-- 7. Subquery: rooms priced above the average room price
SELECT room_number, room_type, price_per_night
FROM Rooms
WHERE price_per_night > (SELECT AVG(price_per_night) FROM Rooms);

-- 8. Transaction demonstration (safe test: final ROLLBACK leaves no inserted row)
START TRANSACTION;
INSERT INTO Guests (guest_name, phone, email, address)
VALUES ('Transaction Demo', '9000000000', 'transaction.demo@example.com', 'Test City');
SELECT * FROM Guests WHERE email = 'transaction.demo@example.com';
ROLLBACK;

-- 9. Negative test: uncomment and run separately to see trigger reject overlap.
-- This deliberately conflicts with sample reservation 1 (room_id 2, Nov 10-13).
-- INSERT INTO Reservations (guest_id, room_id, check_in, check_out, booking_status)
-- VALUES (5, 2, '2026-11-11', '2026-11-14', 'Confirmed');
