from flask import Flask, request, redirect, session, send_file
from datetime import date
import os
import psycopg2
import psycopg2.extras
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE_URL = os.environ.get("DATABASE_URL")

def db():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# =====================
# INIT DB
# =====================

def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        login TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id SERIAL PRIMARY KEY,
        client TEXT,
        address TEXT,
        date DATE,
        status TEXT,
        driver TEXT,
        position INTEGER,
        time_slot TEXT
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

def create_admin():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO users(login,password,role)
    VALUES('admin','admin','admin')
    ON CONFLICT(login) DO NOTHING
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()
create_admin()

# =====================
# POMOCNICZE
# =====================

def is_admin():
    return session.get("role") == "admin"

def status_color(status):

    colors = {
        "DO REALIZACJI":"#cce5ff",
        "W TOKU":"#fff3cd",
        "NIE WYKONANE":"#f8d7da",
        "WYKONANE":"#d4edda"
    }

    return colors.get(status,"#ffffff")

# =====================
# SIDEBAR
# =====================

def sidebar():

    return """
    <div style='
        width:230px;
        background:#1f2a38;
        color:white;
        height:100vh;
        display:inline-block;
        padding:20px;
        font-family:Arial;
        vertical-align:top
    '>

    <h2>🚛 Panel</h2>

    <div style='margin-top:30px'>

    <div style='margin-bottom:10px'>
    <a href='/admin'
    style='display:block;padding:10px;background:#3498db;color:white;text-decoration:none;border-radius:6px'>
    ➕ Nowe zamówienie
    </a>
    </div>

    <div style='margin-bottom:10px'>
    <a href='/admin/active'
    style='display:block;padding:10px;background:#2ecc71;color:white;text-decoration:none;border-radius:6px'>
    📋 Zamówienia
    </a>
    </div>

    <div style='margin-bottom:10px'>
    <a href='/admin/routes'
    style='display:block;padding:10px;background:#9b59b6;color:white;text-decoration:none;border-radius:6px'>
    🚛 Trasówki
    </a>
    </div>

    <div style='margin-top:40px'>
    <a href='/logout'
    style='display:block;padding:10px;background:#e74c3c;color:white;text-decoration:none;border-radius:6px'>
    Wyloguj
    </a>
    </div>

    </div>
    </div>
    """

# =====================
# LOGIN
# =====================

@app.route("/", methods=["GET","POST"])
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
    Login:<br>
    <input name='login'><br><br>

    Hasło:<br>
    <input type='password' name='password'><br><br>

    <button>Zaloguj</button>
    </form>
    """

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# =====================
# NOWE ZAMÓWIENIE
# =====================

@app.route("/admin", methods=["GET","POST"])
def admin():

    if not is_admin():
        return redirect("/")

    if request.method == "POST":

        conn = db()
        cur = conn.cursor()

        time_slot = request.form.get("time_slot")

        if time_slot == "":
            time_slot = None

        cur.execute("""
        INSERT INTO orders(client,address,date,status,time_slot)
        VALUES(%s,%s,%s,'DO REALIZACJI',%s)
        """,
        (
            request.form["client"],
            request.form["address"],
            request.form["date"],
            time_slot
        ))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/admin")

    return sidebar() + f"""

    <div style='display:inline-block;padding:40px'>

    <h2>➕ Nowe zamówienie</h2>

    <form method='post'>

    Klient<br>
    <input name='client' required><br><br>

    Adres<br>
    <input name='address' required><br><br>

    Data<br>
    <input type='date' name='date' value='{date.today()}'><br><br>

    Pora dnia<br>

    <select name='time_slot'>
    <option value=''>brak</option>
    <option value='Rano'>Rano</option>
    </select>

    <br><br>

    <button>Dodaj</button>

    </form>

    </div>
    """

# =====================
# ZAMÓWIENIA
# =====================

@app.route("/admin/active", methods=["GET","POST"])
def active():

    if not is_admin():
        return redirect("/")

    conn = db()
    cur = conn.cursor()

    if request.method == "POST":

        cur.execute("""
        UPDATE orders
        SET driver=%s, position=%s, status=%s
        WHERE id=%s
        """,
        (
            request.form["driver"],
            request.form["position"],
            request.form["status"],
            request.form["id"]
        ))

        conn.commit()

    cur.execute("""
    SELECT * FROM orders
    ORDER BY date, driver NULLS FIRST, position NULLS FIRST
    """)

    orders = cur.fetchall()

    cur.close()
    conn.close()

    html = sidebar() + "<div style='display:inline-block;padding:30px'>"
    html += "<h2>Zamówienia</h2>"

    for o in orders:

        html += f"""

        <form method='post'
        style='background:{status_color(o["status"])};padding:10px;margin:10px;border-radius:6px'>

        <b>{o["client"]}</b><br>

        {o["address"]}<br>

        {o["date"]} | {o.get("time_slot","")}<br>

        Kierowca
        <input name='driver' value='{o.get("driver","")}'>

        Pozycja
        <input name='position' value='{o.get("position","")}' style='width:40px'>

        Status

        <select name='status'>
        <option {"selected" if o["status"]=="DO REALIZACJI" else ""}>DO REALIZACJI</option>
        <option {"selected" if o["status"]=="W TOKU" else ""}>W TOKU</option>
        <option {"selected" if o["status"]=="WYKONANE" else ""}>WYKONANE</option>
        <option {"selected" if o["status"]=="NIE WYKONANE" else ""}>NIE WYKONANE</option>
        </select>

        <input type='hidden' name='id' value='{o["id"]}'>

        <button>Zapisz</button>

        </form>
        """

    html += "</div>"

    return html

# =====================
# TRASÓWKI
# =====================

@app.route("/admin/routes")
def routes():

    if not is_admin():
        return redirect("/")

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    SELECT DISTINCT driver,date
    FROM orders
    WHERE driver IS NOT NULL
    ORDER BY date DESC
    """)

    routes = cur.fetchall()

    cur.close()
    conn.close()

    html = sidebar() + "<div style='display:inline-block;padding:40px'>"

    html += "<h2>🚛 Trasówki</h2>"

    for r in routes:

        html += f"""
        <div style='margin:10px'>
        {r["driver"]} | {r["date"]}
        <a href='/admin/pdf/{r["driver"]}/{r["date"]}'>PDF</a>
        </div>
        """

    html += "</div>"

    return html

# =====================
# PDF
# =====================

@app.route("/admin/pdf/<driver>/<rdate>")
def pdf(driver, rdate):

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM orders
    WHERE driver=%s AND date=%s
    ORDER BY position
    """,
    (driver,rdate))

    orders = cur.fetchall()

    cur.close()
    conn.close()

    filename = "route.pdf"

    c = canvas.Canvas(filename, pagesize=A4)

    y = 800

    c.setFont("Helvetica",12)

    c.drawString(50,y,f"Trasówka {driver} {rdate}")

    y -= 40

    for o in orders:

        text = f"{o['position']}  {o['client']}  {o['address']}"

        c.drawString(50,y,text)

        y -= 25

    c.save()

    return send_file(filename, as_attachment=True)

# =====================

if __name__ == "__main__":
    app.run()
