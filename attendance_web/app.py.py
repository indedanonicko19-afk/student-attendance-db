import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
if not os.path.isdir(TEMPLATE_DIR):
    TEMPLATE_DIR = os.path.join(BASE_DIR, "..", "templates")

STATIC_DIR = os.path.join(BASE_DIR, "static")
if not os.path.isdir(STATIC_DIR):
    STATIC_DIR = os.path.join(BASE_DIR, "..", "static")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = "student_attendance_secret_key_change_me"

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "student_attendance_event"
}

_db_initialized = False


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def get_cursor(conn, dictionary=True):
    return conn.cursor(buffered=True, dictionary=dictionary)


def init_database():
    conn = get_connection()
    cursor = get_cursor(conn, dictionary=False)
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

        cursor.execute("SHOW COLUMNS FROM attendance LIKE 'check_out'")
        co_info = cursor.fetchone()
        if co_info:
            col_type = str(co_info[1]).lower()
            is_nullable = str(co_info[2]).upper()
            if "int" in col_type or is_nullable == "NO":
                cursor.execute("ALTER TABLE attendance MODIFY check_out TIME(6) NULL DEFAULT NULL")
                cursor.execute("UPDATE attendance SET check_out = NULL WHERE check_out = '00:00:00' OR status = 'PRESENT'")

        cursor.execute("SELECT COUNT(*) FROM admin")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO admin (username, password) VALUES ('admin', 'password123')")

        conn.commit()
    finally:
        cursor.close()
        conn.close()


@app.before_request
def ensure_db_ready():
    global _db_initialized
    if not _db_initialized:
        try:
            init_database()
            _db_initialized = True
        except Exception as e:
            print(f"[DB INIT ERROR] {e}")


def format_time(val):
    if val is None:
        return "-"
    s = str(val).split(".")[0]
    if s in ("", "0", "00:00:00", "None"):
        return "-"
    return s


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin" not in session:
            flash("Please sign in first to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ---------------- AUTH ROUTES ----------------
@app.route("/")
def home():
    if "admin" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "admin" in session and request.method == "GET":
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template("login.html")

        conn = get_connection()
        cursor = get_cursor(conn)
        try:
            cursor.execute(
                "SELECT admin_id, username FROM admin WHERE username = %s AND password = %s",
                (username, password)
            )
            admin = cursor.fetchone()
            if admin:
                session["admin"] = admin["username"]
                flash(f"Welcome back, {admin['username']}!", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid username or password.", "error")
        except Exception as e:
            flash(f"Database error: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template("login.html")


@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    confirm = request.form.get("confirm", "").strip()

    if not username or not password:
        flash("All registration fields are required.", "error")
        return redirect(url_for("login"))

    if password != confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = get_cursor(conn)
    try:
        cursor.execute("SELECT admin_id FROM admin WHERE username = %s", (username,))
        if cursor.fetchone():
            flash(f"Username '{username}' is already taken.", "error")
            return redirect(url_for("login"))

        cursor.execute("INSERT INTO admin (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        flash("Account created! You can now sign in.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Registration failed: {e}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


# ---------------- DASHBOARD & ATTENDANCE ----------------
@app.route("/dashboard")
@login_required
def dashboard():
    search = request.args.get("q", "").strip()
    conn = get_connection()
    cursor = get_cursor(conn)
    try:
        query = """
            SELECT 
                a.attendance_id,
                a.event_id,
                COALESCE(e.name, CONCAT('Event #', a.event_id)) AS event_name,
                a.student_id,
                COALESCE(s.name, '-') AS student_name,
                COALESCE(d.department_name, '-') AS department_name,
                s.year_level,
                s.section,
                CAST(a.check_in AS CHAR) AS check_in,
                CAST(a.check_out AS CHAR) AS check_out,
                a.status
            FROM attendance a
            LEFT JOIN events e ON a.event_id = e.event_id
            LEFT JOIN students s ON a.student_id = s.student_id
            LEFT JOIN department d ON s.department_id = CAST(d.department_id AS CHAR)
        """
        params = []
        if search:
            query += """
                WHERE a.student_id LIKE %s
                   OR s.name LIKE %s
                   OR e.name LIKE %s
                   OR d.department_name LIKE %s
                   OR a.status LIKE %s
            """
            like_val = f"%{search}%"
            params = [like_val, like_val, like_val, like_val, like_val]

        query += " ORDER BY a.attendance_id DESC"
        cursor.execute(query, params)
        raw_logs = cursor.fetchall()

        logs = []
        for row in raw_logs:
            c_in = format_time(row["check_in"])
            c_out_raw = format_time(row["check_out"])
            status = row["status"] or "LOGGED-OUT"
            c_out = "Active / In-Event" if (status == "PRESENT" and c_out_raw == "-") else c_out_raw
            logs.append({
                "attendance_id": row["attendance_id"],
                "event_name": row["event_name"],
                "student_id": row["student_id"],
                "student_name": row["student_name"],
                "department_name": row["department_name"],
                "year_sec": f"Y{row['year_level']} {row['section']}" if row["year_level"] else "-",
                "check_in": c_in,
                "check_out": c_out,
                "status": status
            })

        cursor.execute("""
            SELECT event_id, name, CAST(date AS CHAR) AS event_date, CAST(time AS CHAR) AS event_time, venue, organization
            FROM events ORDER BY event_id DESC
        """)
        events = cursor.fetchall()

        cursor.execute("SELECT department_id, department_name FROM department ORDER BY department_name ASC")
        departments = cursor.fetchall()

        return render_template(
            "dashboard.html",
            admin=session["admin"],
            logs=logs,
            events=events,
            departments=departments,
            search=search,
            total_records=len(logs),
            active_present=sum(1 for l in logs if l["status"] == "PRESENT"),
            logged_out_count=sum(1 for l in logs if l["status"] == "LOGGED-OUT")
        )
    finally:
        cursor.close()
        conn.close()


@app.route("/time-in", methods=["POST"])
@login_required
def time_in():
    selected_event_id = request.form.get("event_id", "").strip()
    event_name = request.form.get("event_name", "").strip()
    event_date = request.form.get("event_date", "").strip() or datetime.now().strftime("%Y-%m-%d")
    event_time = request.form.get("event_time", "").strip() or datetime.now().strftime("%H:%M:%S")
    venue = request.form.get("venue", "").strip() or "-"
    organization = request.form.get("organization", "").strip() or "-"
    description = request.form.get("description", "").strip()

    student_id = request.form.get("student_id", "").strip()
    student_name = request.form.get("student_name", "").strip()
    department = request.form.get("department", "").strip() or "General"
    year_raw = request.form.get("year_level", "").strip()
    section = request.form.get("section", "").strip() or "-"

    if not student_id or not student_name:
        flash("Student ID and Student Name are required.", "error")
        return redirect(url_for("dashboard"))

    if not selected_event_id and not event_name:
        flash("Please select an Event or enter a new Event Name.", "error")
        return redirect(url_for("dashboard"))

    year_val = int(year_raw) if year_raw.isdigit() else 1

    conn = get_connection()
    cursor = get_cursor(conn)
    try:
        if selected_event_id:
            event_id = int(selected_event_id)
        else:
            cursor.execute("SELECT event_id FROM events WHERE name = %s AND date = %s", (event_name, event_date))
            ev_row = cursor.fetchone()
            if ev_row:
                event_id = ev_row["event_id"]
            else:
                cursor.execute(
                    "INSERT INTO events (name, date, time, description, venue, organization) VALUES (%s, %s, %s, %s, %s, %s)",
                    (event_name, event_date, event_time, description, venue, organization)
                )
                conn.commit()
                event_id = cursor.lastrowid

        cursor.execute("SELECT department_id FROM department WHERE LOWER(department_name) = LOWER(%s)", (department,))
        d_row = cursor.fetchone()
        if d_row:
            dept_id = str(d_row["department_id"])
        else:
            cursor.execute("INSERT INTO department (department_name) VALUES (%s)", (department,))
            conn.commit()
            dept_id = str(cursor.lastrowid)

        cursor.execute("SELECT student_id FROM students WHERE student_id = %s", (student_id,))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE students SET name = %s, department_id = %s, year_level = %s, section = %s WHERE student_id = %s",
                (student_name, dept_id, year_val, section, student_id)
            )
        else:
            cursor.execute(
                "INSERT INTO students (student_id, name, department_id, year_level, section) VALUES (%s, %s, %s, %s, %s)",
                (student_id, student_name, dept_id, year_val, section)
            )
        conn.commit()

        cursor.execute(
            "SELECT attendance_id FROM attendance WHERE event_id = %s AND student_id = %s AND status = 'PRESENT' AND (check_out IS NULL OR check_out = '00:00:00')",
            (event_id, student_id)
        )
        if cursor.fetchone():
            flash(f"Student '{student_name}' ({student_id}) is already timed-in for this event.", "error")
            return redirect(url_for("dashboard"))

        now_time = datetime.now().strftime("%H:%M:%S.%f")
        cursor.execute(
            "INSERT INTO attendance (event_id, student_id, check_in, check_out, status) VALUES (%s, %s, %s, NULL, 'PRESENT')",
            (event_id, student_id, now_time)
        )
        conn.commit()
        flash(f"Saved! Time-In recorded for {student_name} ({student_id}).", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Failed to save record: {e}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("dashboard"))


@app.route("/time-out", methods=["POST"])
@login_required
def time_out():
    attendance_id = request.form.get("attendance_id", "").strip()
    student_id = request.form.get("student_id", "").strip()

    conn = get_connection()
    cursor = get_cursor(conn)
    try:
        if attendance_id:
            cursor.execute(
                "SELECT attendance_id, student_id, status FROM attendance WHERE attendance_id = %s",
                (int(attendance_id),)
            )
        elif student_id:
            cursor.execute(
                "SELECT attendance_id, student_id, status FROM attendance WHERE student_id = %s AND status = 'PRESENT' AND (check_out IS NULL OR check_out = '00:00:00') ORDER BY attendance_id DESC LIMIT 1",
                (student_id,)
            )
        else:
            flash("Please provide a Student ID.", "error")
            return redirect(url_for("dashboard"))

        active = cursor.fetchone()
        if not active:
            flash("No active Time-In record found for that student.", "error")
            return redirect(url_for("dashboard"))

        if active["status"] == "LOGGED-OUT":
            flash(f"Student ID {active['student_id']} is already timed out.", "error")
            return redirect(url_for("dashboard"))

        now_time = datetime.now().strftime("%H:%M:%S.%f")
        cursor.execute(
            "UPDATE attendance SET check_out = %s, status = 'LOGGED-OUT' WHERE attendance_id = %s",
            (now_time, active["attendance_id"])
        )
        conn.commit()
        flash(f"Time-Out saved for Student ID {active['student_id']}.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Failed to update Time-Out: {e}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("dashboard"))


@app.route("/attendance/delete/<int:attendance_id>", methods=["POST"])
@login_required
def delete_attendance(attendance_id):
    conn = get_connection()
    cursor = get_cursor(conn)
    try:
        cursor.execute("DELETE FROM attendance WHERE attendance_id = %s", (attendance_id,))
        conn.commit()
        flash(f"Attendance record #{attendance_id} deleted.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting record: {e}", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("dashboard"))


# ---------------- EVENTS MANAGER PAGE ----------------
@app.route("/events", methods=["GET", "POST"])
@login_required
def events_page():
    conn = get_connection()
    cursor = get_cursor(conn)
    try:
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            event_date = request.form.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")
            event_time = request.form.get("time", "").strip() or datetime.now().strftime("%H:%M:%S")
            venue = request.form.get("venue", "").strip() or "-"
            organization = request.form.get("organization", "").strip() or "-"
            description = request.form.get("description", "").strip()

            if not name:
                flash("Event Name is required.", "error")
                return redirect(url_for("events_page"))

            cursor.execute(
                "INSERT INTO events (name, date, time, description, venue, organization) VALUES (%s, %s, %s, %s, %s, %s)",
                (name, event_date, event_time, description, venue, organization)
            )
            conn.commit()
            flash(f"Event '{name}' added!", "success")
            return redirect(url_for("events_page"))

        cursor.execute("""
            SELECT
                e.event_id,
                e.name,
                CAST(e.date AS CHAR) AS event_date,
                CAST(e.time AS CHAR) AS event_time,
                e.venue,
                e.organization,
                COALESCE(e.description, '') AS description,
                (SELECT COUNT(*) FROM attendance a WHERE a.event_id = e.event_id) AS total_attendees
            FROM events e
            ORDER BY e.event_id DESC
        """)
        rows = cursor.fetchall()
        for row in rows:
            row["event_time"] = format_time(row["event_time"])

        return render_template("events.html", admin=session["admin"], events=rows)
    except Exception as e:
        conn.rollback()
        flash(f"Database error: {e}", "error")
        return render_template("events.html", admin=session["admin"], events=[])
    finally:
        cursor.close()
        conn.close()


@app.route("/events/delete/<int:event_id>", methods=["POST"])
@login_required
def delete_event(event_id):
    conn = get_connection()
    cursor = get_cursor(conn)
    try:
        cursor.execute("DELETE FROM events WHERE event_id = %s", (event_id,))
        conn.commit()
        flash(f"Event #{event_id} deleted.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting event: {e}", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("events_page"))


@app.route("/api/student/<student_id>")
@login_required
def lookup_student(student_id):
    conn = get_connection()
    cursor = get_cursor(conn)
    try:
        cursor.execute("""
            SELECT s.name, d.department_name, s.year_level, s.section
            FROM students s
            LEFT JOIN department d ON s.department_id = CAST(d.department_id AS CHAR)
            WHERE s.student_id = %s
        """, (student_id,))
        row = cursor.fetchone()
        if row:
            return jsonify({"found": True, **row})
        return jsonify({"found": False})
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    init_database()
    app.run(debug=True, host="127.0.0.1", port=5000)