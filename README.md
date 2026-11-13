# Hotel Reservation Management System

A Python desktop application built with Tkinter for managing guests, rooms, reservations and payments.

## Run on another Windows computer

**MySQL is no longer required.** The portable edition uses Python's built-in SQLite database, so there is no MySQL server, MySQL account, username or password to configure.

1. Install Python 3.10 or newer from https://www.python.org/downloads/ . During installation, enable **Add Python to PATH**.
2. Extract this repository ZIP (or clone the repository).
3. Open the project folder in File Explorer.
4. Double-click `Start_HotelDB.bat`.

The launcher installs the small `tkcalendar` dependency if it is missing and starts the application. The database is created automatically at `data/hotel_reservation.db` on first launch.

## Features

- Dashboard with guest, room, reservation and paid-revenue summaries.
- Guest management: add, view, update and delete.
- Room management: add, view, update and delete.
- Reservation management with calendar date selection and overlapping-booking validation.
- Payment management with payment method and status tracking.
- SQLite foreign keys, constraints, indexes and triggers.
- Local persistence: records remain after closing and reopening the application.

## Data location and moving to another computer

The application stores its data in `data/hotel_reservation.db`. To move the existing hotel records to another computer, close the application and copy this file into the same `data` folder on the other computer. Back it up regularly. Do not commit real guest or payment data to a public GitHub repository.

**Important:** This SQLite edition gives each computer its own local database unless you manually move the database file. It does not provide live synchronization between multiple computers. Shared, simultaneous access requires a separately hosted database and a secure backend API.

## Project structure

```text
HotelReservationDB/
├── app/
│   ├── database.py       # SQLite setup and connection
│   ├── gui.py            # Tkinter application
│   └── main.py           # Application entry point
├── data/                 # Local database is generated here (not committed)
├── database/             # Original MySQL schema and upgrade/demo scripts (reference)
├── requirements.txt
├── Start_HotelDB.bat
└── README.md
```

## Run from PowerShell

```powershell
py -m pip install -r requirements.txt
py app/main.py
```

## Database note

The original MySQL schema and advanced SQL upgrade scripts are retained under `database/` as project/reference material. The portable runtime uses SQLite equivalents for the application's tables, integrity rules and booking/payment operations. MySQL stored procedures are not executed by the SQLite edition.
