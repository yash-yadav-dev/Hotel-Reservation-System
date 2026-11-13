import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from tkcalendar import DateEntry

from database import get_connection, initialize_database


class HotelReservationApp(tk.Tk):
    def __init__(self):
        initialize_database()
        super().__init__()
        self.title("Hotel Reservation | Management Console")
        self.geometry("1260x780")
        self.minsize(1050, 680)
        self.configure(bg="#F3F5F8")

        # A restrained hotel-console theme: deep navy, warm white and teal accents.
        self.colors = {
            "navy": "#14263D", "navy_light": "#203A57", "teal": "#16877F",
            "teal_dark": "#106B65", "bg": "#F3F5F8", "white": "#FFFFFF",
            "ink": "#1D2B3D", "muted": "#718096", "line": "#DCE3EB",
            "soft": "#EAF2F2", "red": "#B84A4A"
        }
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        c = self.colors
        self.style.configure("TFrame", background=c["bg"])
        self.style.configure("TLabel", background=c["bg"], foreground=c["ink"], font=("Segoe UI", 9))
        self.style.configure("TNotebook", background=c["bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
        self.style.configure("TNotebook.Tab", background="#E7ECF2", foreground="#526176",
                             padding=(20, 12), font=("Segoe UI", 9, "bold"), borderwidth=0)
        self.style.map("TNotebook.Tab", background=[("selected", c["white"])],
                       foreground=[("selected", c["teal_dark"])], padding=[("selected", (20, 12))])
        self.style.configure("Treeview", background=c["white"], fieldbackground=c["white"],
                             foreground=c["ink"], rowheight=34, font=("Segoe UI", 9), borderwidth=0)
        self.style.map("Treeview", background=[("selected", "#D8EEEB")],
                       foreground=[("selected", c["navy"])])
        self.style.configure("Treeview.Heading", background=c["navy_light"], foreground=c["white"],
                             font=("Segoe UI", 9, "bold"), padding=(10, 10), relief="flat")
        self.style.map("Treeview.Heading", background=[("active", c["navy"])])
        self.style.configure("TButton", background=c["teal"], foreground=c["white"],
                             padding=(13, 8), font=("Segoe UI", 9, "bold"), borderwidth=0)
        self.style.map("TButton", background=[("active", c["teal_dark"]), ("pressed", c["navy_light"])],
                       foreground=[("disabled", "#D7DEE6")])
        self.style.configure("Header.TLabel", font=("Segoe UI", 19, "bold"),
                             background=c["bg"], foreground=c["navy"])
        self.style.configure("Sub.TLabel", font=("Segoe UI", 9),
                             background=c["bg"], foreground=c["muted"])

        header = tk.Frame(self, bg=c["navy"], height=94)
        header.pack(fill="x")
        header.pack_propagate(False)
        brand = tk.Frame(header, bg=c["navy"])
        brand.pack(side="left", fill="y", padx=26, pady=15)
        tk.Label(brand, text="H  /  HOTEL OPERATIONS", bg=c["navy"], fg="#8ED1C9",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(brand, text="Reservation Management", bg=c["navy"], fg=c["white"],
                 font=("Segoe UI", 19, "bold")).pack(anchor="w", pady=(3, 0))
        tk.Label(brand, text="GUESTS     ROOMS     BOOKINGS     PAYMENTS", bg=c["navy"], fg="#B8C7D8",
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(1, 0))
        status = tk.Frame(header, bg=c["navy_light"], padx=13, pady=9)
        status.pack(side="right", padx=26, pady=25)
        tk.Label(status, text="●", bg=c["navy_light"], fg="#63C6A8",
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 7))
        tk.Label(status, text="DATABASE CONSOLE", bg=c["navy_light"], fg="#E6EDF5",
                 font=("Segoe UI", 8, "bold")).pack(side="left")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=22, pady=(18, 12))

        self.dashboard_tab = ttk.Frame(self.notebook, padding=20)
        self.guests_tab = ttk.Frame(self.notebook, padding=18)
        self.rooms_tab = ttk.Frame(self.notebook, padding=18)
        self.reservations_tab = ttk.Frame(self.notebook, padding=18)
        self.payments_tab = ttk.Frame(self.notebook, padding=18)

        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.guests_tab, text="Guests")
        self.notebook.add(self.rooms_tab, text="Rooms")
        self.notebook.add(self.reservations_tab, text="Reservations")
        self.notebook.add(self.payments_tab, text="Payments")

        self.build_dashboard()
        self.build_guests()
        self.build_rooms()
        self.build_reservations()
        self.build_payments()
        self.refresh_all()

    # ---------- Shared helpers ----------
    def query(self, sql, params=(), fetch=False):
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql.replace("%s", "?"), tuple(str(x) if isinstance(x, Decimal) else x for x in params))
            result = cursor.fetchall() if fetch else cursor.lastrowid
            conn.commit()
            return result
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def call_procedure(self, procedure_name, args):
        """SQLite equivalents of the original MySQL booking/payment procedures."""
        conn = None
        try:
            conn = get_connection()
            if procedure_name == "sp_create_reservation":
                guest_id, room_id, check_in, check_out, booking_status, _ = args
                if check_out <= check_in:
                    raise ValueError("Check-out date must be later than check-in date.")
                room = conn.execute("SELECT room_status FROM Rooms WHERE room_id=?", (room_id,)).fetchone()
                if not room:
                    raise ValueError("Selected room does not exist.")
                if booking_status == "Confirmed":
                    if room[0] != "Available":
                        raise ValueError("Selected room is not available for booking.")
                    conflict = conn.execute("""SELECT COUNT(*) FROM Reservations
                        WHERE room_id=? AND booking_status='Confirmed'
                        AND check_in < ? AND check_out > ?""", (room_id, check_out, check_in)).fetchone()[0]
                    if conflict:
                        raise ValueError("Room is already reserved for overlapping dates.")
                cursor = conn.execute("""INSERT INTO Reservations
                    (guest_id, room_id, check_in, check_out, booking_status)
                    VALUES (?, ?, ?, ?, ?)""", (guest_id, room_id, check_in, check_out, booking_status))
                conn.commit()
                return cursor.lastrowid
            if procedure_name == "sp_record_payment":
                reservation_id, amount, payment_date, payment_method, payment_status = args
                if Decimal(str(amount)) <= 0:
                    raise ValueError("Amount must be greater than zero.")
                cursor = conn.execute("""INSERT INTO Payments
                    (reservation_id, amount, payment_date, payment_method, payment_status)
                    VALUES (?, ?, ?, ?, ?)""",
                    (reservation_id, str(amount), payment_date, payment_method, payment_status))
                conn.commit()
                return cursor.lastrowid
            raise ValueError(f"Unsupported database operation: {procedure_name}")
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def safe_action(self, callback):
        try:
            callback()
        except Exception as exc:
            messagebox.showerror("Database error", str(exc))

    def make_tree(self, parent, columns, headings=None, height=12):
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill="both", expand=True, pady=(12, 0))
        tree = ttk.Treeview(wrapper, columns=columns, show="headings", height=height)
        for col in columns:
            tree.heading(col, text=(headings or {}).get(col, col.replace("_", " ").title()))
            tree.column(col, width=130, anchor="center")
        ybar = ttk.Scrollbar(wrapper, orient="vertical", command=tree.yview)
        xbar = ttk.Scrollbar(wrapper, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        tree.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=(1, 0))
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        wrapper.rowconfigure(0, weight=1)
        wrapper.columnconfigure(0, weight=1)
        return tree

    def clear_tree(self, tree):
        for item in tree.get_children():
            tree.delete(item)

    def selected_id(self, tree):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Select a record", "Please select a row first.")
            return None
        return tree.item(selection[0], "values")[0]

    def form_window(self, title, fields, initial=None, choices=None, on_save=None):
        win = tk.Toplevel(self)
        win.title(title)
        win.transient(self)
        win.grab_set()
        win.configure(bg="#F3F5F8")
        win.resizable(False, False)
        initial = initial or {}
        choices = choices or {}
        entries = {}

        form_head = tk.Frame(win, bg="#14263D", height=58)
        form_head.grid(row=0, column=0, columnspan=2, sticky="ew")
        form_head.grid_propagate(False)
        tk.Label(form_head, text=title, bg="#14263D", fg="#FFFFFF",
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=20, pady=17)

        for row, (key, label) in enumerate(fields, start=1):
            tk.Label(win, text=label, bg="#F3F5F8", fg="#34445B",
                     font=("Segoe UI", 9, "bold")).grid(row=row, column=0, padx=20, pady=8, sticky="w")
            if key in choices:
                widget = ttk.Combobox(win, values=choices[key], state="readonly", width=30)
                widget.set(str(initial.get(key, choices[key][0] if choices[key] else "")))
            elif key in {"check_in", "check_out", "payment_date"}:
                # Calendar picker: users select dates instead of typing them manually.
                widget = DateEntry(win, width=28, date_pattern="yyyy-mm-dd", state="readonly")
                if initial.get(key):
                    widget.set_date(initial[key])
            else:
                widget = ttk.Entry(win, width=33)
                widget.insert(0, str(initial.get(key, "")))
            widget.grid(row=row, column=1, padx=20, pady=8, sticky="ew")
            entries[key] = widget

        # Keep checkout at least one day after check-in.
        if "check_in" in entries and "check_out" in entries:
            check_in_picker = entries["check_in"]
            check_out_picker = entries["check_out"]

            def update_checkout_minimum(_event=None):
                minimum = check_in_picker.get_date() + timedelta(days=1)
                check_out_picker.configure(mindate=minimum)
                if check_out_picker.get_date() < minimum:
                    check_out_picker.set_date(minimum)

            check_in_picker.bind("<<DateEntrySelected>>", update_checkout_minimum)
            update_checkout_minimum()

        def submit():
            values = {key: widget.get().strip() for key, widget in entries.items()}
            if any(value == "" for value in values.values()):
                messagebox.showwarning("Missing information", "Please fill in all displayed fields.", parent=win)
                return
            try:
                on_save(values)
                win.destroy()
            except Exception as exc:
                messagebox.showerror("Unable to save", str(exc), parent=win)

        buttons = ttk.Frame(win)
        buttons.grid(row=len(fields) + 1, column=0, columnspan=2, padx=20, pady=18, sticky="e")
        ttk.Button(buttons, text="Cancel", command=win.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Save", command=submit).pack(side="right")
        win.bind("<Return>", lambda _event: submit())
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def refresh_all(self):
        self.refresh_dashboard()
        self.refresh_guests()
        self.refresh_rooms()
        self.refresh_reservations()
        self.refresh_payments()

    # ---------- Dashboard ----------
    def build_dashboard(self):
        ttk.Label(self.dashboard_tab, text="Overview", style="Header.TLabel").pack(anchor="w")
        ttk.Label(self.dashboard_tab, text="A quick summary of records stored in the MySQL database.",
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 16))
        self.stat_frame = ttk.Frame(self.dashboard_tab)
        self.stat_frame.pack(fill="x")
        self.stat_labels = {}
        for key, title in [("guests", "TOTAL GUESTS"), ("rooms", "TOTAL ROOMS"),
                           ("reservations", "TOTAL RESERVATIONS"), ("revenue", "PAID REVENUE")]:
            card = tk.Frame(self.stat_frame, bg="#FFFFFF", highlightbackground="#DCE3EB", highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=5)
            accent = tk.Frame(card, bg="#16877F", height=4)
            accent.pack(fill="x")
            tk.Label(card, text=title, bg="#FFFFFF", fg="#718096",
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=16, pady=(13, 4))
            value = tk.Label(card, text="—", bg="#FFFFFF", fg="#14263D",
                             font=("Segoe UI", 22, "bold"))
            value.pack(anchor="w", padx=16, pady=(0, 15))
            self.stat_labels[key] = value

        ttk.Label(self.dashboard_tab, text="Recent reservations", style="Header.TLabel").pack(anchor="w", pady=(24, 4))
        self.dashboard_tree = self.make_tree(
            self.dashboard_tab,
            ("reservation_id", "guest_name", "room_number", "check_in", "check_out", "booking_status"),
            height=9
        )
        ttk.Button(self.dashboard_tab, text="Refresh dashboard", command=lambda: self.safe_action(self.refresh_dashboard)).pack(anchor="e", pady=10)

    def refresh_dashboard(self):
        rows = self.query("""
            SELECT
                (SELECT COUNT(*) FROM Guests),
                (SELECT COUNT(*) FROM Rooms),
                (SELECT COUNT(*) FROM Reservations),
                (SELECT COALESCE(SUM(amount), 0) FROM Payments WHERE payment_status='Paid')
        """, fetch=True)[0]
        self.stat_labels["guests"].config(text=str(rows[0]))
        self.stat_labels["rooms"].config(text=str(rows[1]))
        self.stat_labels["reservations"].config(text=str(rows[2]))
        self.stat_labels["revenue"].config(text=f"₹{Decimal(str(rows[3])):,.2f}")

        recent = self.query("""
            SELECT r.reservation_id, g.guest_name, rm.room_number,
                   r.check_in, r.check_out, r.booking_status
            FROM Reservations r
            JOIN Guests g ON g.guest_id = r.guest_id
            JOIN Rooms rm ON rm.room_id = r.room_id
            ORDER BY r.reservation_id DESC
            LIMIT 10
        """, fetch=True)
        self.clear_tree(self.dashboard_tree)
        for row in recent:
            self.dashboard_tree.insert("", "end", values=row)

    # ---------- Guests ----------
    def build_guests(self):
        ttk.Label(self.guests_tab, text="Guest Records", style="Header.TLabel").pack(anchor="w")
        ttk.Label(self.guests_tab, text="Create, view, update and delete guest details.",
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 8))
        bar = ttk.Frame(self.guests_tab)
        bar.pack(fill="x")
        ttk.Button(bar, text="Add guest", command=self.add_guest).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Update selected", command=self.edit_guest).pack(side="left", padx=6)
        ttk.Button(bar, text="Delete selected", command=self.delete_guest).pack(side="left", padx=6)
        ttk.Button(bar, text="Refresh", command=lambda: self.safe_action(self.refresh_guests)).pack(side="right")
        self.guests_tree = self.make_tree(self.guests_tab, ("guest_id", "guest_name", "phone", "email", "address"),
                                          height=14)

    def refresh_guests(self):
        rows = self.query("SELECT guest_id, guest_name, phone, email, address FROM Guests ORDER BY guest_id", fetch=True)
        self.clear_tree(self.guests_tree)
        for row in rows:
            self.guests_tree.insert("", "end", values=row)

    def add_guest(self):
        fields = [("guest_name", "Guest name"), ("phone", "Phone"), ("email", "Email (or enter NA)"), ("address", "Address")]
        def save(v):
            email = None if v["email"].upper() == "NA" else v["email"]
            self.query("INSERT INTO Guests (guest_name, phone, email, address) VALUES (%s,%s,%s,%s)",
                       (v["guest_name"], v["phone"], email, v["address"]))
            self.refresh_all()
        self.form_window("Add guest", fields, on_save=save)

    def edit_guest(self):
        gid = self.selected_id(self.guests_tree)
        if gid is None: return
        row = self.query("SELECT guest_name, phone, email, address FROM Guests WHERE guest_id=%s", (gid,), True)[0]
        fields = [("guest_name", "Guest name"), ("phone", "Phone"), ("email", "Email (or enter NA)"), ("address", "Address")]
        initial = dict(zip([f[0] for f in fields], [row[0], row[1], row[2] or "NA", row[3] or ""]))
        def save(v):
            email = None if v["email"].upper() == "NA" else v["email"]
            self.query("UPDATE Guests SET guest_name=%s, phone=%s, email=%s, address=%s WHERE guest_id=%s",
                       (v["guest_name"], v["phone"], email, v["address"], gid))
            self.refresh_all()
        self.form_window("Update guest", fields, initial, on_save=save)

    def delete_guest(self):
        gid = self.selected_id(self.guests_tree)
        if gid is None: return
        if not messagebox.askyesno("Confirm delete", "Delete this guest? Guests linked to reservations cannot be deleted."):
            return
        self.safe_action(lambda: (self.query("DELETE FROM Guests WHERE guest_id=%s", (gid,)), self.refresh_all()))

    # ---------- Rooms ----------
    def build_rooms(self):
        ttk.Label(self.rooms_tab, text="Room Records", style="Header.TLabel").pack(anchor="w")
        ttk.Label(self.rooms_tab, text="Maintain room numbers, categories, prices and maintenance status.",
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 8))
        bar = ttk.Frame(self.rooms_tab)
        bar.pack(fill="x")
        ttk.Button(bar, text="Add room", command=self.add_room).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Update selected", command=self.edit_room).pack(side="left", padx=6)
        ttk.Button(bar, text="Delete selected", command=self.delete_room).pack(side="left", padx=6)
        ttk.Button(bar, text="Refresh", command=lambda: self.safe_action(self.refresh_rooms)).pack(side="right")
        self.rooms_tree = self.make_tree(self.rooms_tab,
            ("room_id", "room_number", "room_type", "price_per_night", "room_status"), height=14)

    def refresh_rooms(self):
        rows = self.query("SELECT room_id, room_number, room_type, price_per_night, room_status FROM Rooms ORDER BY room_number", fetch=True)
        self.clear_tree(self.rooms_tree)
        for row in rows:
            self.rooms_tree.insert("", "end", values=row)

    def add_room(self):
        fields = [("room_number", "Room number"), ("room_type", "Room type"), ("price_per_night", "Price per night"), ("room_status", "Room status")]
        choices = {"room_status": ["Available", "Maintenance"]}
        def save(v):
            price = Decimal(v["price_per_night"])
            if price <= 0: raise ValueError("Price must be greater than zero.")
            self.query("INSERT INTO Rooms (room_number, room_type, price_per_night, room_status) VALUES (%s,%s,%s,%s)",
                       (v["room_number"], v["room_type"], price, v["room_status"]))
            self.refresh_all()
        self.form_window("Add room", fields, choices=choices, on_save=save)

    def edit_room(self):
        rid = self.selected_id(self.rooms_tree)
        if rid is None: return
        row = self.query("SELECT room_number, room_type, price_per_night, room_status FROM Rooms WHERE room_id=%s", (rid,), True)[0]
        fields = [("room_number", "Room number"), ("room_type", "Room type"), ("price_per_night", "Price per night"), ("room_status", "Room status")]
        initial = dict(zip([f[0] for f in fields], row))
        def save(v):
            price = Decimal(v["price_per_night"])
            if price <= 0: raise ValueError("Price must be greater than zero.")
            self.query("UPDATE Rooms SET room_number=%s, room_type=%s, price_per_night=%s, room_status=%s WHERE room_id=%s",
                       (v["room_number"], v["room_type"], price, v["room_status"], rid))
            self.refresh_all()
        self.form_window("Update room", fields, initial, {"room_status": ["Available", "Maintenance"]}, save)

    def delete_room(self):
        rid = self.selected_id(self.rooms_tree)
        if rid is None: return
        if not messagebox.askyesno("Confirm delete", "Delete this room? Rooms linked to reservations cannot be deleted."):
            return
        self.safe_action(lambda: (self.query("DELETE FROM Rooms WHERE room_id=%s", (rid,)), self.refresh_all()))

    # ---------- Reservations ----------
    def build_reservations(self):
        ttk.Label(self.reservations_tab, text="Reservation Records", style="Header.TLabel").pack(anchor="w")
        ttk.Label(self.reservations_tab, text="Bookings connect a guest to a room for a date range.",
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 8))
        bar = ttk.Frame(self.reservations_tab)
        bar.pack(fill="x")
        ttk.Button(bar, text="Add reservation", command=self.add_reservation).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Update status", command=self.edit_reservation).pack(side="left", padx=6)
        ttk.Button(bar, text="Delete selected", command=self.delete_reservation).pack(side="left", padx=6)
        ttk.Button(bar, text="Refresh", command=lambda: self.safe_action(self.refresh_reservations)).pack(side="right")
        self.reservations_tree = self.make_tree(self.reservations_tab,
            ("reservation_id", "guest_id", "guest_name", "room_id", "room_number", "check_in", "check_out", "booking_status"),
            height=14)

    def refresh_reservations(self):
        rows = self.query("""
            SELECT r.reservation_id, r.guest_id, g.guest_name, r.room_id, rm.room_number,
                   r.check_in, r.check_out, r.booking_status
            FROM Reservations r
            JOIN Guests g ON g.guest_id=r.guest_id
            JOIN Rooms rm ON rm.room_id=r.room_id
            ORDER BY r.reservation_id
        """, fetch=True)
        self.clear_tree(self.reservations_tree)
        for row in rows:
            self.reservations_tree.insert("", "end", values=row)

    def check_room_conflict(self, room_id, check_in, check_out, exclude_id=None):
        sql = """
            SELECT COUNT(*) FROM Reservations
            WHERE room_id=%s AND booking_status='Confirmed'
              AND check_in < %s AND check_out > %s
        """
        params = [room_id, check_out, check_in]
        if exclude_id is not None:
            sql += " AND reservation_id <> %s"
            params.append(exclude_id)
        count = self.query(sql, tuple(params), True)[0][0]
        if count:
            raise ValueError("This room already has a confirmed reservation overlapping those dates.")

    def add_reservation(self):
        guests = self.query("SELECT guest_id, guest_name FROM Guests ORDER BY guest_id", fetch=True)
        rooms = self.query("SELECT room_id, room_number FROM Rooms WHERE room_status='Available' ORDER BY room_number", fetch=True)
        if not guests or not rooms:
            messagebox.showwarning("Missing records", "Add at least one guest and one available room first.")
            return
        guest_map = {f"{r[0]} - {r[1]}": r[0] for r in guests}
        room_map = {f"{r[0]} - {r[1]}": r[0] for r in rooms}
        fields = [("guest", "Guest"), ("room", "Room"), ("check_in", "Check-in date"),
                  ("check_out", "Check-out date"), ("booking_status", "Booking status")]
        choices = {"guest": list(guest_map), "room": list(room_map),
                   "booking_status": ["Confirmed", "Cancelled", "Completed"]}
        def save(v):
            start, end = date.fromisoformat(v["check_in"]), date.fromisoformat(v["check_out"])
            if end <= start: raise ValueError("Check-out must be after check-in.")
            guest_id, room_id = guest_map[v["guest"]], room_map[v["room"]]
            # The stored procedure locks the room row and performs the booking
            # inside a transaction; MySQL triggers provide a second validation layer.
            self.call_procedure("sp_create_reservation",
                [guest_id, room_id, v["check_in"], v["check_out"], v["booking_status"], 0])
            self.refresh_all()
        default_dates = {"check_in": date.today(), "check_out": date.today() + timedelta(days=1)}
        self.form_window("Add reservation", fields, initial=default_dates, choices=choices, on_save=save)

    def edit_reservation(self):
        rid = self.selected_id(self.reservations_tree)
        if rid is None: return
        row = self.query("SELECT booking_status FROM Reservations WHERE reservation_id=%s", (rid,), True)[0]
        fields = [("booking_status", "Booking status")]
        def save(v):
            self.query("UPDATE Reservations SET booking_status=%s WHERE reservation_id=%s", (v["booking_status"], rid))
            self.refresh_all()
        self.form_window("Update reservation status", fields, {"booking_status": row[0]},
                         {"booking_status": ["Confirmed", "Cancelled", "Completed"]}, save)

    def delete_reservation(self):
        rid = self.selected_id(self.reservations_tree)
        if rid is None: return
        if not messagebox.askyesno("Confirm delete", "Delete this reservation? Its payment records must be deleted first."):
            return
        self.safe_action(lambda: (self.query("DELETE FROM Reservations WHERE reservation_id=%s", (rid,)), self.refresh_all()))

    # ---------- Payments ----------
    def build_payments(self):
        ttk.Label(self.payments_tab, text="Payment Records", style="Header.TLabel").pack(anchor="w")
        ttk.Label(self.payments_tab, text="Record payments against existing reservations.",
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 8))
        bar = ttk.Frame(self.payments_tab)
        bar.pack(fill="x")
        ttk.Button(bar, text="Add payment", command=self.add_payment).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Update payment", command=self.edit_payment).pack(side="left", padx=6)
        ttk.Button(bar, text="Delete selected", command=self.delete_payment).pack(side="left", padx=6)
        ttk.Button(bar, text="Refresh", command=lambda: self.safe_action(self.refresh_payments)).pack(side="right")
        self.payments_tree = self.make_tree(self.payments_tab,
            ("payment_id", "reservation_id", "guest_name", "amount", "payment_date", "payment_method", "payment_status"),
            height=14)

    def refresh_payments(self):
        rows = self.query("""
            SELECT p.payment_id, p.reservation_id, g.guest_name, p.amount,
                   p.payment_date, p.payment_method, p.payment_status
            FROM Payments p
            JOIN Reservations r ON r.reservation_id=p.reservation_id
            JOIN Guests g ON g.guest_id=r.guest_id
            ORDER BY p.payment_id
        """, fetch=True)
        self.clear_tree(self.payments_tree)
        for row in rows:
            self.payments_tree.insert("", "end", values=row)

    def add_payment(self):
        reservations = self.query("SELECT reservation_id FROM Reservations ORDER BY reservation_id", fetch=True)
        if not reservations:
            messagebox.showwarning("No reservations", "Create a reservation before adding a payment.")
            return
        res_choices = [str(r[0]) for r in reservations]
        fields = [("reservation_id", "Reservation ID"), ("amount", "Amount"),
                  ("payment_date", "Payment date"),
                  ("payment_method", "Payment method"), ("payment_status", "Payment status")]
        choices = {"reservation_id": res_choices,
                   "payment_method": ["Cash", "Card", "UPI", "Net Banking"],
                   "payment_status": ["Paid", "Pending", "Refunded"]}
        def save(v):
            amount = Decimal(v["amount"])
            if amount <= 0: raise ValueError("Amount must be greater than zero.")
            date.fromisoformat(v["payment_date"])
            self.call_procedure("sp_record_payment",
                [int(v["reservation_id"]), amount, v["payment_date"], v["payment_method"], v["payment_status"]])
            self.refresh_all()
        self.form_window("Add payment", fields, choices=choices, on_save=save)

    def edit_payment(self):
        pid = self.selected_id(self.payments_tree)
        if pid is None: return
        row = self.query("SELECT amount, payment_date, payment_method, payment_status FROM Payments WHERE payment_id=%s",
                         (pid,), True)[0]
        fields = [("amount", "Amount"), ("payment_date", "Payment date"),
                  ("payment_method", "Payment method"), ("payment_status", "Payment status")]
        initial = dict(zip([f[0] for f in fields], row))
        choices = {"payment_method": ["Cash", "Card", "UPI", "Net Banking"],
                   "payment_status": ["Paid", "Pending", "Refunded"]}
        def save(v):
            amount = Decimal(v["amount"])
            if amount <= 0: raise ValueError("Amount must be greater than zero.")
            date.fromisoformat(v["payment_date"])
            self.query("""UPDATE Payments SET amount=%s, payment_date=%s,
                payment_method=%s, payment_status=%s WHERE payment_id=%s""",
                (amount, v["payment_date"], v["payment_method"], v["payment_status"], pid))
            self.refresh_all()
        self.form_window("Update payment", fields, initial, choices, save)

    def delete_payment(self):
        pid = self.selected_id(self.payments_tree)
        if pid is None: return
        if not messagebox.askyesno("Confirm delete", "Delete this payment record?"):
            return
        self.safe_action(lambda: (self.query("DELETE FROM Payments WHERE payment_id=%s", (pid,)), self.refresh_all()))


if __name__ == "__main__":
    app = HotelReservationApp()
    app.mainloop()
