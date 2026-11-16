import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import mysql.connector

# Database Configuration (XAMPP MySQL)
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "student_attendance_event"
}


# ---------------- DATABASE HELPERS ----------------
def get_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        messagebox.showerror("Database Connection Error", f"Cannot connect to MySQL:\n{e}")
        return None


def get_cursor(conn):
    """Always returns a buffered cursor to prevent 'Unread result found' errors."""
    return conn.cursor(buffered=True)


def init_database():
    """Ensures tables exist and fixes attendance.check_out type to TIME(6) NULL."""
    conn = get_connection()
    if not conn:
        return
    cursor = get_cursor(conn)
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                admin_id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS department (
                department_id INT(20) NOT NULL AUTO_INCREMENT PRIMARY KEY,
                department_name VARCHAR(100) NOT NULL UNIQUE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                name VARCHAR(100) NOT NULL,
                student_id VARCHAR(50) NOT NULL PRIMARY KEY,
                department_id VARCHAR(20) NOT NULL,
                year_level INT(50) NOT NULL,
                section VARCHAR(50) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id INT(10) NOT NULL AUTO_INCREMENT PRIMARY KEY,
                name TEXT NOT NULL,
                date DATE NOT NULL,
                time TIME(6) NOT NULL,
                description VARCHAR(200) DEFAULT NULL,
                venue VARCHAR(100) NOT NULL,
                organization VARCHAR(100) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                attendance_id INT(10) NOT NULL AUTO_INCREMENT PRIMARY KEY,
                event_id INT(10) NOT NULL,
                student_id VARCHAR(50) NOT NULL,
                check_in TIME(6) NOT NULL,
                check_out TIME(6) NULL DEFAULT NULL,
                status ENUM('PRESENT','ABSENT','EXCUSED','LOGGED-OUT') NOT NULL DEFAULT 'PRESENT'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # Fix check_out from int(6) NOT NULL -> TIME(6) NULL DEFAULT NULL
        cursor.execute("SHOW COLUMNS FROM attendance LIKE 'check_out'")
        co_info = cursor.fetchone()
        if co_info and "int" in str(co_info[1]).lower():
            cursor.execute("ALTER TABLE attendance MODIFY check_out TIME(6) NULL DEFAULT NULL")
            cursor.execute("UPDATE attendance SET check_out = NULL WHERE check_out = '00:00:00' OR status = 'PRESENT'")

        # Ensure default admin exists
        cursor.execute("SELECT COUNT(*) FROM admin")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO admin (username, password) VALUES ('admin', 'password123')")

        conn.commit()
    except Exception as e:
        messagebox.showerror("Database Initialization Error", str(e))
    finally:
        cursor.close()
        conn.close()


def parse_event_date(raw_date):
    if not raw_date:
        return datetime.now().strftime("%Y-%m-%d")
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw_date.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_event_time(raw_time):
    if not raw_time:
        return datetime.now().strftime("%H:%M:%S")
    cleaned = raw_time.strip().upper()
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p", "%I %p", "%I%p"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%H:%M:%S")
        except ValueError:
            continue
    return None


def format_time_str(val):
    if val is None:
        return "-"
    s = str(val).split(".")[0]
    if s in ("", "0", "00:00:00", "None"):
        return "-"
    return s


# ---------------- UI INTERACTION HELPERS ----------------
def add_hover_effect(widget, normal_bg, hover_bg):
    widget.bind("<Enter>", lambda e: widget.config(bg=hover_bg))
    widget.bind("<Leave>", lambda e: widget.config(bg=normal_bg))


# ---------------- AUTHENTICATION WINDOW (LOGIN & REGISTER) ----------------
class AuthWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Admin Portal - Student Event Attendance")
        self.root.geometry("460x560")
        self.root.resizable(False, False)
        self.root.configure(bg="#0f172a")

        self.center_window()
        self.show_login_screen(animate=True)

    def center_window(self):
        self.root.update_idletasks()
        w, h = 460, 560
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def slide_in_card(self, card, target_relx=0.5, start_relx=0.65):
        step = (target_relx - start_relx) / 10.0

        def animate(curr, count):
            if count <= 10:
                card.place(relx=curr, rely=0.5, anchor="center", width=390, height=490)
                self.root.after(14, lambda: animate(curr + step, count + 1))
            else:
                card.place(relx=target_relx, rely=0.5, anchor="center", width=390, height=490)

        animate(start_relx, 0)

    def show_login_screen(self, animate=True):
        self.clear_window()
        card = tk.Frame(self.root, bg="#1e293b", padx=32, pady=28, highlightthickness=1, highlightbackground="#334155")

        if animate:
            self.slide_in_card(card, 0.5, 0.35)
        else:
            card.place(relx=0.5, rely=0.5, anchor="center", width=390, height=490)

        tk.Label(card, text="🔐 ADMIN PORTAL", font=("Segoe UI", 17, "bold"), fg="#38bdf8", bg="#1e293b").pack(pady=(5, 2))
        tk.Label(card, text="Sign in to manage event attendance", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b").pack(pady=(0, 22))

        tk.Label(card, text="Username", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#1e293b").pack(anchor="w")
        self.user_entry = tk.Entry(
            card, font=("Segoe UI", 11), bg="#0f172a", fg="#ffffff",
            insertbackground="#38bdf8", relief="flat", highlightthickness=1,
            highlightbackground="#334155", highlightcolor="#38bdf8"
        )
        self.user_entry.pack(fill="x", ipady=7, pady=(4, 14))
        self.user_entry.focus()

        pass_header = tk.Frame(card, bg="#1e293b")
        pass_header.pack(fill="x")
        tk.Label(pass_header, text="Password", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#1e293b").pack(side="left")

        self.show_login_pw = False
        toggle_btn = tk.Button(
            pass_header, text="👁 Show", font=("Segoe UI", 8, "bold"),
            bg="#1e293b", fg="#38bdf8", activebackground="#1e293b", activeforeground="#7dd3fc",
            relief="flat", cursor="hand2", bd=0
        )
        toggle_btn.pack(side="right")

        self.pass_entry = tk.Entry(
            card, font=("Segoe UI", 11), show="•", bg="#0f172a", fg="#ffffff",
            insertbackground="#38bdf8", relief="flat", highlightthickness=1,
            highlightbackground="#334155", highlightcolor="#38bdf8"
        )
        self.pass_entry.pack(fill="x", ipady=7, pady=(4, 8))
        self.pass_entry.bind("<Return>", lambda e: self.handle_login())

        def toggle_pw():
            self.show_login_pw = not self.show_login_pw
            self.pass_entry.config(show="" if self.show_login_pw else "•")
            toggle_btn.config(text="🙈 Hide" if self.show_login_pw else "👁 Show")

        toggle_btn.config(command=toggle_pw)

        self.login_status = tk.Label(card, text="", font=("Segoe UI", 9), fg="#f87171", bg="#1e293b")
        self.login_status.pack(pady=(2, 10))

        login_btn = tk.Button(
            card, text="SIGN IN", font=("Segoe UI", 10, "bold"),
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff",
            relief="flat", cursor="hand2", command=self.handle_login, pady=9
        )
        login_btn.pack(fill="x", pady=(0, 14))
        add_hover_effect(login_btn, "#0284c7", "#0369a1")

        tk.Frame(card, bg="#334155", height=1).pack(fill="x", pady=(4, 12))

        reg_btn = tk.Button(
            card, text="New here? Create Admin Account →", font=("Segoe UI", 9, "bold"),
            bg="#1e293b", fg="#10b981", activebackground="#1e293b", activeforeground="#34d399",
            relief="flat", cursor="hand2", command=self.show_register_screen
        )
        reg_btn.pack(fill="x")

    def show_register_screen(self):
        self.clear_window()
        card = tk.Frame(self.root, bg="#1e293b", padx=32, pady=24, highlightthickness=1, highlightbackground="#334155")
        self.slide_in_card(card, 0.5, 0.65)

        tk.Label(card, text="✨ CREATE ACCOUNT", font=("Segoe UI", 17, "bold"), fg="#10b981", bg="#1e293b").pack(pady=(2, 2))
        tk.Label(card, text="Register a new administrator account", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b").pack(pady=(0, 16))

        tk.Label(card, text="New Username", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#1e293b").pack(anchor="w")
        self.reg_user_entry = tk.Entry(
            card, font=("Segoe UI", 11), bg="#0f172a", fg="#ffffff",
            insertbackground="#10b981", relief="flat", highlightthickness=1,
            highlightbackground="#334155", highlightcolor="#10b981"
        )
        self.reg_user_entry.pack(fill="x", ipady=6, pady=(3, 10))
        self.reg_user_entry.focus()

        tk.Label(card, text="New Password", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#1e293b").pack(anchor="w")
        self.reg_pass_entry = tk.Entry(
            card, font=("Segoe UI", 11), show="•", bg="#0f172a", fg="#ffffff",
            insertbackground="#10b981", relief="flat", highlightthickness=1,
            highlightbackground="#334155", highlightcolor="#10b981"
        )
        self.reg_pass_entry.pack(fill="x", ipady=6, pady=(3, 10))

        tk.Label(card, text="Confirm Password", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#1e293b").pack(anchor="w")
        self.reg_conf_entry = tk.Entry(
            card, font=("Segoe UI", 11), show="•", bg="#0f172a", fg="#ffffff",
            insertbackground="#10b981", relief="flat", highlightthickness=1,
            highlightbackground="#334155", highlightcolor="#10b981"
        )
        self.reg_conf_entry.pack(fill="x", ipady=6, pady=(3, 6))
        self.reg_conf_entry.bind("<Return>", lambda e: self.handle_register())

        self.reg_status = tk.Label(card, text="", font=("Segoe UI", 9), fg="#f87171", bg="#1e293b")
        self.reg_status.pack(pady=(2, 8))

        register_btn = tk.Button(
            card, text="CREATE ACCOUNT", font=("Segoe UI", 10, "bold"),
            bg="#10b981", fg="#ffffff", activebackground="#059669", activeforeground="#ffffff",
            relief="flat", cursor="hand2", command=self.handle_register, pady=9
        )
        register_btn.pack(fill="x", pady=(0, 12))
        add_hover_effect(register_btn, "#10b981", "#059669")

        back_btn = tk.Button(
            card, text="← Back to Admin Login", font=("Segoe UI", 9, "bold"),
            bg="#1e293b", fg="#38bdf8", activebackground="#1e293b", activeforeground="#7dd3fc",
            relief="flat", cursor="hand2", command=lambda: self.show_login_screen(animate=True)
        )
        back_btn.pack(fill="x")

    def handle_login(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()

        if not username or not password:
            self.login_status.config(text="⚠ Please enter both username and password.", fg="#fbbf24")
            return

        conn = get_connection()
        if not conn:
            return
        cursor = get_cursor(conn)
        try:
            cursor.execute(
                "SELECT admin_id, username FROM admin WHERE username = %s AND password = %s",
                (username, password)
            )
            admin = cursor.fetchone()
            if admin:
                self.login_status.config(text="✔ Login successful! Launching dashboard...", fg="#4ade80")
                self.root.after(450, lambda: self.launch_dashboard(admin[1]))
            else:
                self.login_status.config(text="✖ Invalid username or password.", fg="#f87171")
                self.pass_entry.delete(0, "end")
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
        finally:
            cursor.close()
            conn.close()

    def launch_dashboard(self, username):
        self.root.destroy()
        main_root = tk.Tk()
        AttendanceApp(main_root, admin_name=username)
        main_root.mainloop()

    def handle_register(self):
        username = self.reg_user_entry.get().strip()
        password = self.reg_pass_entry.get().strip()
        confirm = self.reg_conf_entry.get().strip()

        if not username or not password or not confirm:
            self.reg_status.config(text="⚠ All fields are required.", fg="#fbbf24")
            return

        if password != confirm:
            self.reg_status.config(text="✖ Passwords do not match.", fg="#f87171")
            return

        conn = get_connection()
        if not conn:
            return
        cursor = get_cursor(conn)
        try:
            cursor.execute("SELECT admin_id FROM admin WHERE username = %s", (username,))
            if cursor.fetchone():
                self.reg_status.config(text=f"✖ Username '{username}' is already taken.", fg="#f87171")
                return

            cursor.execute("INSERT INTO admin (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            self.reg_status.config(text="✔ Account created! Redirecting to login...", fg="#4ade80")
            self.root.after(700, lambda: self.show_login_screen(animate=True))
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Database Error", str(e))
        finally:
            cursor.close()
            conn.close()


# ---------------- MAIN INTERACTIVE ATTENDANCE DASHBOARD ----------------
class AttendanceApp:
    def __init__(self, root, admin_name="Admin"):
        self.root = root
        self.admin_name = admin_name
        self.root.title("Student Event Attendance System")
        self.root.geometry("1160x760")
        self.root.minsize(1000, 680)
        self.root.configure(bg="#0f172a")

        self.root.attributes("-alpha", 0.0)
        self.fade_in()

        self.all_logs_cache = []
        self.events_map = {}
        self.create_widgets()
        self.refresh_event_dropdown()
        self.load_attendance_logs()
        self.update_live_clock()

    def fade_in(self, alpha=0.0):
        if alpha < 1.0:
            alpha = min(1.0, alpha + 0.1)
            self.root.attributes("-alpha", alpha)
            self.root.after(18, lambda: self.fade_in(alpha))

    def update_live_clock(self):
        now_text = datetime.now().strftime("📅 %b %d, %Y   ⏰ %I:%M:%S %p")
        self.clock_lbl.config(text=now_text)
        self.root.after(1000, self.update_live_clock)

    def create_widgets(self):
        header = tk.Frame(self.root, bg="#1e293b", padx=24, pady=14, highlightthickness=1, highlightbackground="#334155")
        header.pack(fill="x")

        left_hdr = tk.Frame(header, bg="#1e293b")
        left_hdr.pack(side="left")

        tk.Label(
            left_hdr, text="🎓 STUDENT EVENT ATTENDANCE SYSTEM",
            font=("Segoe UI", 15, "bold"), fg="#38bdf8", bg="#1e293b"
        ).pack(anchor="w")

        tk.Label(
            left_hdr, text=f"Logged in as: {self.admin_name}",
            font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b"
        ).pack(anchor="w")

        right_hdr = tk.Frame(header, bg="#1e293b")
        right_hdr.pack(side="right")

        self.clock_lbl = tk.Label(
            right_hdr, text="", font=("Consolas", 10, "bold"),
            fg="#e2e8f0", bg="#0f172a", padx=12, pady=6
        )
        self.clock_lbl.pack(side="left", padx=(0, 12))

        logout_admin_btn = tk.Button(
            right_hdr, text="⎋ Logout", font=("Segoe UI", 9, "bold"),
            bg="#ef4444", fg="#ffffff", activebackground="#dc2626", activeforeground="#ffffff",
            relief="flat", cursor="hand2", command=self.logout_admin, padx=14, pady=6
        )
        logout_admin_btn.pack(side="right")
        add_hover_effect(logout_admin_btn, "#ef4444", "#dc2626")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#0f172a", borderwidth=0)
        style.configure(
            "TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[18, 10],
            background="#1e293b", foreground="#94a3b8", borderwidth=0
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#0284c7"), ("active", "#334155")],
            foreground=[("selected", "#ffffff"), ("active", "#f8fafc")]
        )

        style.configure(
            "Treeview",
            background="#0f172a",
            foreground="#f8fafc",
            fieldbackground="#0f172a",
            rowheight=28,
            font=("Segoe UI", 9),
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background="#1e293b",
            foreground="#38bdf8",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padding=6
        )
        style.map("Treeview", background=[("selected", "#0284c7")], foreground=[("selected", "#ffffff")])

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=14)

        self.tab_signin = tk.Frame(self.notebook, bg="#0f172a")
        self.tab_logout = tk.Frame(self.notebook, bg="#0f172a")
        self.tab_logs = tk.Frame(self.notebook, bg="#0f172a")

        self.notebook.add(self.tab_signin, text="  1. Time-In (Sign-In)  ")
        self.notebook.add(self.tab_logout, text="  2. Time-Out (Sign-Out)  ")
        self.notebook.add(self.tab_logs, text="  3. Attendance Logs  ")

        self.build_signin_tab()
        self.build_logout_tab()
        self.build_logs_tab()

    def logout_admin(self):
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self.root.destroy()
            root = tk.Tk()
            AuthWindow(root)
            root.mainloop()

    # ---------------- TAB 1: TIME-IN ----------------
    def build_signin_tab(self):
        container = tk.Frame(self.tab_signin, bg="#0f172a")
        container.pack(fill="both", expand=True, padx=6, pady=8)

        form_frame = tk.LabelFrame(
            container, text=" Event & Student Entry ", font=("Segoe UI", 11, "bold"),
            fg="#f8fafc", bg="#1e293b", padx=18, pady=12, bd=1, relief="solid"
        )
        form_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.entries = {}
        row_idx = 0

        tk.Label(form_frame, text="QUICK LOAD EVENT :", font=("Segoe UI", 9, "bold"), fg="#fbbf24", bg="#1e293b").grid(
            row=row_idx, column=0, sticky="w", pady=(0, 6)
        )
        self.event_combo = ttk.Combobox(form_frame, state="readonly", font=("Segoe UI", 9))
        self.event_combo.grid(row=row_idx, column=1, sticky="ew", pady=(0, 6), padx=(10, 0), ipady=2)
        self.event_combo.bind("<<ComboboxSelected>>", self.on_select_existing_event)
        row_idx += 1

        tk.Label(form_frame, text="EVENT DETAILS", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b").grid(
            row=row_idx, column=0, columnspan=2, sticky="w", pady=(4, 4)
        )
        row_idx += 1

        event_fields = [
            ("Event Name * :", "event_name"),
            ("Event Date :", "event_date"),
            ("Event Time :", "event_time"),
            ("Organization :", "organization"),
            ("Venue :", "venue"),
            ("Description :", "description")
        ]

        for label_text, key in event_fields:
            tk.Label(form_frame, text=label_text, font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#1e293b").grid(
                row=row_idx, column=0, sticky="w", pady=3
            )
            ent = tk.Entry(
                form_frame, font=("Segoe UI", 10), bg="#0f172a", fg="#ffffff",
                insertbackground="#38bdf8", relief="flat", highlightthickness=1,
                highlightbackground="#334155", highlightcolor="#38bdf8"
            )
            ent.grid(row=row_idx, column=1, sticky="ew", pady=3, ipady=4, padx=(10, 0))
            self.entries[key] = ent
            row_idx += 1

        st_hdr = tk.Frame(form_frame, bg="#1e293b")
        st_hdr.grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=(10, 4))
        tk.Label(st_hdr, text="STUDENT DETAILS", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b").pack(side="left")
        self.autofill_lbl = tk.Label(st_hdr, text="(Press Enter on Student ID to auto-fill)", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b")
        self.autofill_lbl.pack(side="right")
        row_idx += 1

        student_fields = [
            ("Student ID * :", "student_id"),
            ("Full Name * :", "name"),
            ("Department ID/Name :", "dept"),
            ("Year Level :", "year_level"),
            ("Section :", "section")
        ]

        for label_text, key in student_fields:
            tk.Label(form_frame, text=label_text, font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#1e293b").grid(
                row=row_idx, column=0, sticky="w", pady=3
            )
            ent = tk.Entry(
                form_frame, font=("Segoe UI", 10), bg="#0f172a", fg="#ffffff",
                insertbackground="#38bdf8", relief="flat", highlightthickness=1,
                highlightbackground="#334155", highlightcolor="#38bdf8"
            )
            ent.grid(row=row_idx, column=1, sticky="ew", pady=3, ipady=4, padx=(10, 0))
            self.entries[key] = ent
            row_idx += 1

        self.entries["student_id"].bind("<Return>", self.autofill_student)
        self.entries["student_id"].bind("<FocusOut>", self.autofill_student)

        form_frame.columnconfigure(1, weight=1)

        btn_frame = tk.Frame(form_frame, bg="#1e293b")
        btn_frame.grid(row=row_idx, column=0, columnspan=2, pady=(14, 0), sticky="ew")

        sign_btn = tk.Button(
            btn_frame, text="✔ TIME-IN ATTENDANCE", font=("Segoe UI", 10, "bold"),
            bg="#10b981", fg="#ffffff", activebackground="#059669", activeforeground="#ffffff",
            relief="flat", cursor="hand2", command=self.handle_signin, pady=9
        )
        sign_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        add_hover_effect(sign_btn, "#10b981", "#059669")

        clear_btn = tk.Button(
            btn_frame, text="CLEAR ALL", font=("Segoe UI", 10, "bold"),
            bg="#475569", fg="#ffffff", activebackground="#334155", activeforeground="#ffffff",
            relief="flat", cursor="hand2", command=self.clear_form, pady=9, padx=16
        )
        clear_btn.pack(side="right")
        add_hover_effect(clear_btn, "#475569", "#334155")

        slip_frame = tk.LabelFrame(
            container, text=" Live Confirmation Receipt ", font=("Segoe UI", 11, "bold"),
            fg="#f8fafc", bg="#1e293b", padx=18, pady=12, bd=1, relief="solid"
        )
        slip_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))

        self.receipt_box = tk.Text(
            slip_frame, font=("Consolas", 10), bg="#090d16", fg="#4ade80",
            relief="flat", padx=16, pady=16, wrap="word"
        )
        self.receipt_box.pack(fill="both", expand=True)
        self.show_default_receipt()

    def refresh_event_dropdown(self):
        conn = get_connection()
        if not conn:
            return
        cursor = get_cursor(conn)
        try:
            cursor.execute("SELECT event_id, name, CAST(date AS CHAR) FROM events ORDER BY event_id DESC LIMIT 30")
            rows = cursor.fetchall()
            self.events_map = {f"{r[1]} ({r[2]})": r[0] for r in rows}
            self.event_combo["values"] = ["-- New Event --"] + list(self.events_map.keys())
            if not self.event_combo.get():
                self.event_combo.set("-- New Event --")
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load events:\n{e}")
        finally:
            cursor.close()
            conn.close()

    def on_select_existing_event(self, event=None):
        selected = self.event_combo.get()
        if selected == "-- New Event --" or selected not in self.events_map:
            for k in ("event_name", "event_date", "event_time", "organization", "venue", "description"):
                self.entries[k].delete(0, "end")
            return

        ev_id = self.events_map[selected]
        conn = get_connection()
        if not conn:
            return
        cursor = get_cursor(conn)
        try:
            cursor.execute(
                "SELECT name, CAST(date AS CHAR), CAST(time AS CHAR), organization, venue, description FROM events WHERE event_id = %s",
                (ev_id,)
            )
            row = cursor.fetchone()
            if row:
                keys = ("event_name", "event_date", "event_time", "organization", "venue", "description")
                for k, val in zip(keys, row):
                    self.entries[k].delete(0, "end")
                    if val is not None:
                        text_val = str(val).split(".")[0] if k == "event_time" else str(val)
                        self.entries[k].insert(0, text_val)
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load event:\n{e}")
        finally:
            cursor.close()
            conn.close()

    def autofill_student(self, event=None):
        st_id = self.entries["student_id"].get().strip()
        if not st_id:
            return

        conn = get_connection()
        if not conn:
            return
        cursor = get_cursor(conn)
        try:
            cursor.execute("""
                SELECT s.name, d.department_name, s.year_level, s.section
                FROM students s
                LEFT JOIN department d ON s.department_id = d.department_id
                WHERE s.student_id = %s
            """, (st_id,))
            row = cursor.fetchone()
            if row:
                fields = ("name", "dept", "year_level", "section")
                for key, val in zip(fields, row):
                    self.entries[key].delete(0, "end")
                    if val is not None:
                        self.entries[key].insert(0, str(val))
                self.autofill_lbl.config(text="✔ Returning student auto-filled!", fg="#4ade80")
            else:
                self.autofill_lbl.config(text="New student ID (enter details)", fg="#38bdf8")
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to lookup student:\n{e}")
        finally:
            cursor.close()
            conn.close()

    def show_default_receipt(self):
        self.receipt_box.delete("1.0", "end")
        self.receipt_box.insert("1.0", """==================================================
        ATTENDANCE CONFIRMATION RECEIPT
==================================================
1. Fill out Event Details (or select an existing
   event from the Quick Load dropdown).
2. Enter Student ID (auto-fills returning students)
   and click [TIME-IN ATTENDANCE].
==================================================""")

    def handle_signin(self):
        event_name = self.entries["event_name"].get().strip()
        event_date = self.entries["event_date"].get().strip()
        event_time = self.entries["event_time"].get().strip()
        org_name   = self.entries["organization"].get().strip() or "-"
        venue_name = self.entries["venue"].get().strip() or "-"
        desc_text  = self.entries["description"].get().strip() or ""

        st_id = self.entries["student_id"].get().strip()
        name  = self.entries["name"].get().strip()
        dept  = self.entries["dept"].get().strip() or "General"
        year_raw = self.entries["year_level"].get().strip()
        sec   = self.entries["section"].get().strip() or "-"

        if not event_name or not st_id or not name:
            messagebox.showwarning("Incomplete Form", "Event Name, Student ID, and Full Name are required.")
            return

        formatted_date = parse_event_date(event_date)
        if not formatted_date:
            messagebox.showwarning("Invalid Date", f"Invalid Event Date '{event_date}'. Use YYYY-MM-DD or MM/DD/YYYY.")
            return

        formatted_time = parse_event_time(event_time)
        if not formatted_time:
            messagebox.showwarning("Invalid Time", f"Invalid Event Time '{event_time}'. Use HH:MM or HH:MM AM/PM.")
            return

        year_val = int(year_raw) if year_raw.isdigit() else 1

        conn = get_connection()
        if not conn:
            return

        cursor = get_cursor(conn)
        try:
            # 1. Save or get Event
            cursor.execute(
                "SELECT event_id, organization, venue, description FROM events WHERE name = %s AND date = %s",
                (event_name, formatted_date)
            )
            ev_row = cursor.fetchone()
            if ev_row:
                event_id = ev_row[0]
                org_name = ev_row[1] or org_name
                venue_name = ev_row[2] or venue_name
                desc_text = ev_row[3] or desc_text
            else:
                cursor.execute(
                    "INSERT INTO events (name, date, time, description, venue, organization) VALUES (%s, %s, %s, %s, %s, %s)",
                    (event_name, formatted_date, formatted_time, desc_text, venue_name, org_name)
                )
                conn.commit()
                event_id = cursor.lastrowid

            # 2. Save or get Department (matching unique department_name)
            if dept.isdigit():
                cursor.execute("SELECT department_id, department_name FROM department WHERE department_id = %s", (int(dept),))
            else:
                cursor.execute("SELECT department_id, department_name FROM department WHERE LOWER(department_name) = LOWER(%s)", (dept,))
            drow = cursor.fetchone()

            if drow:
                dept_id = str(drow[0])
                dept_label = drow[1]
            else:
                dept_name_val = f"Department {dept}" if dept.isdigit() else dept
                cursor.execute("INSERT INTO department (department_name) VALUES (%s)", (dept_name_val,))
                conn.commit()
                dept_id = str(cursor.lastrowid)
                dept_label = dept_name_val

            # 3. Insert or update Student (student_id is VARCHAR(50))
            cursor.execute("SELECT student_id FROM students WHERE student_id = %s", (st_id,))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE students SET name = %s, department_id = %s, year_level = %s, section = %s WHERE student_id = %s",
                    (name, dept_id, year_val, sec, st_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO students (student_id, name, department_id, year_level, section) VALUES (%s, %s, %s, %s, %s)",
                    (st_id, name, dept_id, year_val, sec)
                )
            conn.commit()

            # 4. Prevent duplicate active Time-In (FIXED: reads cursor.fetchone())
            cursor.execute(
                "SELECT attendance_id FROM attendance WHERE event_id = %s AND student_id = %s AND status = 'PRESENT' AND check_out IS NULL",
                (event_id, st_id)
            )
            if cursor.fetchone():
                messagebox.showwarning("Already Timed-In", f"Student '{name}' ({st_id}) is already timed-in for '{event_name}'.")
                return

            # 5. Insert attendance into check_in (time(6))
            check_time = datetime.now().strftime("%H:%M:%S.%f")
            cursor.execute(
                "INSERT INTO attendance (event_id, student_id, check_in, check_out, status) VALUES (%s, %s, %s, NULL, 'PRESENT')",
                (event_id, st_id, check_time)
            )
            conn.commit()

            now_str = datetime.now().strftime("%I:%M %p (%B %d, %Y)")
            receipt_text = f"""************************************************
               TIME-IN ATTENDANCE RECEIPT       
************************************************
EVENT DETAILS:
  Event Name  : {event_name}
  Organization: {org_name}
  Venue       : {venue_name}
  Date & Time : {formatted_date} | {formatted_time}
--------------------------------------------------
STUDENT DETAILS:
  Student ID  : {st_id}
  Name        : {name}
  Department  : {dept_label}
  Year & Sec  : Year {year_val} - {sec}
  Check-In    : {now_str}
  Status      : [PRESENT]
************************************************"""
            self.receipt_box.delete("1.0", "end")
            self.receipt_box.insert("1.0", receipt_text)

            self.clear_student_only()
            self.refresh_event_dropdown()
            self.load_attendance_logs()
            messagebox.showinfo("Success", f"Time-In recorded for {name}!")

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Database Error", str(e))
        finally:
            cursor.close()
            conn.close()

    def clear_student_only(self):
        for key in ("student_id", "name", "dept", "year_level", "section"):
            self.entries[key].delete(0, "end")
        self.autofill_lbl.config(text="(Press Enter on Student ID to auto-fill)", fg="#94a3b8")
        self.entries["student_id"].focus()

    def clear_form(self):
        for ent in self.entries.values():
            ent.delete(0, "end")
        self.event_combo.set("-- New Event --")
        self.autofill_lbl.config(text="(Press Enter on Student ID to auto-fill)", fg="#94a3b8")
        self.entries["event_name"].focus()

    # ---------------- TAB 2: TIME-OUT ----------------
    def build_logout_tab(self):
        container = tk.Frame(self.tab_logout, bg="#0f172a")
        container.pack(fill="both", expand=True, padx=6, pady=8)

        left_card = tk.LabelFrame(
            container, text=" Student Time-Out (Log-Out) ", font=("Segoe UI", 11, "bold"),
            fg="#f8fafc", bg="#1e293b", padx=22, pady=22, bd=1, relief="solid"
        )
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(left_card, text="Enter Student ID :", font=("Segoe UI", 11, "bold"), fg="#cbd5e1", bg="#1e293b").pack(anchor="w", pady=(10, 6))

        self.logout_id_entry = tk.Entry(
            left_card, font=("Segoe UI", 13), bg="#0f172a", fg="#ffffff",
            insertbackground="#38bdf8", relief="flat", highlightthickness=1,
            highlightbackground="#334155", highlightcolor="#38bdf8"
        )
        self.logout_id_entry.pack(fill="x", ipady=8, pady=(0, 18))
        self.logout_id_entry.bind("<Return>", lambda e: self.handle_logout())

        logout_btn = tk.Button(
            left_card, text="✔ RECORD TIME-OUT", font=("Segoe UI", 11, "bold"),
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff",
            relief="flat", cursor="hand2", command=self.handle_logout, pady=11
        )
        logout_btn.pack(fill="x")
        add_hover_effect(logout_btn, "#0284c7", "#0369a1")

        right_card = tk.LabelFrame(
            container, text=" Time-Out Confirmation Receipt ", font=("Segoe UI", 11, "bold"),
            fg="#f8fafc", bg="#1e293b", padx=20, pady=20, bd=1, relief="solid"
        )
        right_card.pack(side="right", fill="both", expand=True, padx=(10, 0))

        self.logout_receipt_box = tk.Text(
            right_card, font=("Consolas", 10), bg="#090d16", fg="#38bdf8",
            relief="flat", padx=16, pady=16, wrap="word"
        )
        self.logout_receipt_box.pack(fill="both", expand=True)
        self.logout_receipt_box.insert("1.0", """==================================================
              TIME-OUT CONFIRMATION RECEIPT
==================================================
Enter Student ID on the left and click
[RECORD TIME-OUT] to update active Time-In row.
==================================================""")

    def handle_logout(self):
        st_id = self.logout_id_entry.get().strip()
        if not st_id:
            messagebox.showwarning("Missing Student ID", "Student ID is required.")
            return

        conn = get_connection()
        if not conn:
            return

        cursor = get_cursor(conn)
        try:
            cursor.execute("""
                SELECT s.name, d.department_name, s.year_level, s.section
                FROM students s
                LEFT JOIN department d ON s.department_id = d.department_id
                WHERE s.student_id = %s
            """, (st_id,))
            student = cursor.fetchone()

            if not student:
                messagebox.showerror("Not Found", f"Student ID '{st_id}' is not registered in the system.")
                return

            cursor.execute("""
                SELECT a.attendance_id, CAST(a.check_in AS CHAR), COALESCE(e.name, CONCAT('Event #', a.event_id))
                FROM attendance a
                LEFT JOIN events e ON a.event_id = e.event_id
                WHERE a.student_id = %s AND a.status = 'PRESENT' AND (a.check_out IS NULL OR a.check_out = '00:00:00')
                ORDER BY a.attendance_id DESC LIMIT 1
            """, (st_id,))
            active_log = cursor.fetchone()

            if not active_log:
                messagebox.showwarning("No Active Time-In", f"No active Time-In record found for Student ID '{st_id}'.")
                return

            att_id, check_in_val, event_name = active_log
            logout_dt = datetime.now()
            logout_time_db = logout_dt.strftime("%H:%M:%S.%f")

            cursor.execute(
                "UPDATE attendance SET check_out = %s, status = 'LOGGED-OUT' WHERE attendance_id = %s",
                (logout_time_db, att_id)
            )
            conn.commit()

            now_str = logout_dt.strftime("%I:%M %p (%B %d, %Y)")
            slip = f"""************************************************
             STUDENT TIME-OUT (LOG-OUT)       
************************************************
  Event Name  : {event_name or '-'}
  Student ID  : {st_id}
  Name        : {student[0] or '-'}
  Department  : {student[1] or '-'}
  Year & Sec  : Year {student[2] or '-'} - {student[3] or '-'}
  Check-In    : {format_time_str(check_in_val)}
  Check-Out   : {now_str}
  Status      : [LOGGED-OUT]
************************************************"""
            self.logout_receipt_box.delete("1.0", "end")
            self.logout_receipt_box.insert("1.0", slip)

            self.logout_id_entry.delete(0, "end")
            self.load_attendance_logs()
            messagebox.showinfo("Success", f"Time-out recorded for {student[0] or st_id}!")

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Database Error", str(e))
        finally:
            cursor.close()
            conn.close()

    # ---------------- TAB 3: LIVE SEARCHABLE LOGS ----------------
    def build_logs_tab(self):
        top_bar = tk.Frame(self.tab_logs, bg="#0f172a", pady=8)
        top_bar.pack(fill="x")

        tk.Label(top_bar, text="🔍 Search:", font=("Segoe UI", 10, "bold"), fg="#cbd5e1", bg="#0f172a").pack(side="left", padx=(0, 6))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_logs_table())

        search_entry = tk.Entry(
            top_bar, textvariable=self.search_var, font=("Segoe UI", 10),
            bg="#1e293b", fg="#ffffff", insertbackground="#38bdf8",
            relief="flat", highlightthickness=1, highlightbackground="#334155", highlightcolor="#38bdf8", width=32
        )
        search_entry.pack(side="left", ipady=4, padx=(0, 14))

        self.stats_lbl = tk.Label(
            top_bar, text="Total Records: 0",
            font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b", padx=12, pady=5
        )
        self.stats_lbl.pack(side="left")

        refresh_btn = tk.Button(
            top_bar, text="↻ REFRESH", font=("Segoe UI", 9, "bold"),
            bg="#0284c7", fg="#ffffff", relief="flat", cursor="hand2",
            command=self.load_attendance_logs, padx=14, pady=5
        )
        refresh_btn.pack(side="right")
        add_hover_effect(refresh_btn, "#0284c7", "#0369a1")

        table_frame = tk.Frame(self.tab_logs, bg="#1e293b", highlightthickness=1, highlightbackground="#334155")
        table_frame.pack(fill="both", expand=True)

        columns = ("log_id", "event", "student_id", "name", "dept", "year_sec", "check_in", "check_out", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        headers = {
            "log_id": ("ID", 50),
            "event": ("EVENT", 160),
            "student_id": ("STUDENT ID", 105),
            "name": ("NAME", 145),
            "dept": ("DEPT", 85),
            "year_sec": ("YR & SEC", 100),
            "check_in": ("CHECK-IN", 110),
            "check_out": ("CHECK-OUT", 130),
            "status": ("STATUS", 105)
        }

        for col, (title, width) in headers.items():
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="center" if col in ("log_id", "check_in", "check_out", "status") else "w")

        self.tree.tag_configure("present", foreground="#fbbf24")
        self.tree.tag_configure("logged_out", foreground="#4ade80")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def load_attendance_logs(self):
        conn = get_connection()
        if not conn:
            return

        cursor = get_cursor(conn)
        try:
            query = """
                SELECT 
                    a.attendance_id,
                    COALESCE(e.name, CONCAT('Event #', a.event_id)),
                    a.student_id,
                    s.name,
                    d.department_name,
                    s.year_level,
                    s.section,
                    CAST(a.check_in AS CHAR),
                    CAST(a.check_out AS CHAR),
                    a.status
                FROM attendance a
                LEFT JOIN events e ON a.event_id = e.event_id
                LEFT JOIN students s ON a.student_id = s.student_id
                LEFT JOIN department d ON s.department_id = d.department_id
                ORDER BY a.attendance_id DESC
            """
            cursor.execute(query)
            self.all_logs_cache = []
            for r in cursor.fetchall():
                log_id = r[0]
                ev_name = r[1] or "-"
                st_id = r[2]
                name = r[3] or "-"
                dept = r[4] or "-"
                yr_sec = f"Y{r[5]} {r[6]}" if r[5] and r[6] else (str(r[6]) if r[6] else "-")
                c_in = format_time_str(r[7])
                status = r[9] if r[9] else "LOGGED-OUT"
                c_out_raw = format_time_str(r[8])
                c_out = "Active / In-Event" if (status == "PRESENT" and c_out_raw == "-") else c_out_raw
                self.all_logs_cache.append((log_id, ev_name, st_id, name, dept, yr_sec, c_in, c_out, status))

            self.filter_logs_table()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load logs:\n{e}")
        finally:
            cursor.close()
            conn.close()

    def filter_logs_table(self):
        query_text = self.search_var.get().strip().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)

        total_count = 0

        for item in self.all_logs_cache:
            if query_text and not any(query_text in str(val).lower() for val in item):
                continue

            total_count += 1
            status = item[8]
            tag = "logged_out" if status == "LOGGED-OUT" else "present"

            self.tree.insert("", "end", values=item, tags=(tag,))

        self.stats_lbl.config(text=f"Total Records: {total_count}")


if __name__ == "__main__":
    init_database()
    root = tk.Tk()
    app = AuthWindow(root)
    root.mainloop()