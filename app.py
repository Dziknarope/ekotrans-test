from flask import Flask, request, redirect, session, send_file
from datetime import date, datetime
import os
import psycopg2
import psycopg2.extras
from io import BytesIO
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("Brak DATABASE_URL")

def db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

# =====================
# INIT BAZY
# =====================

def init_db():
    conn = db()
    cur = conn.cursor()

    # users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        login TEXT UNIQUE,
        password TEXT,
        role TEXT
    );
    """)

    # vehicles
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE
    );
    """)

    # orders
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        client TEXT,
        address TEXT,
        date DATE,
        status TEXT,
        vehicle TEXT,
        quantity REAL,
        payment TEXT,
        amount REAL,
        notes TEXT,
        reason TEXT,
        time_slot TEXT
    );
    """)

    conn.commit()
    cur.close()
    conn.close()

def create_users_vehicles():
    conn = db()
    cur = conn.cursor()

    # users
    users = [
        ("admin","Turcja123","admin")
    ]
    for u in users:
        cur.execute("INSERT INTO users (login,password,role) VALUES (%s,%s,%s) ON CONFLICT (login) DO NOTHING", u)

    # vehicles
    vehicles = ["LKR18456","LKR54VN","LKR61886","LKR40306"]
    for v in vehicles:
        cur.execute("INSERT INTO vehicles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (v,))

    conn.commit()
    cur.close()
    conn.close()

init_db()
create_users_vehicles()

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

def sidebar():
    return """
    <div style='width:220px;background:#f0f0f0;color:#333;height:100vh;display:inline-block;padding:20px;font-family:Arial;vertical-align:top'>
        <h3 style='margin-bottom:20px'>ADMIN</h3>
        <div style='margin-bottom:10px; padding:8px; border-radius:6px; background:#e0e0e0;'>
            <a href='/admin/orders' style='color:#333; text-decoration:none; display:block'>📋 Zamówienia</a>
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
    if not is_admin(): return redirect("/")

    conn=db()
    cur=conn.cursor()

    # Dodawanie zamówienia
    if request.method=="POST" and "new_order" in request.form:
        ts = request.form.get("time_slot") or "Rano"
        cur.execute("""
        INSERT INTO orders (client,address,date,status,time_slot)
        VALUES (%s,%s,%s,'DO REALIZACJI',%s)
        """,(
            request.form["client"],
            request.form["address"],
            request.form["date"],
            ts
        ))
        conn.commit()

    # Pobranie wszystkich zamówień
    cur.execute("SELECT * FROM orders ORDER BY date DESC")
    orders=cur.fetchall()
    # zabezpieczenie None
    for o in orders:
        if o['vehicle'] is None:
            o['vehicle'] = ""
        if o['time_slot'] is None:
            o['time_slot'] = ""
    cur.execute("SELECT name FROM vehicles")
    vehicles=[v['name'] for v in cur.fetchall()]
    cur.close(); conn.close()

    # HTML
    html=sidebar()+"<div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'>"
    html+="<h2>📋 Zamówienia</h2>"

    for o in orders:
        html+=f"""
        <form method='post' style='background:{status_color(o['status'])};padding:10px;margin:10px;border-radius:6px'>
        <b>{o['client']}</b><br>
        {o['address']} | {o['date']}<br>
        Pora dnia: {o.get('time_slot','')}<br>
        Pojazd: <select disabled>{''.join([f"<option value='{v}' {'selected' if v==o['vehicle'] else ''}>{v}</option>" for v in vehicles])}</select><br>
        Status: {o['status']}<br>
        <input type='hidden' name='id' value='{o['id']}'>
        </form>
        """

    # Dodawanie nowego zamówienia
    time_options=["Rano",""]
    html+=f"""
    <h3>➕ Dodaj nowe zamówienie</h3>
    <form method='post'>
    Klient:<br><input name='client'><br>
    Adres:<br><input name='address'><br>
    Data:<br><input type='date' name='date' value='{date.today()}'><br>
    Pora dnia:<br>
    <select name='time_slot'>
        {''.join([f"<option value='{t}'>{t}</option>" for t in time_options])}
    </select><br><br>
    <button name='new_order'>Dodaj</button>
    </form>
    """
    html+="</div>"
    return html

# =====================
# TRASÓWKI
# =====================

@app.route("/admin/routes")
def admin_routes():
    if not is_admin(): return redirect("/")

    conn=db()
    cur=conn.cursor()
    cur.execute("SELECT DISTINCT vehicle, date FROM orders WHERE vehicle IS NOT NULL ORDER BY date DESC")
    routes=cur.fetchall()
    cur.close(); conn.close()

    html=sidebar()+"<div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'>"
    html+="<h2>🚛 Trasówki</h2>"

    for r in routes:
        html+=f"<a href='/admin/route/{r['vehicle']}/{r['date']}'>{r['vehicle']} | {r['date']}</a><br>"

    html+="</div>"
    return html

@app.route("/admin/route/<vehicle>/<rdate>")
def admin_route_detail(vehicle,rdate):
    if not is_admin(): return redirect("/")

    conn=db()
    cur=conn.cursor()
    cur.execute("SELECT * FROM orders WHERE vehicle=%s AND date=%s ORDER BY id",(vehicle,rdate))
    orders=cur.fetchall()
    for o in orders:
        if o.get('time_slot') is None:
            o['time_slot']=""
    cur.close(); conn.close()

    html=sidebar()+"<div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'>"
    html+=f"<h2>Trasa pojazdu {vehicle} | {rdate}</h2>"
    for i,o in enumerate(orders,1):
        html+=f"{i}. {o['client']} - {o['address']} (Pora: {o.get('time_slot','')})<br>"
    html+="<br><a href='/admin/routes'>← Powrót</a>"
    html+="</div>"
    return html

# =====================
# PDF TRASY
# =====================

@app.route("/admin/route/<vehicle>/<rdate>/pdf")
def route_pdf(vehicle,rdate):
    if not is_admin(): return redirect("/")

    conn=db()
    cur=conn.cursor()
    cur.execute("SELECT * FROM orders WHERE vehicle=%s AND date=%s ORDER BY id",(vehicle,rdate))
    orders=cur.fetchall()
    for o in orders:
        if o.get('time_slot') is None:
            o['time_slot']=""
    cur.close(); conn.close()

    buffer=BytesIO()
    c=canvas.Canvas(buffer)
    c.setFont("Helvetica",12)
    y=800
    c.drawString(50,y,f"Trasa pojazdu {vehicle} | {rdate}")
    y-=30
    for i,o in enumerate(orders,1):
        c.drawString(60,y,f"{i}. {o['client']} - {o['address']} (Pora: {o['time_slot']})")
        y-=20
        if y<50:
            c.showPage()
            y=800
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"Trasa_{vehicle}_{rdate}.pdf", mimetype="application/pdf")

# =====================
# RUN
# =====================

if __name__=="__main__":
    app.run(debug=True)
