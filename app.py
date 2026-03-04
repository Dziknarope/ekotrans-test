from flask import Flask, request, redirect, session, jsonify
from datetime import date, datetime
import os
import psycopg2
import psycopg2.extras

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

def create_users():
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
# SIDEBAR ADMIN
# =====================

def sidebar():
    return """
    <div style='width:220px;background:#f0f0f0;height:100vh;display:inline-block;padding:20px;font-family:Arial;vertical-align:top'>
        <h3>ADMIN</h3>
        <a href='/admin'>➕ Nowe zlecenie</a><br><br>
        <a href='/admin/active'>📋 Aktywne</a><br><br>
        <a href='/admin/done'>✅ Wykonane</a><br><br>
        <a href='/admin/routes'>🚛 Trasówki</a><br><br>
        <a href='/logout' style='color:red'>Wyloguj</a>
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
            return redirect("/admin" if user["role"]=="admin" else "/driver")
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
# AUTOCOMPLETE KLIENTÓW
# =====================

@app.route("/clients")
def clients():
    if not session.get("role"):
        return jsonify([])

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT client FROM orders ORDER BY client")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([r["client"] for r in rows if r["client"]])

# =====================
# ADMIN – NOWE
# =====================

@app.route("/admin", methods=["GET","POST"])
def admin_new():
    if not is_admin(): return redirect("/")

    if request.method=="POST":
        conn=db(); cur=conn.cursor()
        cur.execute("""
        INSERT INTO orders (client,address,date,status,driver,position,time_slot)
        VALUES (%s,%s,%s,'DO REALIZACJI',%s,1,%s)
        """,(
            request.form["client"],
            request.form["address"],
            request.form["date"],
            request.form["driver"].lower(),
            request.form["time_slot"]
        ))
        conn.commit(); cur.close(); conn.close()
        return redirect("/admin")

    return sidebar()+f"""
    <div style='display:inline-block;padding:20px'>
    <h2>Nowe zlecenie</h2>
    <form method='post'>
    Klient:<br>
    <input name='client' list='clients'><br>
    <datalist id='clients'></datalist>
    Adres:<br><input name='address'><br>
    Data:<br><input type='date' name='date' value='{date.today()}'><br>
    Kierowca:<br><input name='driver'><br>
    Pora dnia:<br>
    <select name='time_slot'>
        <option>Rano</option>
        <option>Po 15:00</option>
    </select><br><br>
    <button>Dodaj</button>
    </form>
    </div>

    <script>
    fetch("/clients")
    .then(res => res.json())
    .then(data => {{
        let list = document.getElementById("clients");
        data.forEach(c => {{
            let option = document.createElement("option");
            option.value = c;
            list.appendChild(option);
        }});
    }});
    </script>
    """

# =====================
# ADMIN – RESZTA
# =====================

@app.route("/admin/active", methods=["GET","POST"])
def admin_active():
    if not is_admin(): return redirect("/")

    conn=db(); cur=conn.cursor()

    if request.method=="POST":
        cur.execute("""
        UPDATE orders SET status=%s, driver=%s, time_slot=%s
        WHERE id=%s
        """,(
            request.form["status"],
            request.form["driver"],
            request.form.get("time_slot",""),
            request.form["id"]
        ))
        conn.commit()

    cur.execute("SELECT * FROM orders WHERE status!='WYKONANE' ORDER BY date")
    orders=cur.fetchall()
    cur.close(); conn.close()

    html=sidebar()+"<div style='display:inline-block;padding:20px'><h2>Aktywne</h2>"
    for o in orders:
        html+=f"""
        <form method='post' style='background:{status_color(o["status"])};padding:10px;margin:10px'>
        <b>{o["client"]}</b><br>
        {o["address"]} | {o["date"]}<br>
        Kierowca:<input name='driver' value='{o["driver"]}'><br>
        Pora:<input name='time_slot' value='{o.get("time_slot","")}'><br>
        <select name='status'>
            <option {'selected' if o["status"]=="DO REALIZACJI" else ""}>DO REALIZACJI</option>
            <option {'selected' if o["status"]=="W TOKU" else ""}>W TOKU</option>
            <option {'selected' if o["status"]=="NIE WYKONANE" else ""}>NIE WYKONANE</option>
            <option {'selected' if o["status"]=="WYKONANE" else ""}>WYKONANE</option>
        </select>
        <input type='hidden' name='id' value='{o["id"]}'>
        <button>Zapisz</button>
        </form>
        """
    return html+"</div>"

@app.route("/admin/done")
def admin_done():
    if not is_admin(): return redirect("/")
    conn=db(); cur=conn.cursor()
    cur.execute("SELECT * FROM orders WHERE status='WYKONANE' ORDER BY date DESC")
    orders=cur.fetchall()
    cur.close(); conn.close()

    html=sidebar()+"<div style='display:inline-block;padding:20px'><h2>Wykonane</h2>"
    for o in orders:
        html+=f"{o['date']} | {o['driver']} | {o['client']}<br>"
    return html+"</div>"

@app.route("/admin/routes")
def admin_routes():
    if not is_admin(): return redirect("/")
    conn=db(); cur=conn.cursor()
    cur.execute("SELECT DISTINCT driver,date FROM orders ORDER BY date DESC")
    routes=cur.fetchall()
    cur.close(); conn.close()

    html=sidebar()+"<div style='display:inline-block;padding:20px'><h2>Trasy</h2>"
    for r in routes:
        html+=f"<a href='/admin/route/{r['driver']}/{r['date']}'>{r['driver']} | {r['date']}</a><br>"
    return html+"</div>"

@app.route("/admin/route/<driver>/<rdate>")
def admin_route_detail(driver,rdate):
    if not is_admin(): return redirect("/")
    conn=db(); cur=conn.cursor()
    cur.execute("SELECT * FROM orders WHERE driver=%s AND date=%s",(driver,rdate))
    orders=cur.fetchall()
    cur.close(); conn.close()

    html=sidebar()+f"<div style='display:inline-block;padding:20px'><h2>{driver} | {rdate}</h2>"
    for o in orders:
        html+=f"{o['client']} - {o['address']}<br>"
    return html+"</div>"

# =====================
# PANEL KIEROWCY
# =====================

@app.route("/driver", methods=["GET","POST"])
def driver_panel():
    if not is_driver(): return redirect("/")
    user=session["user"]
    today=date.today()

    conn=db(); cur=conn.cursor()

    if request.method=="POST" and "new_order" in request.form:
        cur.execute("""
        INSERT INTO orders (client,address,date,status,driver,position,time_slot)
        VALUES (%s,%s,%s,'DO REALIZACJI',%s,1,%s)
        """,(
            request.form["client"],
            request.form["address"],
            request.form["date"],
            user,
            request.form["time_slot"]
        ))
        conn.commit()

    cur.execute("SELECT * FROM orders WHERE driver=%s AND date=%s",(user,today))
    orders=cur.fetchall()
    cur.close(); conn.close()

    html=f"<h2>Panel kierowcy | {user} | {today}</h2>"

    for o in orders:
        html+=f"{o['client']} - {o['address']} ({o.get('time_slot','')})<br>"

    html+=f"""
    <h3>Dodaj zlecenie</h3>
    <form method='post'>
    Klient:<br>
    <input name='client' list='clients2'><br>
    <datalist id='clients2'></datalist>
    Adres:<br><input name='address'><br>
    Data:<br><input type='date' name='date' value='{today}'><br>
    Pora dnia:<br>
    <select name='time_slot'>
        <option>Rano</option>
        <option>Po 15:00</option>
    </select><br><br>
    <button name='new_order'>Dodaj</button>
    </form>

    <script>
    fetch("/clients")
    .then(res => res.json())
    .then(data => {{
        let list = document.getElementById("clients2");
        data.forEach(c => {{
            let option = document.createElement("option");
            option.value = c;
            list.appendChild(option);
        }});
    }});
    </script>
    """

    html+="<br><a href='/logout'>Wyloguj</a>"
    return html

# =====================
# START
# =====================

if __name__ == "__main__":
    app.run(debug=True)
