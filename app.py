from flask import Flask, request, redirect, session
from datetime import date
import os
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("Brak DATABASE_URL")


def db():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )


# =====================
# INIT BAZY
# =====================

def init_db():

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
        position INTEGER DEFAULT 1,
        time_slot TEXT
    );
    """)

    # zabezpieczenie gdy kolumna nie istnieje
    cur.execute("""
    ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS time_slot TEXT;
    """)

    conn.commit()
    cur.close()
    conn.close()


def create_users():

    conn = db()
    cur = conn.cursor()

    users = [
        ("admin", "Turcja123", "admin")
    ]

    for u in users:
        cur.execute(
            "INSERT INTO users (login,password,role) VALUES (%s,%s,%s) ON CONFLICT (login) DO NOTHING",
            u
        )

    conn.commit()
    cur.close()
    conn.close()


init_db()
create_users()


# =====================
# POMOCNICZE
# =====================

def is_admin():
    return session.get("role") == "admin"


def status_color(status):

    colors = {
        "DO REALIZACJI": "#cce5ff",
        "W TOKU": "#fff3cd",
        "NIE WYKONANE": "#f8d7da",
        "WYKONANE": "#d4edda"
    }

    return colors.get(status, "#ffffff")


# =====================
# SIDEBAR
# =====================

def sidebar():

    return """
    <div style='width:220px;background:#f0f0f0;height:100vh;
    display:inline-block;padding:20px;font-family:Arial'>

        <h3>MENU</h3>

        <div style='margin-bottom:10px;padding:10px;background:white;border-radius:6px'>
        <a href='/admin'>➕ Nowe zlecenie</a>
        </div>

        <div style='margin-bottom:10px;padding:10px;background:white;border-radius:6px'>
        <a href='/admin/active'>📋 Aktywne</a>
        </div>

        <div style='margin-bottom:10px;padding:10px;background:white;border-radius:6px'>
        <a href='/admin/done'>✅ Wykonane</a>
        </div>

        <div style='margin-bottom:10px;padding:10px;background:white;border-radius:6px'>
        <a href='/admin/routes'>🚛 Trasówki</a>
        </div>

        <div style='margin-top:30px'>
        <a href='/logout'>Wyloguj</a>
        </div>

    </div>
    """


# =====================
# LOGIN
# =====================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        conn = db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE login=%s AND password=%s",
            (request.form["login"], request.form["password"])
        )

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            session["user"] = user["login"]
            session["role"] = user["role"]

            return redirect("/admin")

    return """
    <h2>Logowanie</h2>

    <form method='post'>

    Login<br>
    <input name='login'><br>

    Hasło<br>
    <input type='password' name='password'><br><br>

    <button>Zaloguj</button>

    </form>
    """


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =====================
# NOWE ZLECENIE
# =====================

@app.route("/admin", methods=["GET", "POST"])
def admin_new():

    if not is_admin():
        return redirect("/")

    if request.method == "POST":

        client = request.form.get("client")
        address = request.form.get("address")
        date_value = request.form.get("date")
        time_slot = request.form.get("time_slot") or None

        conn = db()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO orders (client,address,date,status,time_slot)
            VALUES (%s,%s,%s,'DO REALIZACJI',%s)
            """,
            (client, address, date_value, time_slot)
        )

        conn.commit()

        cur.close()
        conn.close()

        return redirect("/admin")

    return sidebar() + f"""

    <div style='display:inline-block;padding:20px'>

    <h2>Dodaj zamówienie</h2>

    <form method='post'>

    Klient<br>
    <input name='client'><br>

    Adres<br>
    <input name='address'><br>

    Data<br>
    <input type='date' name='date' value='{date.today()}'><br>

    Pora dnia<br>
    <select name='time_slot'>
    <option value=''>--</option>
    <option value='RANO'>Rano</option>
    </select>

    <br><br>

    <button>Dodaj</button>

    </form>

    </div>
    """


# =====================
# AKTYWNE
# =====================

@app.route("/admin/active")
def admin_active():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM orders
    WHERE status!='WYKONANE'
    ORDER BY date
    """)

    orders = cur.fetchall()

    cur.close()
    conn.close()

    html = sidebar() + "<div style='display:inline-block;padding:20px'><h2>Aktywne</h2>"

    for o in orders:

        html += f"""
        <div style='background:{status_color(o["status"])};
        padding:10px;margin:10px;border-radius:6px'>

        <b>{o["client"]}</b><br>
        {o["address"]}<br>
        {o["date"]}<br>
        {o.get("time_slot","")}

        </div>
        """

    html += "</div>"

    return html


# =====================
# WYKONANE
# =====================

@app.route("/admin/done")
def admin_done():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM orders
    WHERE status='WYKONANE'
    ORDER BY date DESC
    """)

    orders = cur.fetchall()

    cur.close()
    conn.close()

    html = sidebar() + "<div style='display:inline-block;padding:20px'><h2>Wykonane</h2>"

    for o in orders:

        html += f"""
        <div style='padding:10px;margin:10px;background:#d4edda;border-radius:6px'>

        {o["date"]} | {o["client"]}

        </div>
        """

    html += "</div>"

    return html


# =====================
# TRASY
# =====================

@app.route("/admin/routes")
def admin_routes():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    SELECT DISTINCT date FROM orders
    ORDER BY date DESC
    """)

    routes = cur.fetchall()

    cur.close()
    conn.close()

    html = sidebar() + "<div style='display:inline-block;padding:20px'><h2>Trasówki</h2>"

    for r in routes:

        html += f"""
        <a href='/admin/route/{r["date"]}'>
        {r["date"]}
        </a><br>
        """

    html += "</div>"

    return html


# =====================
# RUN
# =====================

if __name__ == "__main__":
    app.run(debug=True)
