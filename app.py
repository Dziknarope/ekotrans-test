from flask import Flask, request, redirect, session from datetime import date, datetime import os import psycopg2 import psycopg2.extras

app = Flask(name) app.secret_key = "supersecretkey"

DATABASE_URL = os.environ.get("DATABASE_URL") if not DATABASE_URL: raise Exception("Brak DATABASE_URL")

def db(): return psycopg2.connect( DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor )

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

@app.route("/", methods=["GET", "POST"]) def login(): if request.method == "POST": conn = db() cur = conn.cursor() cur.execute( "SELECT * FROM users WHERE login=%s AND password=%s", (request.form["login"], request.form["password"]) ) user = cur.fetchone() cur.close() conn.close()

if user:
        session["user"] = user["login"]
        session["role"] = user["role"]
        if user["role"] == "admin":
            return redirect("/admin")
        return redirect("/driver")

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

ADMIN - NOWE ZLECENIE

=====================

@app.route("/admin", methods=["GET", "POST"]) def admin_new(): if not is_admin(): return redirect("/")

conn = db()
cur = conn.cursor()

cur.execute("SELECT login FROM users WHERE role='driver'")
drivers = [d["login"] for d in cur.fetchall()]

if request.method == "POST":
    cur.execute(
        """
        INSERT INTO orders (client,address,date,status,driver,time_slot)
        VALUES (%s,%s,%s,'DO REALIZACJI',%s,%s)
        """,
        (
            request.form["client"],
            request.form["address"],
            request.form["date"],
            request.form["driver"],
            request.form["time_slot"]
        )
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/admin")

html = sidebar()
html += "<div style='margin-left:260px;padding:20px'>"
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

cur.close()
conn.close()
return html

if name == "main": app.run()
