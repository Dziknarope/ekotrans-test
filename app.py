from flask import Flask, request, redirect, session, send_file
from datetime import date
import os
import psycopg2
import psycopg2.extras
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE_URL = os.environ.get("DATABASE_URL")

def db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


# =========================
# STAŁE
# =========================

VEHICLES = [
    "LKR18456",
    "LKR54VN",
    "LKR61886",
    "LKR40306"
]

STATUSES = [
    "DO REALIZACJI",
    "W TOKU",
    "NIE WYKONANE",
    "WYKONANE"
]


# =========================
# BAZA
# =========================

def init_db():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id SERIAL PRIMARY KEY,
        client TEXT,
        address TEXT,
        phone TEXT,
        quantity TEXT,
        payment TEXT,
        amount TEXT,
        notes TEXT,
        date DATE,
        time_slot TEXT,
        status TEXT,
        vehicle TEXT,
        route_date DATE
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()


# =========================
# LOGIN
# =========================

@app.route("/", methods=["GET","POST"])
def login():

    if request.method == "POST":

        if request.form["login"] == "admin" and request.form["password"] == "Turcja123":
            session["user"] = "admin"
            return redirect("/orders")

    return """
    <h2>Logowanie</h2>

    <form method='post'>
    Login<br>
    <input name='login'><br><br>

    Hasło<br>
    <input type='password' name='password'><br><br>

    <button>Zaloguj</button>
    </form>
    """


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================
# SIDEBAR
# =========================

def sidebar():

    return """
    <div style='width:220px;background:#2c3e50;color:white;height:100vh;padding:20px;display:inline-block;vertical-align:top;font-family:Arial'>

    <h3>MENU</h3>

    <a href='/orders/new' style='color:white;text-decoration:none;display:block;margin-top:15px'>➕ Nowe zamówienie</a>

    <a href='/orders' style='color:white;text-decoration:none;display:block;margin-top:10px'>📋 Zamówienia</a>

    <a href='/routes' style='color:white;text-decoration:none;display:block;margin-top:10px'>🚛 Trasówki</a>

    <a href='/done' style='color:white;text-decoration:none;display:block;margin-top:10px'>✅ Wykonane</a>

    <a href='/logout' style='color:#ffaaaa;text-decoration:none;display:block;margin-top:30px'>Wyloguj</a>

    </div>
    """


# =========================
# NOWE ZAMÓWIENIE
# =========================

@app.route("/orders/new", methods=["GET","POST"])
def new_order():

    if "user" not in session:
        return redirect("/")

    if request.method == "POST":

        conn = db()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO orders
        (client,address,phone,quantity,payment,amount,notes,date,time_slot,status)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'DO REALIZACJI')
        """,(

            request.form["client"],
            request.form["address"],
            request.form["phone"],
            request.form["quantity"],
            request.form["payment"],
            request.form["amount"],
            request.form["notes"],
            request.form["date"],
            request.form["time_slot"]

        ))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/orders")

    return sidebar() + """

    <div style='padding:30px;display:inline-block;vertical-align:top'>

    <h2>Nowe zamówienie</h2>

    <form method='post'>

    Klient<br>
    <input name='client'><br><br>

    Adres<br>
    <input name='address'><br><br>

    Telefon<br>
    <input name='phone'><br><br>

    Ilość<br>
    <input name='quantity'><br><br>

    Płatność<br>
    <input name='payment'><br><br>

    Kwota<br>
    <input name='amount'><br><br>

    Notatki<br>
    <input name='notes'><br><br>

    Data<br>
    <input type='date' name='date'><br><br>

    Pora dnia<br>
    <select name='time_slot'>
    <option value=''>---</option>
    <option>Rano</option>
    </select><br><br>

    <button>Dodaj zamówienie</button>

    </form>

    </div>
    """


# =========================
# ZAMÓWIENIA
# =========================

@app.route("/orders", methods=["GET","POST"])
def orders():

    if "user" not in session:
        return redirect("/")

    conn = db()
    cur = conn.cursor()

    if request.method == "POST":

        cur.execute("""
        UPDATE orders
        SET status=%s, vehicle=%s, route_date=%s
        WHERE id=%s
        """,(

            request.form["status"],
            request.form["vehicle"],
            request.form["route_date"],
            request.form["id"]

        ))

        conn.commit()

    cur.execute("SELECT * FROM orders WHERE status!='WYKONANE' ORDER BY date")
    orders = cur.fetchall()

    cur.close()
    conn.close()

    html = sidebar() + "<div style='padding:30px;display:inline-block;vertical-align:top'>"

    html += "<h2>Aktywne zamówienia</h2>"

    for o in orders:

        vehicle_options = "<option value=''></option>"

        for v in VEHICLES:

            selected = "selected" if o["vehicle"] == v else ""

            vehicle_options += f"<option {selected}>{v}</option>"

        status_options = ""

        for s in STATUSES:

            selected = "selected" if o["status"] == s else ""

            status_options += f"<option {selected}>{s}</option>"

        html += f"""

        <form method='post' style='border:1px solid #ccc;padding:10px;margin-bottom:10px'>

        <b>{o['client']}</b><br>

        {o['address']}<br><br>

        Pojazd<br>

        <select name='vehicle'>
        {vehicle_options}
        </select><br><br>

        Data trasy<br>

        <input type='date' name='route_date' value='{o['route_date'] or ""}'><br><br>

        Status<br>

        <select name='status'>
        {status_options}
        </select><br><br>

        <input type='hidden' name='id' value='{o['id']}'>

        <button>Zapisz</button>

        </form>
        """

    html += "</div>"

    return html


# =========================
# TRASÓWKI
# =========================

@app.route("/routes")
def routes():

    if "user" not in session:
        return redirect("/")

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    SELECT route_date, vehicle
    FROM orders
    WHERE vehicle IS NOT NULL
    GROUP BY route_date, vehicle
    ORDER BY route_date DESC
    """)

    routes = cur.fetchall()

    cur.close()
    conn.close()

    html = sidebar() + "<div style='padding:30px;display:inline-block;vertical-align:top'>"

    html += "<h2>Trasówki</h2>"

    for r in routes:

        html += f"""
        <a href='/route/{r['vehicle']}/{r['route_date']}'>
        {r['route_date']} | {r['vehicle']}
        </a><br><br>
        """

    html += "</div>"

    return html


# =========================
# PDF
# =========================

@app.route("/route/<vehicle>/<rdate>")
def route(vehicle,rdate):

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM orders
    WHERE vehicle=%s AND route_date=%s
    """,(vehicle,rdate))

    orders = cur.fetchall()

    cur.close()
    conn.close()

    filename = f"route_{vehicle}.pdf"

    c = canvas.Canvas(filename)

    y = 800

    c.drawString(50,y,f"TRASA {rdate} | {vehicle}")

    y -= 40

    i = 1

    for o in orders:

        c.drawString(50,y,f"{i}. {o['client']}")

        y -= 20

        c.drawString(70,y,o["address"])

        y -= 30

        i += 1

    c.save()

    return send_file(filename, as_attachment=True)


# =========================
# WYKONANE
# =========================

@app.route("/done")
def done():

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM orders WHERE status='WYKONANE' ORDER BY date DESC")

    orders = cur.fetchall()

    cur.close()
    conn.close()

    html = sidebar() + "<div style='padding:30px;display:inline-block;vertical-align:top'>"

    html += "<h2>Wykonane</h2>"

    for o in orders:

        html += f"{o['date']} | {o['client']}<br>"

    html += "</div>"

    return html


# =========================
# START
# =========================

if __name__ == "__main__":
    app.run()
