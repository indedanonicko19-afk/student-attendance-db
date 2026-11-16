import os
import sys
import time
import getpass
from datetime import datetime
import mysql.connector

# Enable ANSI colors on Windows Terminal / CMD
if os.name == "nt":
    os.system("")

# ANSI Color Palette (Modern Dark Cyan / Emerald Aesthetic)
C_RESET   = "\033[0m"
C_BOLD    = "\033[1m"
C_DIM     = "\033[2m"
C_CYAN    = "\033[96m"
C_BLUE    = "\033[94m"
C_GREEN   = "\033[92m"
C_YELLOW  = "\033[93m"
C_RED     = "\033[91m"
C_WHITE   = "\033[97m"
C_GRAY    = "\033[90m"

# Database Configuration (XAMPP MySQL)
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "student_attendance_event"
}


# ---------------- UI & TRANSITION HELPERS ----------------
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def transition_effect(message="Loading", duration=0.45):
    """Smooth terminal loading animation between screens."""
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    idx = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r  {C_CYAN}{frames[idx % len(frames)]} {message}...{C_RESET}")
        sys.stdout.flush()
        time.sleep(0.05)
        idx += 1
    sys.stdout.write("\r" + " " * (len(message) + 15) + "\r")
    sys.stdout.flush()


def print_banner(subtitle="ADMIN MANAGEMENT CONSOLE"):
    clear_screen()
    print(f"{C_CYAN}{C_BOLD}╔══════════════════════════════════════════════════════════════════════════╗")
    print(f"║                   STUDENT EVENT ATTENDANCE SYSTEM                        ║")
    print(f"║{C_RESET}{C_DIM}{subtitle.center(74)}{C_RESET}{C_CYAN}{C_BOLD}║")
    print(f"╚══════════════════════════════════════════════════════════════════════════╝{C_RESET}")


# ---------------- DATABASE HELPERS ----------------
def get_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        print(f"\n  {C_RED}[!] Database Connection Error: {e}{C_RESET}")
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

        cursor.execute("SELECT COUNT(*) FROM admin")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO admin (username, password) VALUES ('admin', 'password123')")

        conn.commit()
    except Exception as e:
        print(f"\n  {C_RED}[!] Database Initialization Error: {e}{C_RESET}")
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


# ---------------- ADMIN REGISTRATION & LOGIN PORTAL ----------------
def create_admin_account():
    print_banner("CREATE NEW ADMIN ACCOUNT")
    print(f"\n  {C_GRAY}┌──────────────────────────────────────────────────────────────────────┐")
    print(f"  │  {C_WHITE}{C_BOLD}Register a new administrator account (Saved permanently in MySQL){C_RESET}{C_GRAY}   │")
    print(f"  └──────────────────────────────────────────────────────────────────────┘{C_RESET}\n")

    new_user = input(f"  {C_CYAN}❯ New Username     :{C_RESET} ").strip()
    new_pass = getpass.getpass(f"  {C_CYAN}❯ New Password     :{C_RESET} ").strip()
    conf_pass = getpass.getpass(f"  {C_CYAN}❯ Confirm Password :{C_RESET} ").strip()

    if not new_user or not new_pass:
        print(f"\n  {C_YELLOW}[!] Username and password cannot be empty.{C_RESET}")
        time.sleep(1.5)
        return False

    if new_pass != conf_pass:
        print(f"\n  {C_RED}[!] Passwords do not match! Please try again.{C_RESET}")
        time.sleep(1.5)
        return False

    conn = get_connection()
    if not conn:
        time.sleep(1.5)
        return False

    cursor = get_cursor(conn)
    try:
        cursor.execute("SELECT admin_id FROM admin WHERE username = %s", (new_user,))
        if cursor.fetchone():
            print(f"\n  {C_RED}[!] Username '{new_user}' is already taken. Choose another one.{C_RESET}")
            time.sleep(1.5)
            return False

        cursor.execute("INSERT INTO admin (username, password) VALUES (%s, %s)", (new_user, new_pass))
        conn.commit()
        print(f"\n  {C_GREEN}✔ Account successfully created! You can now log in with '{new_user}'.{C_RESET}")
        time.sleep(1.8)
        return True
    except Exception as e:
        conn.rollback()
        print(f"\n  {C_RED}[!] Registration Error: {e}{C_RESET}")
        time.sleep(1.5)
        return False
    finally:
        cursor.close()
        conn.close()


def admin_login():
    while True:
        print_banner("ADMIN SECURITY & AUTHENTICATION PORTAL")
        print(f"\n  {C_GRAY}┌──────────────────────────────────────────────────────────────────────┐")
        print(f"  │  {C_GREEN}{C_BOLD}[1]{C_RESET} {C_WHITE}Login to Existing Admin Account                                  {C_GRAY}│")
        print(f"  │  {C_CYAN}{C_BOLD}[2]{C_RESET} {C_WHITE}Create New Admin Account (Register)                              {C_GRAY}│")
        print(f"  │  {C_RED}{C_BOLD}[3]{C_RESET} {C_WHITE}Exit System                                                      {C_GRAY}│")
        print(f"  └──────────────────────────────────────────────────────────────────────┘{C_RESET}")

        auth_choice = input(f"\n  {C_CYAN}❯ Enter choice (1-3):{C_RESET} ").strip()

        if auth_choice == "2":
            transition_effect("Opening Registration Page", 0.3)
            create_admin_account()
            continue

        elif auth_choice == "3":
            transition_effect("Shutting down system", 0.4)
            clear_screen()
            print(f"\n  {C_CYAN}Goodbye! System closed safely.{C_RESET}\n")
            sys.exit(0)

        elif auth_choice == "1":
            attempts = 0
            while attempts < 3:
                print_banner("ADMIN LOGIN")
                print(f"\n  {C_GRAY}┌──────────────────────────────────────────────────────────────────────┐")
                print(f"  │  {C_WHITE}{C_BOLD}Please sign in with your Administrator credentials{C_RESET}{C_GRAY}                  │")
                print(f"  └──────────────────────────────────────────────────────────────────────┘{C_RESET}\n")

                username = input(f"  {C_CYAN}❯ Username :{C_RESET} ").strip()
                password = getpass.getpass(f"  {C_CYAN}❯ Password :{C_RESET} ").strip()

                if not username or not password:
                    print(f"\n  {C_YELLOW}[!] Username and password cannot be empty.{C_RESET}")
                    time.sleep(1.2)
                    continue

                transition_effect("Verifying credentials", 0.5)

                conn = get_connection()
                if not conn:
                    time.sleep(1.5)
                    break

                cursor = get_cursor(conn)
                try:
                    cursor.execute(
                        "SELECT admin_id, username FROM admin WHERE username = %s AND password = %s",
                        (username, password)
                    )
                    admin = cursor.fetchone()
                    if admin:
                        print(f"  {C_GREEN}✔ Access Granted! Welcome, {C_BOLD}{admin[1]}{C_RESET}{C_GREEN}.{C_RESET}")
                        time.sleep(0.8)
                        return admin[1]
                    else:
                        attempts += 1
                        remaining = 3 - attempts
                        print(f"  {C_RED}✖ Invalid username or password. ({remaining} attempt(s) left){C_RESET}")
                        time.sleep(1.3)
                except Exception as e:
                    print(f"  {C_RED}[!] Login Error: {e}{C_RESET}")
                    time.sleep(1.5)
                finally:
                    cursor.close()
                    conn.close()

            print(f"\n  {C_RED}{C_BOLD}[!] Too many failed login attempts. Returning to main portal.{C_RESET}")
            time.sleep(1.5)
        else:
            print(f"\n  {C_RED}[!] Invalid option. Please enter 1, 2, or 3.{C_RESET}")
            time.sleep(1)


# ---------------- CORE ATTENDANCE FUNCTIONS ----------------
def save_or_get_event(cursor, conn, event_name, event_date, event_time, org_name, venue_name, desc_text):
    formatted_date = parse_event_date(event_date)
    if not formatted_date:
        raise ValueError(f"Invalid date format '{event_date}'. Use YYYY-MM-DD or MM/DD/YYYY.")

    formatted_time = parse_event_time(event_time)
    if not formatted_time:
        raise ValueError(f"Invalid time format '{event_time}'. Use HH:MM or HH:MM AM/PM.")

    org_val = org_name or "-"
    venue_val = venue_name or "-"
    desc_val = desc_text or ""

    cursor.execute(
        "SELECT event_id, CAST(time AS CHAR), description, venue, organization FROM events WHERE name = %s AND date = %s",
        (event_name, formatted_date)
    )
    existing = cursor.fetchone()

    if existing:
        event_id = existing[0]
        saved_time = format_time_str(existing[1])
        saved_desc = existing[2] or desc_val
        saved_venue = existing[3] or venue_val
        saved_org = existing[4] or org_val
    else:
        cursor.execute("""
            INSERT INTO events (name, date, time, description, venue, organization)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (event_name, formatted_date, formatted_time, desc_val, venue_val, org_val))
        conn.commit()
        event_id = cursor.lastrowid
        saved_time = formatted_time
        saved_desc = desc_val
        saved_venue = venue_val
        saved_org = org_val

    return {
        "event_id": event_id,
        "name": event_name,
        "organization": saved_org,
        "venue": saved_venue,
        "description": saved_desc,
        "date": formatted_date,
        "time": saved_time
    }


def record_attendance(event_name, event_date, event_time, org_name, venue_name, desc_text,
                      student_id_input, name_input, dept_input, year_input, sec_input):
    conn = get_connection()
    if not conn:
        return False, None, "Database connection failure."

    cursor = get_cursor(conn)
    try:
        event_info = save_or_get_event(
            cursor, conn, event_name, event_date, event_time, org_name, venue_name, desc_text
        )

        dept_clean = dept_input or "General"
        if dept_clean.isdigit():
            cursor.execute("SELECT department_id, department_name FROM department WHERE department_id = %s", (int(dept_clean),))
        else:
            cursor.execute("SELECT department_id, department_name FROM department WHERE LOWER(department_name) = LOWER(%s)", (dept_clean,))
        dept_row = cursor.fetchone()

        if dept_row:
            dept_id = str(dept_row[0])
            dept_label = dept_row[1]
        else:
            dept_name_val = f"Department {dept_clean}" if dept_clean.isdigit() else dept_clean
            cursor.execute("INSERT INTO department (department_name) VALUES (%s)", (dept_name_val,))
            conn.commit()
            dept_id = str(cursor.lastrowid)
            dept_label = dept_name_val

        year_val = int(year_input) if year_input.isdigit() else 1
        sec_val = sec_input or "-"

        cursor.execute("SELECT student_id FROM students WHERE student_id = %s", (student_id_input,))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE students SET name = %s, department_id = %s, year_level = %s, section = %s WHERE student_id = %s",
                (name_input, dept_id, year_val, sec_val, student_id_input)
            )
        else:
            cursor.execute(
                "INSERT INTO students (student_id, name, department_id, year_level, section) VALUES (%s, %s, %s, %s, %s)",
                (student_id_input, name_input, dept_id, year_val, sec_val)
            )
        conn.commit()

        cursor.execute(
            "SELECT attendance_id FROM attendance WHERE event_id = %s AND student_id = %s AND status = 'PRESENT' AND check_out IS NULL",
            (event_info["event_id"], student_id_input)
        )
        if cursor.fetchone():
            return False, None, f"Student '{name_input}' ({student_id_input}) is already timed-in for this event."

        check_in_time = datetime.now().strftime("%H:%M:%S.%f")
        cursor.execute(
            "INSERT INTO attendance (event_id, student_id, check_in, check_out, status) VALUES (%s, %s, %s, NULL, 'PRESENT')",
            (event_info["event_id"], student_id_input, check_in_time)
        )
        conn.commit()

        receipt_data = {
            "student_id": student_id_input,
            "name": name_input,
            "department": dept_label,
            "year_level": str(year_val),
            "section": sec_val,
            "check_in": datetime.now().strftime("%I:%M %p (%B %d, %Y)"),
            "status": "PRESENT",
            "event": event_info
        }
        return True, receipt_data, None

    except Exception as err:
        conn.rollback()
        return False, None, str(err)
    finally:
        cursor.close()
        conn.close()


def record_logout(student_id_input):
    conn = get_connection()
    if not conn:
        return False, None, "Database connection failure."

    cursor = get_cursor(conn)
    try:
        cursor.execute("""
            SELECT s.name, d.department_name, s.year_level, s.section
            FROM students s
            LEFT JOIN department d ON s.department_id = d.department_id
            WHERE s.student_id = %s
        """, (student_id_input,))
        student = cursor.fetchone()

        if not student:
            return False, None, f"Student ID '{student_id_input}' is not registered in the system."

        cursor.execute("""
            SELECT a.attendance_id, CAST(a.check_in AS CHAR), COALESCE(e.name, CONCAT('Event #', a.event_id))
            FROM attendance a
            LEFT JOIN events e ON a.event_id = e.event_id
            WHERE a.student_id = %s AND a.status = 'PRESENT' AND (a.check_out IS NULL OR a.check_out = '00:00:00')
            ORDER BY a.attendance_id DESC LIMIT 1
        """, (student_id_input,))
        active_log = cursor.fetchone()

        if not active_log:
            return False, None, f"No active Time-In record found for Student ID '{student_id_input}'."

        att_id, check_in_val, event_name = active_log
        logout_dt = datetime.now()
        logout_time_db = logout_dt.strftime("%H:%M:%S.%f")

        cursor.execute(
            "UPDATE attendance SET check_out = %s, status = 'LOGGED-OUT' WHERE attendance_id = %s",
            (logout_time_db, att_id)
        )
        conn.commit()

        logout_data = {
            "event_name": event_name or "-",
            "student_id": student_id_input,
            "name": student[0] or "-",
            "department": student[1] or "-",
            "year_level": str(student[2]) if student[2] is not None else "-",
            "section": student[3] or "-",
            "check_in": format_time_str(check_in_val),
            "check_out": logout_dt.strftime("%I:%M %p (%B %d, %Y)"),
            "status": "LOGGED-OUT"
        }
        return True, logout_data, None

    except Exception as err:
        conn.rollback()
        return False, None, str(err)
    finally:
        cursor.close()
        conn.close()


def view_logs():
    transition_effect("Fetching attendance logs", 0.4)
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
        rows = cursor.fetchall()

        print_banner("ATTENDANCE LOG SHEET (SINGLE-ROW VIEW)")
        print(f"\n{C_CYAN}{C_BOLD}{'ID':<5} {'EVENT':<18} {'STUD ID':<12} {'NAME':<16} {'DEPT':<8} {'YR/SEC':<11} {'CHECK-IN':<11} {'CHECK-OUT':<18} {'STATUS':<11}{C_RESET}")
        print(f"{C_GRAY}{'─' * 118}{C_RESET}")

        if not rows:
            print(f"  {C_YELLOW}No attendance records found.{C_RESET}")
        else:
            for r in rows:
                log_id    = str(r[0])
                ev_name   = (str(r[1])[:16] + "..") if r[1] and len(str(r[1])) > 18 else (str(r[1]) if r[1] else "-")
                st_id     = str(r[2])
                st_name   = (str(r[3])[:14] + "..") if r[3] and len(str(r[3])) > 16 else (str(r[3]) if r[3] else "-")
                st_dept   = (str(r[4])[:6] + "..") if r[4] and len(str(r[4])) > 8 else (str(r[4]) if r[4] else "-")
                yr_sec    = f"Y{r[5]} {r[6]}" if r[5] and r[6] else (str(r[6]) if r[6] else "-")
                yr_sec    = (yr_sec[:9] + "..") if len(yr_sec) > 11 else yr_sec
                c_in      = format_time_str(r[7])
                st_status = str(r[9]) if r[9] else "LOGGED-OUT"
                c_out_raw = format_time_str(r[8])
                c_out     = "Active / In-Event" if (st_status == "PRESENT" and c_out_raw == "-") else c_out_raw

                status_color = C_GREEN if st_status == "LOGGED-OUT" else C_YELLOW
                c_out_color  = C_DIM if c_out == "Active / In-Event" else C_WHITE

                print(
                    f"{C_WHITE}{log_id:<5} {ev_name:<18} {st_id:<12} {st_name:<16} {st_dept:<8} "
                    f"{yr_sec:<11} {c_in:<11} {c_out_color}{c_out:<18}{C_RESET} {status_color}{st_status:<11}{C_RESET}"
                )
        print(f"{C_GRAY}{'─' * 118}{C_RESET}")
    except Exception as e:
        print(f"  {C_RED}[!] Error fetching logs: {e}{C_RESET}")
    finally:
        cursor.close()
        conn.close()


# ---------------- MAIN APPLICATION LOOP ----------------
def main():
    init_database()
    current_admin = admin_login()
    if not current_admin:
        return

    while True:
        print_banner(f"LOGGED IN AS: {current_admin.upper()}")
        print(f"\n  {C_GRAY}┌──────────────────────────────────────────────────────────────────────┐")
        print(f"  │  {C_GREEN}{C_BOLD}[1]{C_RESET} {C_WHITE}Sign-in Attendance (Time-In)                                     {C_GRAY}│")
        print(f"  │  {C_CYAN}{C_BOLD}[2]{C_RESET} {C_WHITE}Sign-out Attendance (Time-Out)                                   {C_GRAY}│")
        print(f"  │  {C_BLUE}{C_BOLD}[3]{C_RESET} {C_WHITE}View Attendance Log Sheet                                        {C_GRAY}│")
        print(f"  │  {C_YELLOW}{C_BOLD}[4]{C_RESET} {C_WHITE}Logout Admin                                                     {C_GRAY}│")
        print(f"  │  {C_RED}{C_BOLD}[5]{C_RESET} {C_WHITE}Exit System                                                      {C_GRAY}│")
        print(f"  └──────────────────────────────────────────────────────────────────────┘{C_RESET}")

        choice = input(f"\n  {C_CYAN}❯ Enter choice (1-5):{C_RESET} ").strip()

        if choice == "1":
            transition_effect("Opening Time-In Form", 0.3)
            print_banner("1. SIGN-IN ATTENDANCE (TIME-IN)")

            print(f"\n  {C_CYAN}{C_BOLD}── EVENT DETAILS ──{C_RESET}")
            event_name = input(f"  {C_WHITE}Event Name        :{C_RESET} ").strip()
            event_date = input(f"  {C_WHITE}Event Date        :{C_RESET} ").strip()
            event_time = input(f"  {C_WHITE}Event Time        :{C_RESET} ").strip()
            org_name   = input(f"  {C_WHITE}Organization      :{C_RESET} ").strip()
            venue_name = input(f"  {C_WHITE}Venue             :{C_RESET} ").strip()
            desc_text  = input(f"  {C_WHITE}Event Description :{C_RESET} ").strip()

            print(f"\n  {C_GREEN}{C_BOLD}── STUDENT DETAILS ──{C_RESET}")
            student_id = input(f"  {C_WHITE}Student ID        :{C_RESET} ").strip()
            name       = input(f"  {C_WHITE}Full Name         :{C_RESET} ").strip()
            department = input(f"  {C_WHITE}Department        :{C_RESET} ").strip()
            year_level = input(f"  {C_WHITE}Year Level        :{C_RESET} ").strip()
            section    = input(f"  {C_WHITE}Course & Section  :{C_RESET} ").strip()

            if not event_name or not student_id or not name:
                print(f"\n  {C_YELLOW}[!] Event Name, Student ID, and Full Name are required.{C_RESET}")
                input(f"\n  {C_DIM}Press [ENTER] to return to menu...{C_RESET}")
                continue

            transition_effect("Recording Time-In", 0.4)
            success, receipt, err = record_attendance(
                event_name, event_date, event_time, org_name, venue_name, desc_text,
                student_id, name, department, year_level, section
            )
            if success:
                ev = receipt["event"]
                print(f"\n  {C_GREEN}{C_BOLD}╔════════════════════════════════════════════════════════════════════╗")
                print(f"  ║                   ATTENDANCE TIME-IN RECEIPT                       ║")
                print(f"  ╠════════════════════════════════════════════════════════════════════╣{C_RESET}")
                print(f"  {C_CYAN}  EVENT DETAILS:{C_RESET}")
                print(f"    Event Name   : {C_WHITE}{ev['name']}{C_RESET}")
                print(f"    Organization : {C_WHITE}{ev['organization']}{C_RESET}")
                print(f"    Venue        : {C_WHITE}{ev['venue']}{C_RESET}")
                print(f"    Date & Time  : {C_WHITE}{ev['date']} | {ev['time']}{C_RESET}")
                if ev["description"]:
                    print(f"    Description  : {C_WHITE}{ev['description']}{C_RESET}")
                print(f"  {C_GRAY}  ────────────────────────────────────────────────────────────────────{C_RESET}")
                print(f"  {C_GREEN}  STUDENT DETAILS:{C_RESET}")
                print(f"    Student ID   : {C_WHITE}{receipt['student_id']}{C_RESET}")
                print(f"    Name         : {C_WHITE}{receipt['name']}{C_RESET}")
                print(f"    Department   : {C_WHITE}{receipt['department']}{C_RESET}")
                print(f"    Year & Sec   : {C_WHITE}Year {receipt['year_level']} - {receipt['section']}{C_RESET}")
                print(f"    Check-In     : {C_WHITE}{receipt['check_in']}{C_RESET}")
                print(f"    Status       : {C_GREEN}{C_BOLD}[{receipt['status']}]{C_RESET}")
                print(f"  {C_GREEN}{C_BOLD}╚════════════════════════════════════════════════════════════════════╝{C_RESET}")
            else:
                print(f"\n  {C_RED}[!] Error: {err}{C_RESET}")

            input(f"\n  {C_DIM}Press [ENTER] to return to menu...{C_RESET}")

        elif choice == "2":
            transition_effect("Opening Time-Out Form", 0.3)
            print_banner("2. SIGN-OUT ATTENDANCE (TIME-OUT)")

            print(f"\n  {C_CYAN}{C_BOLD}── STUDENT SIGN-OUT ──{C_RESET}")
            student_id = input(f"  {C_WHITE}Enter Student ID :{C_RESET} ").strip()

            if not student_id:
                print(f"\n  {C_YELLOW}[!] Student ID is required.{C_RESET}")
                input(f"\n  {C_DIM}Press [ENTER] to return to menu...{C_RESET}")
                continue

            transition_effect("Updating attendance record", 0.4)
            success, logout_data, err = record_logout(student_id)
            if success:
                print(f"\n  {C_CYAN}{C_BOLD}╔════════════════════════════════════════════════════════════════════╗")
                print(f"  ║                   ATTENDANCE TIME-OUT RECEIPT                      ║")
                print(f"  ╠════════════════════════════════════════════════════════════════════╣{C_RESET}")
                print(f"    Event Name   : {C_WHITE}{logout_data['event_name']}{C_RESET}")
                print(f"    Student ID   : {C_WHITE}{logout_data['student_id']}{C_RESET}")
                print(f"    Name         : {C_WHITE}{logout_data['name']}{C_RESET}")
                print(f"    Department   : {C_WHITE}{logout_data['department']}{C_RESET}")
                print(f"    Year & Sec   : {C_WHITE}Year {logout_data['year_level']} - {logout_data['section']}{C_RESET}")
                print(f"    Check-In     : {C_WHITE}{logout_data['check_in']}{C_RESET}")
                print(f"    Check-Out    : {C_WHITE}{logout_data['check_out']}{C_RESET}")
                print(f"    Status       : {C_GREEN}{C_BOLD}[{logout_data['status']}]{C_RESET}")
                print(f"  {C_CYAN}{C_BOLD}╚════════════════════════════════════════════════════════════════════╝{C_RESET}")
            else:
                print(f"\n  {C_RED}[!] Error: {err}{C_RESET}")

            input(f"\n  {C_DIM}Press [ENTER] to return to menu...{C_RESET}")

        elif choice == "3":
            view_logs()
            input(f"\n  {C_DIM}Press [ENTER] to return to menu...{C_RESET}")

        elif choice == "4":
            transition_effect("Logging out admin", 0.4)
            current_admin = admin_login()
            if not current_admin:
                return

        elif choice == "5":
            transition_effect("Shutting down system", 0.4)
            clear_screen()
            print(f"\n  {C_CYAN}Goodbye! System closed safely.{C_RESET}\n")
            sys.exit(0)

        else:
            print(f"\n  {C_RED}[!] Invalid option. Please enter 1 to 5.{C_RESET}")
            time.sleep(1)


if __name__ == "__main__":
    main()