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
        start_time TIMESTAMP,
        end_time TIMESTAMP
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

def sidebar():
    return """
    <div style='width:220px;background:#444;color:white;height:100vh;float:left;padding:20px;box-sizing:border-box'>
        <h3>ADMIN</h3>
        <div style='margin-bottom:10px;padding:5px;border:1px solid #888;border-radius:4px'><a href='/admin' style='color:white;text-decoration:none'>➕ Nowe zlecenie</a></div>
        <div style='margin-bottom:10px;padding:5px;border:1px solid #888;border-radius:4px'><a href='/admin/active' style='color:white;text-decoration:none'>📋 Aktywne</a></div>
        <div style='margin-bottom:10px;padding:5px;border:1px solid #888;border-radius:4px'><a href='/admin/done' style='color:white;text-decoration:none'>✅ Wykonane</a></div>
        <div style='margin-bottom:10px;padding:5px;border:1px solid #888;border-radius:4px'><a href='/admin/routes' style='color:white;text-decoration:none'>🚛 Trasówki</a></div>
        <div style='margin-top:20px'><a href='/logout' style='color:red;text-decoration:none'>Wyloguj</a></div>
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
# ADMIN – NOWE ZLECENIE
# =====================

@app.route("/admin", methods=["GET","POST"])
def admin_new():
    if not is_admin(): return redirect("/")

    conn=db()
    cur=conn.cursor()
    cur.execute("SELECT login FROM users WHERE role='driver'")
    drivers=[d['login'] for d in cur.fetchall()]
    cur.close(); conn.close()

    if request.method=="POST":
        conn=db(); cur=conn.cursor()
        cur.execute("""
        INSERT INTO orders (client,address,date,status,driver,position,time_slot)
        VALUES (%s,%s,%s,'DO REALIZACJI',%s,%s,%s)
        """,(
            request.form["client"],
            request.form["address"],
            request.form["date"],
            request.form["driver"].lower(),
            1,
            request.form["time_slot"]
        ))
        conn.commit(); cur.close(); conn.close()
        return redirect("/admin")

    options = "".join([f"<option value='{d}'>{d}</option>" for d in drivers])
    return sidebar()+f"""
    <div style='margin-left:250px;padding:20px'>
    <h2>➕ Dodaj nowe zlecenie</h2>
    <form method='post'>
    Klient:<br><input name='client'><br>
    Adres:<br><input name='address'><br>
    Data:<br><input type='date' name='date' value='{date.today()}'><br>
    Kierowca:<br><select name='driver'>{options}</select><br>
    Pora dnia:<br>
    <select name='time_slot'>
        <option value='Rano'>Rano</option>
        <option value='Po 15:00'>Po 15:00</option>
    </select><br><br>
    <button>Dodaj</button>
    </form>
    </div>
    """

# =====================
# ADMIN – AKTYWNE
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
            request.form["time_slot"],
            request.form["id"]
        ))
        conn.commit()

    cur.execute("SELECT * FROM orders WHERE status!='WYKONANE' ORDER BY date, driver")
    orders=cur.fetchall()
    cur.close(); conn.close()

    html=sidebar()+"<div style='margin-left:250px;padding:20px'><h2>📋 Aktywne</h2>"
    for o in orders:
        html+=f"""
        <form method='post' style='background:{status_color(o['status'])};padding:10px;margin:10px;border-radius:6px'>
        <b>{o['client']}</b><br>
        {o['address']} | {o['date']} | {o['time_slot']}<br>
        Kierowca:<input name='driver' value='{o['driver']}'><br>
        Pora dnia:<input name='time_slot' value='{o['time_slot']}'><br>
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
# ADMIN – WYKONANE
# =====================

@app.route("/admin/done")
def admin_done():
    if not is_admin(): return redirect("/")
    conn=db(); cur=conn.cursor()
    cur.execute("SELECT * FROM orders WHERE status='WYKONANE' ORDER BY date DESC")
    orders=cur.fetchall()
    cur.close(); conn.close()

    html=sidebar()+"<div style='margin-left:250px;padding:20px'><h2>✅ Wykonane</h2>"
    for o in orders:
        html+=f"<div style='background:{status_color(o['status'])};padding:10px;margin:10px'>"
        html+=f"{o['date']} | {o['driver']} | {o['client']} | {o['address']} | Ilość: {o['quantity'] or ''} | Kwota: {o['amount'] or ''}</div>"
    return html+"</div>"

# =====================
# ADMIN – TRASÓWKI
# =====================

@app.route("/admin/routes", methods=["GET","POST"])
def admin_routes():
    if not is_admin(): return redirect("/")
    conn=db(); cur=conn.cursor()
    cur.execute("SELECT DISTINCT driver FROM orders ORDER BY driver")
    drivers=cur.fetchall()
    cur.close(); conn.close()

    html=sidebar()+"<div style='margin-left:250px;padding:20px'><h2>🚛 Trasówki</h2>"
    html+="<form method='get' action='/admin/route_detail'>"
    html+="Wybierz kierowcę:<br><select name='driver'>"
    html+="".join([f"<option value='{d['login']}'>{d['login']}</option>" for d in drivers])
    html+="</select><br>Data:<br><input type='date' name='date' value='"+str(date.today())+"'><br><button>Pokaż trasę</button></form>"
    html+="</div>"
    return html

@app.route("/admin/route_detail")
def admin_route_detail():
    if not is_admin(): return redirect("/")
    driver=request.args.get("driver")
    rdate=request.args.get("date")

    conn=db(); cur=conn.cursor()
    cur.execute("SELECT * FROM orders WHERE driver=%s AND date=%s ORDER BY time_slot",(driver,rdate))
    orders=cur.fetchall()
    cur.execute("SELECT * FROM fuel_logs WHERE driver=%s AND date=%s",(driver,rdate))
    fuels=cur.fetchall()
    cur.execute("SELECT * FROM driver_days WHERE driver=%s AND date=%s",(driver,rdate))
    day=cur.fetchone()
    cur.close(); conn.close()

    html=sidebar()+f"<div style='margin-left:250px;padding:20px'><h2>Trasa {driver} | {rdate}</h2>"
    if day and day["end_time"]:
        html+="<b style='color:red'>Dzień zamknięty</b><br>"

    for o in orders:
        html+=f"{o['time_slot']} - {o['client']} | {o['address']}<br>"

    html+="<h3>⛽ Tankowania</h3>"
    for f in fuels:
        html+=f"Licznik: {f['mileage']} | Litry: {f['liters']}<br>"

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
    cur.execute("SELECT * FROM driver_days WHERE driver=%s AND date=%s",(user,today))
    day=cur.fetchone()

    if request.method=="POST":
        if "start_day" in request.form:
            if not day:
                cur.execute("INSERT INTO driver_days (driver,date,start_time) VALUES (%s,%s,%s)",(user,today,datetime.now()))
            else:
                cur.execute("UPDATE driver_days SET start_time=%s WHERE driver=%s AND date=%s",(datetime.now(),user,today))
            conn.commit()

        if "end_day" in request.form:
            cur.execute("UPDATE driver_days SET end_time=%s WHERE driver=%s AND date=%s",(datetime.now(),user,today))
            conn.commit()

        if "fuel" in request.form:
            cur.execute("INSERT INTO fuel_logs (driver,date,mileage,liters) VALUES (%s,%s,%s,%s)",(user,today,request.form["mileage"],request.form["liters"]))
            conn.commit()

        if "update_order" in request.form:
            cur.execute("UPDATE orders SET status=%s, quantity=%s, amount=%s, notes=%s, payment=%s WHERE id=%s AND driver=%s",(
                request.form["status"],
                request.form["quantity"],
                request.form["amount"],
                request.form["notes"],
                request.form["payment"],
                request.form["id"],
                user
            ))
            conn.commit()

    cur.execute("SELECT * FROM orders WHERE driver=%s AND date=%s ORDER BY time_slot",(user,today))
    orders=cur.fetchall()
    cur.close(); conn.close()

    html=f"<h2>🚛 Panel dzienny | {user.capitalize()} | {today}</h2>"

    if day and day.get("start_time"):
        html+=f"Czas pracy: {day.get('start_time')} - {day.get('end_time') or 'w trakcie'}<br>"

    for o in orders:
        html+=f"""
        <form method='post' style='background:{status_color(o['status'])};padding:10px;margin:10px;border-radius:6px'>
        <b>{o['client']}</b><br>
        {o['address']}<br>
        Status:<br><select name='status'>
            <option {'selected' if o['status']=="W TOKU" else ''}>W TOKU</option>
            <option {'selected' if o['status']=="WYKONANE" else ''}>WYKONANE</option>
            <option {'selected' if o['status']=="NIE WYKONANE" else ''}>NIE WYKONANE</option>
        </select><br>
        Ilość: <input name='quantity' value='{o['quantity'] or ""}'><br>
        Kwota: <input name='amount' value='{o['amount'] or ""}'><br>
        Notatki: <input name='notes' value='{o['notes'] or ""}'><br>
        Forma płatności:<br>
        <select name='payment'>
            <option value='Gotówka' {'selected' if o['payment']=='Gotówka' else ''}>Gotówka</option>
            <option value='Przelew' {'selected' if o['payment']=='Przelew' else ''}>Przelew</option>
        </select>
        <input type='hidden' name='id' value='{o['id']}'>
        <button name='update_order'>Zapisz</button>
        </form>
        """

    html+="<form method='post'>"
    if not day or not day.get("start_time"):
        html+="<button name='start_day'>▶️ Start dnia</button>"
    if day and not day.get("end_time"):
        html+="<button name='end_day'>⏹ Zakończ dzień</button>"
    html+="</form>"

    html+="<h3>⛽ Tankowanie</h3>"
    html+="<form method='post'>Stan licznika:<br><input name='mileage'><br>Litry:<br><input name='liters'><br><button name='fuel'>Zapisz tankowanie</button></form>"

    html+="<br><a href='/logout'>Wyloguj</a>"
    return html

if __name__ == "__main__":
    app.run()
