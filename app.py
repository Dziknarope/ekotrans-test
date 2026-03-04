from flask import Flask, request, redirect, session, send_file
from datetime import date
import os
import psycopg2
import psycopg2.extras
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import fonts
from reportlab.platypus import TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

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
        password TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS drivers (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        client TEXT,
        address TEXT,
        date DATE,
        driver TEXT,
        position INTEGER DEFAULT 1,
        status TEXT DEFAULT 'NOWE',
        notes TEXT
    );
    """)

    conn.commit()
    cur.close()
    conn.close()

def seed():
    conn = db()
    cur = conn.cursor()

    cur.execute("INSERT INTO users (login,password) VALUES ('admin','admin123') ON CONFLICT DO NOTHING")

    drivers = ["Leszek","Tadeusz","Marcel","Dyzio","Emil"]
    for d in drivers:
        cur.execute("INSERT INTO drivers (name) VALUES (%s) ON CONFLICT DO NOTHING",(d,))

    conn.commit()
    cur.close()
    conn.close()

init_db()
seed()

# =====================
# LOGIN
# =====================

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        conn=db(); cur=conn.cursor()
        cur.execute("SELECT * FROM users WHERE login=%s AND password=%s",
                    (request.form["login"],request.form["password"]))
        user=cur.fetchone()
        cur.close(); conn.close()
        if user:
            session["admin"]=True
            return redirect("/orders")
    return """
    <h2>Logowanie ADMIN</h2>
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

def auth():
    if not session.get("admin"):
        return False
    return True

# =====================
# LISTA ZAMÓWIEŃ
# =====================

@app.route("/orders", methods=["GET","POST"])
def orders():
    if not auth(): return redirect("/")

    conn=db(); cur=conn.cursor()

    if request.method=="POST":
        cur.execute("""
        INSERT INTO orders (client,address,date,driver,position,status)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,(
            request.form["client"],
            request.form["address"],
            request.form["date"],
            request.form["driver"],
            request.form["position"],
            request.form["status"]
        ))
        conn.commit()

    cur.execute("SELECT * FROM orders ORDER BY date DESC, driver, position")
    orders=cur.fetchall()

    cur.execute("SELECT name FROM drivers ORDER BY name")
    drivers=cur.fetchall()

    cur.close(); conn.close()

    html = "<h2>Zamówienia</h2>"
    html += "<a href='/logout'>Wyloguj</a><br><br>"

    html += """
    <h3>Dodaj zamówienie</h3>
    <form method='post'>
    Klient:<br><input name='client'><br>
    Adres:<br><input name='address'><br>
    Data:<br><input type='date' name='date' value='{}'><br>
    Kierowca:<br>
    <select name='driver'>
    """.format(date.today())

    for d in drivers:
        html+=f"<option>{d['name']}</option>"

    html+="</select><br>"
    html+="Pozycja w trasie:<br><input name='position' value='1'><br>"
    html+="Status:<br><select name='status'><option>NOWE</option><option>W TRASIE</option><option>DOSTARCZONE</option></select><br><br>"
    html+="<button>Dodaj</button></form><hr>"

    for o in orders:
        html+=f"""
        <div style='border:1px solid #ccc;padding:10px;margin:5px'>
        <b>{o['date']} | {o['driver']} | Poz: {o['position']}</b><br>
        {o['client']} - {o['address']}<br>
        Status: {o['status']}
        </div>
        """

    html+="<hr><h3>Trasówki</h3>"
    html+="<form method='get' action='/route'>Data:<input type='date' name='date'> Kierowca:<input name='driver'><button>Pokaż</button></form>"

    return html

# =====================
# WIDOK TRASY + PDF
# =====================

@app.route("/route")
def route():
    if not auth(): return redirect("/")

    rdate=request.args.get("date")
    driver=request.args.get("driver")

    conn=db(); cur=conn.cursor()
    cur.execute("""
    SELECT * FROM orders
    WHERE date=%s AND driver=%s
    ORDER BY position
    """,(rdate,driver))
    orders=cur.fetchall()
    cur.close(); conn.close()

    html=f"<h2>Trasa {driver} | {rdate}</h2>"
    html+=f"<a href='/route/pdf?date={rdate}&driver={driver}'>📄 Generuj PDF</a><br><br>"

    for o in orders:
        html+=f"{o['position']}. {o['client']} - {o['address']} ({o['status']})<br>"

    html+="<br><a href='/orders'>← Wróć</a>"
    return html

# =====================
# GENEROWANIE PDF
# =====================

@app.route("/route/pdf")
def route_pdf():
    if not auth(): return redirect("/")

    rdate=request.args.get("date")
    driver=request.args.get("driver")

    conn=db(); cur=conn.cursor()
    cur.execute("""
    SELECT * FROM orders
    WHERE date=%s AND driver=%s
    ORDER BY position
    """,(rdate,driver))
    orders=cur.fetchall()
    cur.close(); conn.close()

    filename=f"trasa_{driver}_{rdate}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements=[]

    styles=getSampleStyleSheet()
    elements.append(Paragraph(f"Trasa: {driver} | Data: {rdate}", styles["Heading1"]))
    elements.append(Spacer(1,0.3*inch))

    data=[["Poz","Klient","Adres","Status"]]

    for o in orders:
        data.append([o["position"],o["client"],o["address"],o["status"]])

    table=Table(data, colWidths=[40,150,200,100])
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ]))

    elements.append(table)
    doc.build(elements)

    return send_file(filename, as_attachment=True)

# =====================
# START
# =====================

if __name__ == "__main__":
    app.run(debug=True)
