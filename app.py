from flask import Flask, request, redirect, session, send_file
from datetime import date, datetime
import os
import psycopg2
import psycopg2.extras
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("Brak DATABASE_URL")

# =====================
# BAZA DANYCH
# =====================

def db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

def init_db():
    conn = db()
    cur = conn.cursor()

    # tabela użytkowników (admin)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        login TEXT UNIQUE,
        password TEXT,
        role TEXT
    );
    """)

    # tabela zamówień
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        client TEXT,
        address TEXT,
        date DATE,
        status TEXT,
        vehicle TEXT,
        time_slot TEXT,
        quantity REAL,
        amount REAL,
        notes TEXT
    );
    """)

    # tabela pojazdów
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE
    );
    """)

    conn.commit()
    cur.close()
    conn.close()

def create_default_users():
    conn = db()
    cur = conn.cursor()
    users = [
        ("admin","Turcja123","admin"),
    ]
    for u in users:
        cur.execute("INSERT INTO users (login,password,role) VALUES (%s,%s,%s) ON CONFLICT (login) DO NOTHING", u)
    conn.commit()
    cur.close()
    conn.close()

def create_default_vehicles():
    conn = db()
    cur = conn.cursor()
    vehicles = [
        ("LKR18456",),
        ("LKR54VN",),
        ("LKR61886",),
        ("LKR40306",),
        ("LKR99999",)
    ]
    for v in vehicles:
        cur.execute("INSERT INTO vehicles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", v)
    conn.commit()
    cur.close()
    conn.close()

# Inicjalizacja bazy
init_db()
create_default_users()
create_default_vehicles()

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
            <a href='/admin' style='color:#333; text-decoration:none; display:block'>➕ Nowe zamówienie</a>
        </div>
        <div style='margin-bottom:10px; padding:8px; border-radius:6px; background:#e0e0e0;'>
            <a href='/admin/orders' style='color:#333; text-decoration:none; display:block'>📋 Zamówienia</a>
        </div>
        <div style='margin-bottom:10px; padding:8px; border-radius:6px; background:#e0e0e0;'>
            <a href='/admin/routes' style='color:#333; text-decoration:none; display:block'>🚚 Trasówki</a>
        </div>
        <div style='margin-bottom:10px; padding:8px; border-radius:6px; background:#e0e0e0;'>
            <a href='/admin/pdf' style='color:#333; text-decoration:none; display:block'>🧾 PDF tras</a>
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
            return redirect("/admin")
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
# NOWE ZAMÓWIENIE
# =====================

@app.route("/admin", methods=["GET","POST"])
def admin_new_order():
    if not is_admin(): return redirect("/")

    if request.method=="POST":
        client = request.form.get("client","").strip()
        address = request.form.get("address","").strip()
        order_date = request.form.get("date", str(date.today()))
        time_slot = request.form.get("time_slot","")

        conn=db()
        cur=conn.cursor()
        cur.execute("""
        INSERT INTO orders (client,address,date,status,time_slot)
        VALUES (%s,%s,%s,'DO REALIZACJI',%s)
        """,(client,address,order_date,time_slot))
        conn.commit()
        cur.close(); conn.close()
        return redirect("/admin/orders")

    # wybór pory dnia
    time_options = ["","Rano"]
    options_html = "".join([f"<option value='{t}'>{t}</option>" for t in time_options])

    return sidebar()+f"""
    <div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'>
    <h2>➕ Dodaj nowe zamówienie</h2>
    <form method='post'>
    Klient:<br><input name='client'><br>
    Adres:<br><input name='address'><br>
    Data:<br><input type='date' name='date' value='{date.today()}'><br>
    Pora dnia:<br>
    <select name='time_slot'>{options_html}</select><br><br>
    <button>Dodaj</button>
    </form>
    </div>
    """

# =====================
# LISTA ZAMÓWIEŃ
# =====================

@app.route("/admin/orders", methods=["GET","POST"])
def admin_orders():
    if not is_admin(): return redirect("/")

    conn=db(); cur=conn.cursor()
    # pobranie pojazdów
    cur.execute("SELECT name FROM vehicles ORDER BY name")
    vehicles = [v["name"] for v in cur.fetchall()]

    if request.method=="POST":
        order_id = request.form.get("id")
        status = request.form.get("status")
        vehicle = request.form.get("vehicle")
        quantity = request.form.get("quantity") or None
        amount = request.form.get("amount") or None
        notes = request.form.get("notes") or ""
        cur.execute("""
        UPDATE orders SET status=%s, vehicle=%s, quantity=%s, amount=%s, notes=%s
        WHERE id=%s
        """,(status,vehicle,quantity,amount,notes,order_id))
        conn.commit()

    cur.execute("SELECT * FROM orders ORDER BY date DESC")
    orders = cur.fetchall()
    cur.close(); conn.close()

    html = sidebar()+"<div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'><h2>📋 Zamówienia</h2>"
    for o in orders:
        vehicle_options = "".join([f"<option value='{v}' {'selected' if v==o['vehicle'] else ''}>{v}</option>" for v in vehicles])
        html+=f"""
        <form method='post' style='background:{status_color(o['status'])};padding:10px;margin:10px;border-radius:6px'>
        <b>{o['client']}</b><br>
        {o['address']}<br>
        Data: {o['date']} | Pora: {o.get('time_slot','')}<br>
        Pojazd: <select name='vehicle'>{vehicle_options}</select><br>
        Status: 
        <select name='status'>
            <option {'selected' if o['status']=="DO REALIZACJI" else ''}>DO REALIZACJI</option>
            <option {'selected' if o['status']=="W TOKU" else ''}>W TOKU</option>
            <option {'selected' if o['status']=="WYKONANE" else ''}>WYKONANE</option>
            <option {'selected' if o['status']=="NIE WYKONANE" else ''}>NIE WYKONANE</option>
        </select><br>
        Ilość: <input name='quantity' value='{o['quantity'] or ""}'><br>
        Kwota: <input name='amount' value='{o['amount'] or ""}'><br>
        Notatki: <input name='notes' value='{o['notes'] or ""}'><br>
        <input type='hidden' name='id' value='{o['id']}'>
        <button>Zapisz</button>
        </form>
        """
    html += "</div>"
    return html

# =====================
# TRASÓWKI
# =====================

@app.route("/admin/routes")
def admin_routes():
    if not is_admin(): return redirect("/")
    conn=db(); cur=conn.cursor()
    cur.execute("SELECT DISTINCT vehicle, date FROM orders WHERE vehicle IS NOT NULL ORDER BY date DESC")
    routes = cur.fetchall()
    cur.close(); conn.close()

    html = sidebar()+"<div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'><h2>🚚 Trasówki</h2>"
    for r in routes:
        html+=f"<a href='/admin/route/{r['vehicle']}/{r['date']}'>{r['vehicle']} | {r['date']}</a><br>"
    html += "</div>"
    return html

@app.route("/admin/route/<vehicle>/<rdate>")
def admin_route_detail(vehicle,rdate):
    if not is_admin(): return redirect("/")
    conn=db(); cur=conn.cursor()
    cur.execute("SELECT * FROM orders WHERE vehicle=%s AND date=%s ORDER BY id",(vehicle,rdate))
    orders = cur.fetchall()
    cur.close(); conn.close()

    html = sidebar()+f"<div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'><h2>Trasa {vehicle} | {rdate}</h2>"
    for i,o in enumerate(orders,1):
        html+=f"{i}. {o['client']} - {o['address']} (Pora: {o.get('time_slot','')})<br>"
    html += "</div>"
    return html

# =====================
# GENEROWANIE PDF
# =====================

@app.route("/admin/pdf")
def generate_pdf():
    if not is_admin(): return redirect("/")

    conn=db(); cur=conn.cursor()
    cur.execute("SELECT DISTINCT vehicle, date FROM orders WHERE vehicle IS NOT NULL ORDER BY date DESC")
    routes = cur.fetchall()
    cur.close(); conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    for r in routes:
        conn=db(); cur=conn.cursor()
        cur.execute("SELECT * FROM orders WHERE vehicle=%s AND date=%s ORDER BY id",(r['vehicle'],r['date']))
        orders = cur.fetchall()
        cur.close(); conn.close()
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, f"TRASA | Pojazd: {r['vehicle']} | Data: {r['date']}")
        y -= 20
        c.setFont("Helvetica", 12)
        for i,o in enumerate(orders,1):
            c.drawString(60, y, f"{i}. {o['client']} - {o['address']} (Pora: {o.get('time_slot','')})")
            y -= 18
            if y < 50:
                c.showPage()
                y = height - 50
        y -= 20
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="trasowki.pdf", mimetype='application/pdf')

# =====================
# URUCHOMIENIE
# =====================

if __name__=="__main__":
    app.run(debug=True)
