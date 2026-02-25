from flask import Flask, request, redirect, session
from datetime import date
import os
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = "supersekretnyklucz123"

# Pobierz URL bazy z Environment
DATABASE_URL = os.environ.get("DATABASE_URL")

# Funkcja połączenia z bazą
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

# Tworzymy tabele jeśli nie istnieją
def init_db():
    conn = get_db()
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
        mass REAL,
        payment TEXT,
        amount REAL,
        notes TEXT
    );
    """)
    conn.commit()
    cur.close()
    conn.close()

# Dodajemy użytkowników jeśli ich nie ma
def init_users():
    conn = get_db()
    cur = conn.cursor()
    users = [
        ("admin", "Turcja123", "admin"),
        ("leszek", "LKR18456", "driver"),
        ("tadeusz", "LKR54VN", "driver"),
        ("marcel", "LKR61886", "driver"),
        ("dyzio", "LKR40306", "driver"),
        ("emil", "Turcja123", "driver")
    ]
    for login, password, role in users:
        cur.execute("INSERT INTO users (login,password,role) VALUES (%s,%s,%s) ON CONFLICT (login) DO NOTHING", (login,password,role))
    conn.commit()
    cur.close()
    conn.close()

# Kolory statusów
def status_color(status):
    if status == "DO REALIZACJI":
        return "#ff9800"
    if status == "W TOKU":
        return "#2196f3"
    if status == "WYKONANE":
        return "#4caf50"
    return "#999"

# Sesje
def is_logged():
    return "user" in session

def current_user():
    return session.get("user")

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_input = request.form["login"]
        password_input = request.form["password"]
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE login=%s AND password=%s", (login_input,password_input))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            session["user"] = user[1]  # login
            session["role"] = user[3]  # role
            if user[3]=="admin":
                return redirect("/admin")
            else:
                return redirect("/driver")
    return """
    <body style='background:#f4f6f9;font-family:Arial;padding:40px;text-align:center'>
        <h2>🔐 Logowanie EkoTrans</h2>
        <form method='post' style='background:white;padding:30px;border-radius:10px;display:inline-block'>
            Login:<br>
            <input name='login' style='padding:10px;margin-bottom:10px'><br>
            Hasło:<br>
            <input type='password' name='password' style='padding:10px;margin-bottom:20px'><br>
            <button type='submit' style='padding:10px 20px;background:#4caf50;color:white;border:none;border-radius:5px'>
                Zaloguj
            </button>
        </form>
    </body>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/admin", methods=["GET","POST"])
def admin():
    if not is_logged() or session["role"]!="admin":
        return redirect("/")
    conn = get_db()
    cur = conn.cursor()
    if request.method=="POST":
        client = request.form["client"]
        address = request.form["address"]
        date_input = request.form["date"]
        driver = request.form["driver"]
        cur.execute("INSERT INTO orders (client,address,date,status,driver) VALUES (%s,%s,%s,%s,%s)",
                    (client,address,date_input,"DO REALIZACJI",driver))
        conn.commit()
        return redirect("/admin")
    cur.execute("SELECT * FROM orders ORDER BY date DESC")
    orders = cur.fetchall()
    cur.close()
    conn.close()

    html = f"""
    <body style='background:#f4f6f9;font-family:Arial;padding:30px'>
    <h2>📋 Panel Admin</h2>
    Zalogowany: {current_user()} | <a href='/logout'>Wyloguj</a><br><br>

    <h3>➕ Dodaj nowe zlecenie</h3>
    <form method='post' style='background:white;padding:20px;border-radius:10px;margin-bottom:30px'>
        Klient:<br>
        <input name='client' style='width:100%;padding:10px;margin-bottom:10px'>
        Adres:<br>
        <input name='address' style='width:100%;padding:10px;margin-bottom:10px'>
        Data:<br>
        <input type='date' name='date' value='{str(date.today())}' style='width:100%;padding:10px;margin-bottom:10px'>
        Kierowca:<br>
        <select name='driver' style='width:100%;padding:10px;margin-bottom:20px'>
            <option>leszek</option>
            <option>tadeusz</option>
            <option>marcel</option>
            <option>dyzio</option>
            <option>emil</option>
        </select>
        <button type='submit' style='padding:12px 20px;background:#4caf50;color:white;border:none;border-radius:6px'>
            Dodaj zlecenie
        </button>
    </form>

    <h3>📦 Wszystkie zlecenia</h3>
    """
    for z in orders:
        html += f"""
        <div style='background:white;padding:15px;margin-bottom:10px;border-radius:8px'>
            <b>{z[1]}</b> | {z[2]} | {z[3]}<br>
            Kierowca: {z[5]}<br>
            Status: <span style='color:{status_color(z[4])}'>{z[4]}</span><br>
            Masa: {z[6]} m³ | Płatność: {z[7]} | Kwota: {z[8]}<br>
            Notatki: {z[9]}
        </div>
        """
    html += "</body>"
    return html

@app.route("/driver", methods=["GET","POST"])
def driver():
    if not is_logged() or session["role"]!="driver":
        return redirect("/")
    user = current_user()
    conn = get_db()
    cur = conn.cursor()
    if request.method=="POST":
        order_id = int(request.form["order"])
        cur.execute("""UPDATE orders SET status='WYKONANE', mass=%s, payment=%s, amount=%s, notes=%s
                       WHERE id=%s AND driver=%s""",
                    (request.form["mass"], request.form["payment"], request.form["amount"], request.form["notes"], order_id, user))
        conn.commit()
        return redirect("/driver")
    cur.execute("SELECT * FROM orders WHERE driver=%s ORDER BY date DESC", (user,))
    orders = cur.fetchall()
    cur.close()
    conn.close()

    html = f"""
    <body style='background:#f4f6f9;font-family:Arial;padding:30px'>
    <h2>🚛 Panel Kierowcy</h2>
    Zalogowany: {user} | <a href='/logout'>Wyloguj</a><br><br>
    """
    for z in orders:
        html += f"""
        <form method='post' style='background:white;padding:20px;margin-bottom:20px;border-radius:10px'>
            <b>{z[1]}</b><br>
            {z[2]} | {z[3]}<br>
            Status: {z[4]}<br><br>

            <input type='hidden' name='order' value='{z[0]}'>

            Masa (m³):<br>
            <input name='mass' style='width:100%;padding:10px;margin-bottom:10px'>

            Płatność:<br>
            <select name='payment' style='width:100%;padding:10px;margin-bottom:10px'>
                <option>Gotówka</option>
                <option>Przelew</option>
            </select>

            Kwota:<br>
            <input name='amount' style='width:100%;padding:10px;margin-bottom:10px'>

            Notatki:<br>
            <input name='notes' style='width:100%;padding:10px;margin-bottom:20px'>

            <button type='submit' style='width:100%;padding:12px;background:#2196f3;color:white;border:none;border-radius:6px'>
                Zakończ zlecenie
            </button>
        </form>
        """
    html += "</body>"
    return html

if __name__=="__main__":
    init_db()
    init_users()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
