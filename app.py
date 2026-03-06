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

# =============================
# STAŁE POJAZDY
# =============================

VEHICLES = [
"LKR18456",
"LKR54VN",
"LKR61886",
"LKR40306",
"LKR77777"
]

# =============================
# INIT BAZY
# =============================

def init_db():

    conn=db()
    cur=conn.cursor()

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

# =============================
# DANE TESTOWE
# =============================

def seed_data():

    conn=db()
    cur=conn.cursor()

    cur.execute("SELECT COUNT(*) FROM orders")
    count=cur.fetchone()["count"]

    if count==0:

        today=date.today()

        data=[

("Jan Kowalski","Kraków Zakopiańska 12","500100200","2t","Gotówka","800","",today,"Rano","DO REALIZACJI",None,None),

("Anna Nowak","Wieliczka Solna 5","501200300","1t","Przelew","420","",today,"","DO REALIZACJI",None,None),

("Budmex","Niepołomice Przemysłowa 3","502300400","3t","Gotówka","1200","",today,"Rano","DO REALIZACJI",None,None),

("Tomasz Zieliński","Bochnia Krakowska 22","503400500","1.5t","Gotówka","600","",today,"","DO REALIZACJI",None,None),

("Skład XYZ","Myślenice Słoneczna 7","504500600","4t","Przelew","2000","",today,"Rano","DO REALIZACJI",None,None),

("Piotr Wójcik","Dobczyce Parkowa 10","505600700","2t","Gotówka","900","",today,"","DO REALIZACJI",None,None)

]

        for o in data:

            cur.execute("""
            INSERT INTO orders
            (client,address,phone,quantity,payment,amount,notes,date,time_slot,status,vehicle,route_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,o)

    conn.commit()
    cur.close()
    conn.close()

init_db()
seed_data()

# =============================
# KOLORY STATUSÓW
# =============================

def status_color(status):

    colors={
    "DO REALIZACJI":"#cce5ff",
    "W TOKU":"#fff3cd",
    "NIE WYKONANE":"#f8d7da",
    "WYKONANE":"#d4edda"
    }

    return colors.get(status,"white")

# =============================
# SIDEBAR
# =============================

def sidebar():

    return """

    <div style='
    width:220px;
    height:100vh;
    background:#2c3e50;
    color:white;
    padding:20px;
    display:inline-block;
    vertical-align:top;
    font-family:Arial'>

    <h2>LOGISTYKA</h2>

    <hr>

    <a href='/orders' style='color:white;text-decoration:none;display:block;margin:10px 0'>📋 Zamówienia</a>

    <a href='/add' style='color:white;text-decoration:none;display:block;margin:10px 0'>➕ Dodaj zamówienie</a>

    <a href='/routes' style='color:white;text-decoration:none;display:block;margin:10px 0'>🚚 Trasówki</a>

    <a href='/logout' style='color:#ffaaaa;text-decoration:none;display:block;margin-top:40px'>Wyloguj</a>

    </div>

    """

# =============================
# LOGIN
# =============================

@app.route("/",methods=["GET","POST"])
def login():

    if request.method=="POST":

        if request.form["password"]=="Turcja123":

            session["admin"]=True
            return redirect("/orders")

    return """

    <h2>Logowanie</h2>

    <form method='post'>

    Hasło<br>
    <input type='password' name='password'>

    <br><br>

    <button>Zaloguj</button>

    </form>

    """

# =============================
# LOGOUT
# =============================

@app.route("/logout")
def logout():

    session.clear()
    return redirect("/")

# =============================
# LISTA ZAMÓWIEŃ
# =============================

@app.route("/orders")
def orders():

    if not session.get("admin"):
        return redirect("/")

    conn=db()
    cur=conn.cursor()

    cur.execute("SELECT * FROM orders WHERE status!='WYKONANE' ORDER BY id DESC")
    orders=cur.fetchall()

    cur.close()
    conn.close()

    html=sidebar()+"<div style='display:inline-block;padding:20px'>"

    html+="<h2>Aktywne zamówienia</h2>"

    for o in orders:

        vehicle_select="<select name='vehicle'>"

        for v in VEHICLES:

            selected="selected" if o["vehicle"]==v else ""

            vehicle_select+=f"<option {selected}>{v}</option>"

        vehicle_select+="</select>"

        html+=f"""

        <form method='post' action='/assign' style='
        background:{status_color(o['status'])};
        padding:10px;
        margin:10px;
        border-radius:8px'>

        <b>{o['client']}</b><br>

        {o['address']}<br>

        Tel: {o['phone']}<br>

        Ilość: {o['quantity']}<br>

        Pora dnia: {o['time_slot']}<br><br>

        Pojazd: {vehicle_select}<br>

        Data trasy:
        <input type='date' name='route_date' value='{date.today()}'>

        <input type='hidden' name='id' value='{o['id']}'>

        <br><br>

        <button>Przypisz do trasówki</button>

        </form>

        """

    html+="</div>"

    return html

# =============================
# PRZYPISANIE DO TRASY
# =============================

@app.route("/assign",methods=["POST"])
def assign():

    conn=db()
    cur=conn.cursor()

    cur.execute("""

    UPDATE orders
    SET vehicle=%s,
    route_date=%s

    WHERE id=%s

    """,(request.form["vehicle"],request.form["route_date"],request.form["id"]))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/orders")

# =============================
# DODAJ ZAMÓWIENIE
# =============================

@app.route("/add",methods=["GET","POST"])
def add():

    if request.method=="POST":

        conn=db()
        cur=conn.cursor()

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

    return sidebar()+"""

    <div style='display:inline-block;padding:20px'>

    <h2>Dodaj zamówienie</h2>

    <form method='post'>

    Klient<br>
    <input name='client'><br>

    Adres<br>
    <input name='address'><br>

    Telefon<br>
    <input name='phone'><br>

    Ilość<br>
    <input name='quantity'><br>

    Płatność<br>
    <input name='payment'><br>

    Kwota<br>
    <input name='amount'><br>

    Notatki<br>
    <input name='notes'><br>

    Data<br>
    <input type='date' name='date'><br>

    Pora dnia<br>

    <select name='time_slot'>
    <option value=''>--</option>
    <option>Rano</option>
    </select>

    <br><br>

    <button>Dodaj</button>

    </form>

    </div>

    """

# =============================
# TRASÓWKI
# =============================

@app.route("/routes")
def routes():

    conn=db()
    cur=conn.cursor()

    cur.execute("""

    SELECT DISTINCT vehicle,route_date
    FROM orders
    WHERE vehicle IS NOT NULL
    ORDER BY route_date DESC

    """)

    routes=cur.fetchall()

    cur.close()
    conn.close()

    html=sidebar()+"<div style='display:inline-block;padding:20px'>"

    html+="<h2>Trasówki</h2>"

    for r in routes:

        html+=f"""

        <a href='/route/{r['vehicle']}/{r['route_date']}'>
        {r['vehicle']} | {r['route_date']}
        </a><br><br>

        """

    html+="</div>"

    return html

# =============================
# SZCZEGÓŁ TRASY
# =============================

@app.route("/route/<vehicle>/<rdate>")
def route_detail(vehicle,rdate):

    conn=db()
    cur=conn.cursor()

    cur.execute("""

    SELECT *
    FROM orders
    WHERE vehicle=%s
    AND route_date=%s

    """,(vehicle,rdate))

    orders=cur.fetchall()

    cur.close()
    conn.close()

    html=sidebar()+"<div style='display:inline-block;padding:20px'>"

    html+=f"<h2>Trasa {vehicle} {rdate}</h2>"

    html+=f"<a href='/pdf/{vehicle}/{rdate}'>📄 Drukuj PDF</a><br><br>"

    for o in orders:

        html+=f"""

        <div style='padding:10px;border:1px solid #ccc;margin-bottom:10px'>

        <b>{o['client']}</b><br>

        {o['address']}<br>

        Tel: {o['phone']}<br>

        Ilość: {o['quantity']}<br>

        {o['notes']}

        </div>

        """

    html+="</div>"

    return html

# =============================
# PDF
# =============================

@app.route("/pdf/<vehicle>/<rdate>")
def pdf(vehicle,rdate):

    conn=db()
    cur=conn.cursor()

    cur.execute("""

    SELECT *
    FROM orders
    WHERE vehicle=%s
    AND route_date=%s

    """,(vehicle,rdate))

    orders=cur.fetchall()

    cur.close()
    conn.close()

    file="route.pdf"

    c=canvas.Canvas(file)

    y=800

    c.drawString(50,y,f"Trasówka {vehicle} {rdate}")

    y-=40

    for o in orders:

        c.drawString(50,y,o["client"])
        y-=15
        c.drawString(50,y,o["address"])
        y-=15
        c.drawString(50,y,o["quantity"])
        y-=30

    c.save()

    return send_file(file,as_attachment=True)

# =============================

if __name__=="__main__":
    app.run()
