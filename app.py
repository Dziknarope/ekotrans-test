from flask import Flask, request, redirect, session
from datetime import date, datetime
import os
import psycopg2
import psycopg2.extras
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("Brak DATABASE_URL")

def db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

# =====================
# INICJALIZACJA BAZY
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
        status TEXT DEFAULT 'DO REALIZACJI',
        vehicle TEXT,
        quantity REAL,
        payment TEXT,
        amount REAL,
        notes TEXT,
        reason TEXT,
        time_slot TEXT DEFAULT 'Rano'
    );
    """)
    conn.commit()
    cur.close()
    conn.close()

def create_users():
    conn = db()
    cur = conn.cursor()
    users = [
        ("admin","Turcja123","admin")
    ]
    for u in users:
        cur.execute("INSERT INTO users (login,password,role) VALUES (%s,%s,%s) ON CONFLICT (login) DO NOTHING", u)
    conn.commit()
    cur.close()
    conn.close()

# Pojazdy na stałe w systemie
VEHICLES = ["LKR18456","LKR54VN","LKR61886","LKR40306"]

init_db()
create_users()

# =====================
# FUNKCJE POMOCNICZE
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

def sidebar():
    return """
    <div style='width:220px;background:#f0f0f0;color:#333;height:100vh;display:inline-block;padding:20px;font-family:Arial;vertical-align:top'>
        <h3 style='margin-bottom:20px'>ADMIN</h3>
        <div style='margin-bottom:10px; padding:8px; border-radius:6px; background:#e0e0e0;'>
            <a href='/admin/orders' style='color:#333; text-decoration:none; display:block'>➕ Zamówienia</a>
        </div>
        <div style='margin-bottom:10px; padding:8px; border-radius:6px; background:#e0e0e0;'>
            <a href='/admin/vehicles' style='color:#333; text-decoration:none; display:block'>🚛 Trasówki</a>
        </div>
        <div style='margin-bottom:10px; padding:8px; border-radius:6px; background:#e0e0e0;'>
            <a href='/admin/pdf' style='color:#333; text-decoration:none; display:block'>🖨 PDF</a>
        </div>
        <div style='margin-top:20px; padding:8px; border-radius:6px; background:#f8d7da;'>
            <a href='/logout' style='color:#721c24; text-decoration:none; display:block'>Wyloguj</a>
        </div>
    </div>
    """

# =====================
# LOGOWANIE
# =====================

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        conn=db()
        cur=conn.cursor()
        cur.execute("SELECT * FROM users WHERE login=%s AND password=%s",
                    (request.form["login"],request.form["password"]))
        user=cur.fetchone()
        cur.close(); conn.close()
        if user:
            session["user"]=user["login"]
            session["role"]=user["role"]
            return redirect("/admin/orders")
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
# ZAMÓWIENIA
# =====================

@app.route("/admin/orders", methods=["GET","POST"])
def admin_orders():
    if not is_admin(): 
        return redirect("/")

    conn = db()
    cur = conn.cursor()

    if request.method == "POST":
        try:
            order_id = request.form.get("id")
            cur.execute("""
                UPDATE orders
                SET status=%s
                WHERE id=%s
            """, (request.form.get("status","DO REALIZACJI"), order_id))
            conn.commit()
        except Exception as e:
            print("Błąd przy aktualizacji zamówienia:", e)

    cur.execute("""
        SELECT id, client, address, date, status,
               COALESCE(vehicle,'') AS vehicle,
               COALESCE(time_slot,'Rano') AS time_slot
        FROM orders
        ORDER BY date, id
    """)
    orders = cur.fetchall()
    cur.close()
    conn.close()

    html = sidebar() + "<div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'><h2>📋 Zamówienia</h2>"

    for o in orders:
        html += f"""
        <form method='post' style='background:{status_color(o['status'])};padding:10px;margin:10px;border-radius:6px'>
        <b>{o['client']}</b><br>
        {o['address']} | {o['date']}<br>
        Pojazd: {o['vehicle']}<br>
        Pora dnia: {o['time_slot']}<br>
        Status:
        <select name='status'>
            <option {'selected' if o['status']=="DO REALIZACJI" else ''}>DO REALIZACJI</option>
            <option {'selected' if o['status']=="W TOKU" else ''}>W TOKU</option>
            <option {'selected' if o['status']=="WYKONANE" else ''}>WYKONANE</option>
            <option {'selected' if o['status']=="NIE WYKONANE" else ''}>NIE WYKONANE</option>
        </select><br>
        <input type='hidden' name='id' value='{o['id']}'>
        <button>Zapisz</button>
        </form>
        """

    # Dodawanie nowego zamówienia
    html += """
    <h3>➕ Dodaj nowe zamówienie</h3>
    <form method='post' action='/admin/add_order'>
    Klient:<br><input name='client'><br>
    Adres:<br><input name='address'><br>
    Data:<br><input type='date' name='date' value='{0}'><br>
    Pora dnia:<br>
    <select name='time_slot'>
        <option>Rano</option>
        <option></option>
    </select><br><br>
    <button>Dodaj</button>
    </form>
    """.format(date.today())

    html += "</div>"
    return html

@app.route("/admin/add_order", methods=["POST"])
def add_order():
    if not is_admin(): 
        return redirect("/")
    client = request.form.get("client")
    address = request.form.get("address")
    order_date = request.form.get("date")
    time_slot = request.form.get("time_slot") or "Rano"

    conn = db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (client, address, date, status, time_slot)
        VALUES (%s,%s,%s,'DO REALIZACJI',%s)
    """, (client, address, order_date, time_slot))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/admin/orders")

# =====================
# TRASÓWKI / POJAZDY
# =====================

@app.route("/admin/vehicles")
def admin_vehicles():
    if not is_admin(): return redirect("/")
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders ORDER BY date, id")
    orders = cur.fetchall()
    cur.close()
    conn.close()

    html = sidebar() + "<div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'><h2>🚛 Trasówki / Pojazdy</h2>"
    for vehicle in VEHICLES:
        html += f"<h3>Pojazd {vehicle}</h3>"
        for o in orders:
            if o['vehicle'] == vehicle:
                html += f"{o['date']} | {o['client']} - {o['address']} ({o.get('time_slot','Rano')})<br>"
    html += "</div>"
    return html

# =====================
# PDF ZAMÓWIENIA
# =====================

@app.route("/admin/pdf")
def admin_pdf():
    if not is_admin(): return redirect("/")

    pdf_file = f"/tmp/orders_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    c = canvas.Canvas(pdf_file)
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders ORDER BY date, id")
    orders = cur.fetchall()
    cur.close(); conn.close()

    y = 800
    for o in orders:
        c.drawString(50, y, f"{o['date']} | {o['client']} | {o['address']} | {o.get('vehicle','')} | {o.get('time_slot','Rano')} | {o.get('status','DO REALIZACJI')}")
        y -= 20
        if y < 50:
            c.showPage()
            y = 800
    c.save()
    return f"PDF wygenerowany: {pdf_file}"

# =====================
# START
# =====================

if __name__ == "__main__":
    app.run(debug=True)
