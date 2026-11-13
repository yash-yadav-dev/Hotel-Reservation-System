"""Local SQLite storage for Hotel Reservation DBMS.

No MySQL server, account, password, or external database driver is required.
The database file is created automatically in the project's data/ directory.
"""
from pathlib import Path
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "hotel_reservation.db"

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS Guests (
    guest_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT UNIQUE,
    address TEXT
);
CREATE TABLE IF NOT EXISTS Rooms (
    room_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_number TEXT NOT NULL UNIQUE,
    room_type TEXT NOT NULL,
    price_per_night NUMERIC NOT NULL CHECK(price_per_night > 0),
    room_status TEXT NOT NULL DEFAULT 'Available'
        CHECK(room_status IN ('Available', 'Maintenance'))
);
CREATE TABLE IF NOT EXISTS Reservations (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    check_in TEXT NOT NULL,
    check_out TEXT NOT NULL,
    booking_status TEXT NOT NULL DEFAULT 'Confirmed'
        CHECK(booking_status IN ('Confirmed', 'Cancelled', 'Completed')),
    CHECK(check_out > check_in),
    FOREIGN KEY(guest_id) REFERENCES Guests(guest_id),
    FOREIGN KEY(room_id) REFERENCES Rooms(room_id)
);
CREATE TABLE IF NOT EXISTS Payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL,
    amount NUMERIC NOT NULL CHECK(amount > 0),
    payment_date TEXT NOT NULL,
    payment_method TEXT NOT NULL
        CHECK(payment_method IN ('Cash', 'Card', 'UPI', 'Net Banking')),
    payment_status TEXT NOT NULL DEFAULT 'Paid'
        CHECK(payment_status IN ('Paid', 'Pending', 'Refunded')),
    FOREIGN KEY(reservation_id) REFERENCES Reservations(reservation_id)
);
CREATE INDEX IF NOT EXISTS idx_res_room_status_dates
    ON Reservations(room_id, booking_status, check_in, check_out);
CREATE INDEX IF NOT EXISTS idx_pay_res_status_date
    ON Payments(reservation_id, payment_status, payment_date);
CREATE TRIGGER IF NOT EXISTS trg_reservation_no_overlap_insert
BEFORE INSERT ON Reservations
WHEN NEW.booking_status = 'Confirmed'
BEGIN
    SELECT CASE WHEN (SELECT room_status FROM Rooms WHERE room_id=NEW.room_id) <> 'Available'
        THEN RAISE(ABORT, 'A room under maintenance cannot be booked.') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM Reservations
        WHERE room_id=NEW.room_id AND booking_status='Confirmed'
          AND check_in < NEW.check_out AND check_out > NEW.check_in
    ) THEN RAISE(ABORT, 'Room is already reserved for overlapping dates.') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_reservation_no_overlap_update
BEFORE UPDATE ON Reservations
WHEN NEW.booking_status = 'Confirmed'
BEGIN
    SELECT CASE WHEN (SELECT room_status FROM Rooms WHERE room_id=NEW.room_id) <> 'Available'
        THEN RAISE(ABORT, 'A room under maintenance cannot be booked.') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM Reservations
        WHERE room_id=NEW.room_id AND reservation_id<>NEW.reservation_id
          AND booking_status='Confirmed'
          AND check_in < NEW.check_out AND check_out > NEW.check_in
    ) THEN RAISE(ABORT, 'Room is already reserved for overlapping dates.') END;
END;
"""


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def initialize_database():
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        # Seed a small starter inventory only on the first launch.
        room_count = conn.execute("SELECT COUNT(*) FROM Rooms").fetchone()[0]
        if room_count == 0:
            conn.executemany(
                "INSERT INTO Rooms (room_number, room_type, price_per_night, room_status) VALUES (?, ?, ?, ?)",
                [
                    ("101", "Single", 1800, "Available"),
                    ("102", "Double", 2500, "Available"),
                    ("103", "Deluxe", 3500, "Available"),
                    ("201", "Double", 2700, "Available"),
                    ("202", "Suite", 5500, "Available"),
                    ("203", "Deluxe", 3800, "Maintenance"),
                ],
            )
