from flask import Flask, request, redirect, session
from datetime import date, datetime
import os
import psycopg2
import psycopg2.extras

app = Flask(name)
app.secret_key = "supersecretkey"

DATABASE_URL = os.environ.get("DATABASE_URL") if not DATABASE_URL: raise Exception("Brak DATABASE_URL")

def db(): return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

=====================

INIT BAZY

=====================

def init_db(): conn = db() cur = conn.cursor()

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
    time_slot TEXT
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS driver_days (
    id SERIAL PRIMARY KEY,
    driver TEXT,
    date DATE,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    closed BOOLEAN DEFAULT FALSE
);
""")

conn.commit()
cur.close()
conn.close()

init_db()

=====================

POMOCNICZE

=====================

def is_admin(): return session.get("role") == "admin"

def is_driver(): return session.get("role") == "driver"

def status_color(status): colors = { "DO REALIZACJI": "#cce5ff", "W TOKU": "#fff3cd", "NIE WYKONANE": "#f8d7da", "WYKONANE": "#d4edda" } return colors.get(status, "#ffffff")

def sidebar(): return """ <div style='width:230px;background:#1f2937;height:100vh;float:left;padding:20px'> <h3 style='color:white'>ADMIN</h3> <a href='/admin' style='display:block;background:#374151;color:white;padding:10px;border-radius:8px;margin-bottom:10px;text-decoration:none'>Nowe zlecenie</a> <a href='/admin/active' style='display:block;background:#374151;color:white;padding:10px;border-radius:8px;margin-bottom:10px;text-decoration:none'>Aktywne</a> <a href='/admin/done' style='display:block;background:#374151;color:white;padding:10px;border-radius:8px;margin-bottom:10px;text-decoration:none'>Wykonane</a> <a href='/admin/routes' style='display:block;background:#374151;color:white;padding:10px;border-radius:8px;margin-bottom:10px;text-decoration:none'>Trasowki</a> <a href='/logout' style='display:block;background:#7f1d1d;color:white;padding:10px;border-radius:8px;margin-top:20px;text-decoration:none'>Wyloguj</a> </div> """

=====================

LOGIN

=====================

@app.route("/", methods=["GET", "POST"]) def login(): if request.method == "POST": conn = db(); cur = conn.cursor() cur.execute("SELECT * FROM users WHERE login=%s AND password=%s", (request.form["login"], request.form["password"])) user = cur.fetchone() cur.close(); conn.close() if user: session["user"] = user["login"] session["role"] = user["role"] return redirect("/admin" if user["role"] == "admin" else "/driver")

return """
<h2>Logowanie</h2>
<form method='post'>
Login:<br><input name='login'><br>
Haslo:<br><input type='password' name='password'><br><br>
<button>Zaloguj</button>
</form>
"""

@app.route("/logout") def logout(): session.clear() return redirect("/")

=====================

ADMIN NOWE ZLECENIE

=====================

@app.route("/admin", methods=["GET", "POST"]) def admin_new(): if not is_admin(): return redirect("/")

conn = db(); cur = conn.cursor()
cur.execute("SELECT login FROM users WHERE role='driver'")
drivers = [d["login"] for d in cur.fetchall()]

if request.method == "POST":
    cur.execute("""
    INSERT INTO orders (client,address,date,status,driver,time_slot)
    VALUES (%s,%s,%s,'DO REALIZACJI',%s,%s)
    """, (
        request.form["client"],
        request.form["address"],
        request.form["date"],
        request.form["driver"],
        request.form["time_slot"]
    ))
    conn.commit()
    return redirect("/admin")

html = sidebar() + "<div style='margin-left:260px;padding:20px'>"
html += "<h2>Dodaj nowe zlecenie</h2>"
html += "<form method='post'>"
html += "Klient:<br><input name='client'><br>"
html += "Adres:<br><input name='address'><br>"
html += f"Data:<br><input type='date' name='date' value='{date.today()}'><br>"
html += "Pora dnia:<br><select name='time_slot'>"
html += "<option>Rano 7-11</option>"
html += "<option>Poludnie 11-15</option>"
html += "<option>Po 15:00</option>"
html += "</select><br>"
html += "Kierowca:<br><select name='driver'>"
for d in drivers:
    html += f"<option>{d}</option>"
html += "</select><br><br><button>Dodaj</button></form></div>"

cur.close(); conn.close()
return html

=====================

ADMIN WYKONANE

=====================

@app.route("/admin/done") def admin_done(): if not is_admin(): return redirect("/") conn = db(); cur = conn.cursor() cur.execute("SELECT * FROM orders WHERE status='WYKONANE' ORDER BY date DESC") orders = cur.fetchall() cur.close(); conn.close()

html = sidebar() + "<div style='margin-left:260px;padding:20px'><h2>Wykonane</h2>"
html += "<table border='1' cellpadding='6'><tr><th>Data</th><th>Kierowca</th><th>Klient</th><th>Adres</th><th>Ilosc m3</th><th>Kwota</th></tr>"
for o in orders:
    html += f"<tr><td>{o['date']}</td><td>{o['driver']}</td><td>{o['client']}</td><td>{o['address']}</td><td>{o['quantity']}</td><td>{o['amount']}</td></tr>"
html += "</table></div>"
return html

=====================

ADMIN TRASOWKI

=====================

@app.route("/admin/routes") def admin_routes(): if not is_admin(): return redirect("/") conn = db(); cur = conn.cursor() cur.execute("SELECT DISTINCT driver FROM orders") drivers = [d['driver'] for d in cur.fetchall()] cur.close(); conn.close()

html = sidebar() + "<div style='margin-left:260px;padding:20px'><h2>Wybierz kierowce</h2>"
for d in drivers:
    html += f"<a href='/admin/routes/{d}' style='display:inline-block;background:#2563eb;color:white;padding:15px 25px;border-radius:25px;margin:10px;text-decoration:none'>{d}</a>"
html += "</div>"
return html

@app.route("/admin/routes/<driver>") def admin_route_dates(driver): if not is_admin(): return redirect("/") conn = db(); cur = conn.cursor() cur.execute("SELECT DISTINCT date FROM orders WHERE driver=%s ORDER BY date DESC", (driver,)) dates = cur.fetchall() cur.close(); conn.close()

html = sidebar() + f"<div style='margin-left:260px;padding:20px'><h2>{driver}</h2>"
for d in dates:
    html += f"<a href='/admin/route/{driver}/{d['date']}' style='display:block;margin:8px 0'>{d['date']}</a>"
html += "</div>"
return html

@app.route("/admin/route/<driver>/<rdate>") def admin_route_detail(driver, rdate): if not is_admin(): return redirect("/") conn = db(); cur = conn.cursor() cur.execute("SELECT * FROM orders WHERE driver=%s AND date=%s ORDER BY time_slot", (driver, rdate)) orders = cur.fetchall() cur.close(); conn.close()

html = sidebar() + f"<div style='margin-left:260px;padding:20px'><h2>Trasa {driver} {rdate}</h2>"
for o in orders:
    html += f"{o['time_slot']} - {o['client']} - {o['address']}<br>"
html += "</div>"
return html

=====================

PANEL KIEROWCY

=====================

@app.route("/driver", methods=["GET", "POST"]) def driver_panel(): if not is_driver(): return redirect("/") user = session["user"] today = date.today()

conn = db(); cur = conn.cursor()

cur.execute("SELECT * FROM driver_days WHERE driver=%s AND date=%s", (user, today))
day = cur.fetchone()

if request.method == "POST" and "start_day" in request.form:
    cur.execute("INSERT INTO driver_days (driver,date,started_at,closed) VALUES (%s,%s,%s,FALSE)",
                (user, today, datetime.now()))
    conn.commit()

if request.method == "POST" and "end_day" in request.form:
    cur.execute("UPDATE driver_days SET ended_at=%s, closed=TRUE WHERE driver=%s AND date=%s",
                (datetime.now(), user, today))
    conn.commit()

if request.method == "POST" and "update_order" in request.form:
    cur.execute("""
    UPDATE orders SET status=%s, quantity=%s, amount=%s, payment=%s, notes=%s
    WHERE id=%s AND driver=%s
    """, (
        request.form["status"],
        request.form["quantity"],
        request.form["amount"],
        request.form["payment"],
        request.form["notes"],
        request.form["id"],
        user
    ))
    conn.commit()

cur.execute("SELECT * FROM orders WHERE driver=%s AND date=%s ORDER BY time_slot", (user, today))
orders = cur.fetchall()

html = f"<h2>Panel kierowcy | {user} | {today}</h2>"

if not day:
    html += "<form method='post'><button name='start_day'>Start dzien</button></form>"

if day and not day['closed']:
    html += "<form method='post'><button name='end_day'>Zakoncz dzien</button></form>"

if day and day.get('started_at') and day.get('ended_at'):
    diff = day['ended_at'] - day['started_at']
    hours = round(diff.total_seconds() / 3600, 2)
    html += f"<p>Czas pracy: {hours} h</p>"

for o in orders:
    html += f"""
    <form method='post' style='background:{status_color(o['status'])};padding:10px;margin:10px;border-radius:6px'>
    <b>{o['client']}</b><br>
    {o['address']}<br>
    <select name='status'>
        <option {'selected' if o['status']=='W TOKU' else ''}>W TOKU</option>
        <option {'selected' if o['status']=='WYKONANE' else ''}>WYKONANE</option>
        <option {'selected' if o['status']=='NIE WYKONANE' else ''}>NIE WYKONANE</option>
    </select><br>
    Ilosc m3: <input name='quantity' value='{o['quantity'] or ''}'><br>
    Kwota: <input name='amount' value='{o['amount'] or ''}'><br>
    Forma platnosci:
    <select name='payment'>
        <option {'selected' if o['payment']=='Gotowka' else ''}>Gotowka</option>
        <option {'selected' if o['payment']=='Przelew' else ''}>Przelew</option>
    </select><br>
    Notatki: <input name='notes' value='{o['notes'] or ''}'><br>
    <input type='hidden' name='id' value='{o['id']}'>
    <button name='update_order'>Zapisz</button>
    </form>
    """

html += "<br><a href='/logout'>Wyloguj</a>"
cur.close(); conn.close()
return html

if name == "main": app.run()
