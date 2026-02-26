from flask import Flask, request, redirect, session
from datetime import date, datetime
import os
import psycopg2
import psycopg2.extras
import sys

app = Flask(__name__)
app.secret_key = "supersecretkey"

# =====================
# SPRAWDZENIE DATABASE_URL
# =====================
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("❌ Brak DATABASE_URL!", file=sys.stderr)
    raise Exception("Brak DATABASE_URL")
else:
    print("✅ DATABASE_URL znaleziony:", DATABASE_URL)

# =====================
# POŁĄCZENIE Z BAZĄ
# =====================
def db():
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        print("✅ Połączono z bazą danych")
        return conn
    except Exception as e:
        print("❌ Błąd połączenia z bazą:", e, file=sys.stderr)
        raise

# =====================
# INICJALIZACJA BAZY (tylko przy pierwszym uruchomieniu)
# =====================
def init_db():
    try:
        conn = db()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            login TEXT UNIQUE,
            password TEXT,
            role TEXT
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            client TEXT,
            address TEXT,
            date DATE,
            status TEXT,
            driver TEXT,
            quantity REAL,
            payment TEXT,
            amount REAL,
            notes TEXT,
            reason TEXT,
            position INTEGER DEFAULT 1
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS driver_days (
            id SERIAL PRIMARY KEY,
            driver TEXT,
            date DATE,
            closed BOOLEAN DEFAULT FALSE,
            closed_at TIMESTAMP
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS fuel_logs (
            id SERIAL PRIMARY KEY,
            driver TEXT,
            date DATE,
            mileage INTEGER,
            liters REAL
        );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Baza danych zainicjalizowana")
    except Exception as e:
        print("❌ Błąd init_db:", e, file=sys.stderr)
        raise

# =====================
# TWORZENIE UŻYTKOWNIKÓW TESTOWYCH
# =====================
def create_users():
    try:
        conn = db()
        cur = conn.cursor()
        users = [
            ("admin","Turcja123","admin"),
            ("leszek","LKR18456","driver"),
            ("tadeusz","LKR54VN","driver"),
            ("marcel","LKR61886","driver"),
            ("dyzio","LKR40306","driver"),
            ("emil","Turcja123","driver")
        ]
        for u in users:
            cur.execute("INSERT INTO users (login,password,role) VALUES (%s,%s,%s) ON CONFLICT (login) DO NOTHING", u)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Użytkownicy testowi stworzeni")
    except Exception as e:
        print("❌ Błąd create_users:", e, file=sys.stderr)
        raise

# =====================
# POMOCNICZE
# =====================
def is_admin():
    return session.get("role") == "admin"

def is_driver():
    return session.get("role") == "driver"

def status_color(status):
    colors = {
        "DO REALIZACJI":"#cce5ff",
        "W TOKU":"#fff3cd",
        "NIE WYKONANE":"#f8d7da",
        "WYKONANE":"#d4edda"
    }
    return colors.get(status,"#ffffff")

# =====================
# SIDEBAR (jasny)
# =====================
def sidebar():
    return """
    <div style='width:220px;background:#f0f0f0;color:#333;height:100vh;display:inline-block;padding:20px;font-family:Arial;vertical-align:top'>
        <h3 style='margin-bottom:20px'>ADMIN</h3>
        <div style='margin-bottom:10px; padding:8px; border-radius:6px; background:#e0e0e0;'>
            <a href='/admin' style='color:#333; text-decoration:none; display:block'>➕ Nowe zlecenie</a>
        </div>
        <div style='margin-bottom:10px; padding:8px; border-radius:6px; background:#e0e0e0;'>
            <a href='/admin/active' style='color:#333; text-decoration:none; display:block'>📋 Aktywne</a>
        </div>
        <div style='margin-bottom:10px; padding:8px; border-radius:6px; background:#e0e0e0;'>
            <a href='/admin/done' style='color:#333; text-decoration:none; display:block'>✅ Wykonane</a>
        </div>
        <div style='margin-bottom:10px; padding:8px; border-radius:6px; background:#e0e0e0;'>
            <a href='/admin/routes' style='color:#333; text-decoration:none; display:block'>🚛 Trasówki</a>
        </div>
        <div style='margin-top:20px; padding:8px; border-radius:6px; background:#f8d7da;'>
            <a href='/logout' style='color:#721c24; text-decoration:none; display:block'>Wyloguj</a>
        </div>
    </div>
    """

# =====================
# LOGIN
# =====================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        try:
            conn=db()
            cur=conn.cursor()
            cur.execute("SELECT * FROM users WHERE login=%s AND password=%s",
                        (request.form["login"],request.form["password"]))
            user=cur.fetchone()
            cur.close(); conn.close()
            if user:
                session["user"]=user["login"]
                session["role"]=user["role"]
                return redirect("/admin" if user["role"]=="admin" else "/driver")
        except Exception as e:
            print("❌ Błąd login:", e, file=sys.stderr)
            return "<h3>Błąd logowania. Sprawdź konsolę serwera.</h3>"
    return """
    <h2>Logowanie</h2>
    <form method='post'>
    Login:<br><input name='login'><br>
    Hasło:<br><input type='password' name='password'><br><br>
    <button>Zaloguj</button>
    </form>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# =====================
# URUCHOMIENIE SERWERA Z INIT
# =====================
if __name__ == "__main__":
    print("⏳ Startujemy aplikację...")
    try:
        init_db()
        create_users()
        print("✅ Aplikacja gotowa do startu")
    except Exception as e:
        print("❌ Problem przy inicjalizacji:", e, file=sys.stderr)
    app.run(debug=True)
