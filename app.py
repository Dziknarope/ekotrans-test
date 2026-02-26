from flask import Flask, request, redirect, session
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
        cur.execute("INSERT INTO users (login,password,role) VALUES (%s,%s,%s) ON CONFLICT (login) DO NOTHING", u)
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
# NOWY SIDEBAR – jasny z ramkami
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
# RESZTA KODU – BEZ ZMIAN
# =====================

@app.route("/admin", methods=["GET","POST"])
def admin_new():
    if not is_admin(): return redirect("/")

    if request.method=="POST":
        conn=db(); cur=conn.cursor()
        cur.execute("""
        INSERT INTO orders (client,address,date,status,driver,position)
        VALUES (%s,%s,%s,'DO REALIZACJI',%s,%s)
        """,(
            request.form["client"],
            request.form["address"],
            request.form["date"],
            request.form["driver"].lower(),
            request.form["position"]
        ))
        conn.commit(); cur.close(); conn.close()
        return redirect("/admin")

    return sidebar()+"""
    <div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'>
    <h2>➕ Dodaj nowe zlecenie</h2>
    <form method='post'>
    Klient:<br><input name='client'><br>
    Adres:<br><input name='address'><br>
    Data:<br><input type='date' name='date' value='{0}'><br>
    Kierowca:<br><input name='driver'><br>
    Kolejność:<br><input name='position' value='1'><br><br>
    <button>Dodaj</button>
    </form>
    </div>
    """.format(date.today())

# =====================
# ADMIN – AKTYWNE
# =====================

@app.route("/admin/active", methods=["GET","POST"])
def admin_active():
    if not is_admin(): return redirect("/")

    conn=db(); cur=conn.cursor()

    if request.method=="POST":
        cur.execute("""
        UPDATE orders SET status=%s, driver=%s, position=%s
        WHERE id=%s
        """,(
            request.form["status"],
            request.form["driver"],
            request.form["position"],
            request.form["id"]
        ))
        conn.commit()

    cur.execute("SELECT * FROM orders WHERE status!='WYKONANE' ORDER BY date, driver, position")
    orders=cur.fetchall()
    cur.close(); conn.close()

    html=sidebar()+"<div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'><h2>📋 Aktywne</h2>"
    for o in orders:
        html+=f"""
        <form method='post' style='background:{status_color(o['status'])};padding:10px;margin:10px;border-radius:6px'>
        <b>{o['client']}</b><br>
        {o['address']} | {o['date']}<br>
        Kierowca:<input name='driver' value='{o['driver']}'>
        Kolejność:<input name='position' value='{o['position']}'><br>
        <select name='status'>
            <option {'selected' if o['status']=="DO REALIZACJI" else ''}>DO REALIZACJI</option>
            <option {'selected' if o['status']=="W TOKU" else ''}>W TOKU</option>
            <option {'selected' if o['status']=="NIE WYKONANE" else ''}>NIE WYKONANE</option>
            <option {'selected' if o['status']=="WYKONANE" else ''}>WYKONANE</option>
        </select>
        <input type='hidden' name='id' value='{o['id']}'>
        <button>Zapisz</button>
        </form>
        """
    return html+"</div>"

# =====================
# RESZTA PANELI I KIEROWCY – BEZ ZMIAN
# =====================

@app.route("/admin/done")
def admin_done():
    if not is_admin(): return redirect("/")
    conn=db(); cur=conn.cursor()
    cur.execute("SELECT * FROM orders WHERE status='WYKONANE' ORDER BY date DESC")
    orders=cur.fetchall()
    cur.close(); conn.close()

    html=sidebar()+"<div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'><h2>✅ Wykonane</h2>"
    for o in orders:
        html+=f"<div style='background:{status_color(o['status'])};padding:10px;margin:10px'>{o['date']} | {o['driver']} | {o['client']}</div>"
    return html+"</div>"

@app.route("/admin/routes")
def admin_routes():
    if not is_admin(): return redirect("/")
    conn=db(); cur=conn.cursor()
    cur.execute("SELECT DISTINCT driver,date FROM orders ORDER BY date DESC")
    routes=cur.fetchall()
    cur.close(); conn.close()

    html=sidebar()+"<div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'><h2>🚛 Trasówki</h2>"
    for r in routes:
        html+=f"<a href='/admin/route/{r['driver']}/{r['date']}'>{r['driver']} | {r['date']}</a><br>"
    return html+"</div>"

@app.route("/admin/route/<driver>/<rdate>")
def admin_route_detail(driver,rdate):
    if not is_admin(): return redirect("/")
    conn=db(); cur=conn.cursor()
    cur.execute("SELECT * FROM orders WHERE driver=%s AND date=%s ORDER BY position",(driver,rdate))
    orders=cur.fetchall()
    cur.execute("SELECT * FROM fuel_logs WHERE driver=%s AND date=%s",(driver,rdate))
    fuels=cur.fetchall()
    cur.execute("SELECT * FROM driver_days WHERE driver=%s AND date=%s",(driver,rdate))
    day=cur.fetchone()
    cur.close(); conn.close()

    html=sidebar()+f"<div style='display:inline-block; vertical-align:top; margin-left:20px; padding:20px'><h2>Trasa {driver} | {rdate}</h2>"

    if day and day["closed"]:
        html+="<b style='color:red'>Dzień zamknięty</b><br>"
        html+=f"<a href='/admin/unlock/{driver}/{rdate}'>🔓 Odblokuj dzień</a><br><br>"

    for o in orders:
        html+=f"{o['position']}. {o['client']} - {o['address']}<br>"

    html+="<h3>⛽ Tankowania</h3>"
    for f in fuels:
        html+=f"Licznik: {f['mileage']} | Litry: {f['liters']}<br>"

    return html+"</div>"

@app.route("/admin/unlock/<driver>/<rdate>")
def unlock_day(driver,rdate):
    conn=db(); cur=conn.cursor()
    cur.execute("UPDATE driver_days SET closed=FALSE WHERE driver=%s AND date=%s",(driver,rdate))
    conn.commit(); cur.close(); conn.close()
    return redirect(f"/admin/route/{driver}/{rdate}")

@app.route("/driver", methods=["GET","POST"])
def driver_panel():
    if not is_driver(): return redirect("/")
    user=session["user"]
    today=date.today()

    conn=db(); cur=conn.cursor()

    cur.execute("SELECT * FROM driver_days WHERE driver=%s AND date=%s",(user,today))
    day=cur.fetchone()

    if request.method=="POST" and "close_day" in request.form:
        if not day:
            cur.execute("INSERT INTO driver_days (driver,date,closed,closed_at) VALUES (%s,%s,TRUE,%s)",
                        (user,today,datetime.now()))
        else:
            cur.execute("UPDATE driver_days SET closed=TRUE, closed_at=%s WHERE driver=%s AND date=%s",
                        (datetime.now(),user,today))
        conn.commit()

    if request.method=="POST" and "fuel" in request.form:
        if not day or not day["closed"]:
            cur.execute("INSERT INTO fuel_logs (driver,date,mileage,liters) VALUES (%s,%s,%s,%s)",
                        (user,today,request.form["mileage"],request.form["liters"]))
            conn.commit()

    if request.method=="POST" and "update_order" in request.form:
        if not day or not day["closed"]:
            cur.execute("""
            UPDATE orders SET status=%s, quantity=%s, amount=%s, notes=%s
            WHERE id=%s AND driver=%s
            """,(
                request.form["status"],
                request.form["quantity"],
                request.form["amount"],
                request.form["notes"],
                request.form["id"],
                user
            ))
            conn.commit()

    cur.execute("SELECT * FROM orders WHERE driver=%s AND date=%s ORDER BY position",(user,today))
    orders=cur.fetchall()
    cur.close(); conn.close()

    html=f"<h2>🚛 Panel dzienny | {user.capitalize()} | {today}</h2>"
    if day and day["closed"]:
        html+="<b style='color:red'>DZIEŃ ZAMKNIĘTY</b><br>"

    for o in orders:
        html+=f"""
        <form method='post' style='background:{status_color(o['status'])};padding:10px;margin:10px;border-radius:6px'>
        <b>{o['client']}</b><br>
        {o['address']}<br>
        <select name='status'>
            <option {'selected' if o['status']=="W TOKU" else ''}>W TOKU</option>
            <option {'selected' if o['status']=="WYKONANE" else ''}>WYKONANE</option>
            <option {'selected' if o['status']=="NIE WYKONANE" else ''}>NIE WYKONANE</option>
        </select><br>
        Ilość: <input name='quantity' value='{o['quantity'] or ""}'><br>
        Kwota: <input name='amount' value='{o['amount'] or ""}'><br>
        Notatki: <input name='notes' value='{o['notes'] or ""}'><br>
        <input type='hidden' name='id' value='{o['id']}'>
        <button name='update_order'>Zapisz</button>
        </form>
        """

    if not (day and day["closed"]):
        html+="""
        <form method='post'>
        <button name='close_day'>🔵 Zakończ dzień</button>
        </form>
        <h3>⛽ Tankowanie</h3>
        <form method='post'>
        Stan licznika:<br><input name='mileage'><br>
        Litry:<br><input name='liters'><br>
        <button name='fuel'>Zapisz tankowanie</button>
        </form>
        """

    html+="<br><a href='/logout'>Wyloguj</a>"
    return html

if __name__ == "__main__":
    app.run()
