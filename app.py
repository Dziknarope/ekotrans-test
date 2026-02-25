from flask import Flask, request, redirect, session
from datetime import date
import os
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = "supersekretnyklucz123"
app.debug = True  # tymczasowo włączone dla debugowania

# Pobranie URL bazy z Environment
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("DATABASE_URL nie ustawione! Dodaj zmienną środowiskową.")

# Połączenie z bazą
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

# Tworzenie tabel jeśli nie istnieją
def create_tables_if_not_exist():
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
        quantity REAL,
        payment TEXT,
        amount REAL,
        notes TEXT,
        reason TEXT
    );
    """)
    conn.commit()
    cur.close()
    conn.close()

# Dodanie domyślnych użytkowników
def create_default_users():
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
        cur.execute(
            "INSERT INTO users (login,password,role) VALUES (%s,%s,%s) ON CONFLICT (login) DO NOTHING",
            (login,password,role)
        )
    conn.commit()
    cur.close()
    conn.close()

# Inicjalizacja przy starcie
create_tables_if_not_exist()
create_default_users()

# Kolory / ikonki statusów
def status_icon(status):
    if status == "WYKONANE":
        return "✅"
    if status == "W TOKU":
        return "🟡"
    if status == "NIE WYKONANE":
        return "❌"
    return "⚪"

# Sesje
def is_logged():
    return "user" in session

def current_user():
    return session.get("user")

# Logowanie
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
            session["user"] = user["login"]
            session["role"] = user["role"]
            if user["role"]=="admin":
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

# Panel admina
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
                    (client,address,date_input,"DO REALIZACJI",driver.lower()))
        conn.commit()
        return redirect("/admin")
    cur.execute("SELECT * FROM orders ORDER BY date DESC")
    orders = cur.fetchall()
    cur.close()
    conn.close()

    html = f"""
    <body style='background:#f4f6f9;font-family:Arial;padding:30px'>
    <h2>📋 Panel Admin</h2>
    Zalogowany: {current_user().capitalize()} | <a href='/logout'>Wyloguj</a><br><br>

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
            <option>Leszek</option>
            <option>Tadeusz</option>
            <option>Marcel</option>
            <option>Dyzio</option>
            <option>Emil</option>
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
            <b>{status_icon(z['status'])} {z['client']}</b> | {z['address']} | {z['date']}<br>
            Kierowca: {z['driver'].capitalize()}<br>
            Status: {z['status']} | Ilość: {z['quantity']} m³ | Płatność: {z['payment']} | Kwota: {z['amount']}<br>
            Notatki: {z['notes']} | Powód: {z['reason']}
        </div>
        """
    html += "</body>"
    return html

# Panel kierowcy
@app.route("/driver", methods=["GET","POST"])
def driver():
    if not is_logged() or session["role"]!="driver":
        return redirect("/")
    user = current_user().capitalize()
    conn = get_db()
    cur = conn.cursor()
    if request.method=="POST":
        order_id = int(request.form["order"])
        cur.execute("""UPDATE orders
                       SET status=%s, quantity=%s, payment=%s, amount=%s, notes=%s, reason=%s
                       WHERE id=%s AND driver=%s""",
                    (request.form["status"], request.form["quantity"], request.form["payment"],
                     request.form["amount"], request.form["notes"], request.form["reason"],
                     order_id, user.lower()))
        conn.commit()
        return redirect("/driver")
    cur.execute("SELECT * FROM orders WHERE driver=%s ORDER BY date DESC", (user.lower(),))
    orders = cur.fetchall()
    cur.close()
    conn.close()

    html = f"""
    <body style='background:#f4f6f9;font-family:Arial;padding:30px'>
    <h2>🚛 Panel Kierowcy</h2>
    Zalogowany: {user} | <a href='/logout'>Wyloguj</a><br><br>
    """

    for z in orders:
        icon = status_icon(z['status'])
        html += f"""
        <form method='post' style='background:white;padding:20px;margin-bottom:20px;border-radius:10px'>
            <b>{icon} {z['client']}</b><br>
            {z['address']} | {z['date']}<br><br>

            <input type='hidden' name='order' value='{z['id']}'>

            Status:<br>
            <select name="status" style='width:100%;padding:10px;margin-bottom:10px'>
                <option value="W TOKU" {"selected" if z['status']=="W TOKU" else ""}>🟡 W TOKU</option>
                <option value="WYKONANE" {"selected" if z['status']=="WYKONANE" else ""}>✅ WYKONANE</option>
                <option value="NIE WYKONANE" {"selected" if z['status']=="NIE WYKONANE" else ""}>❌ NIE WYKONANE</option>
            </select>

            Powód (tylko jeśli NIE WYKONANE):<br>
            <select name="reason" style='width:100%;padding:10px;margin-bottom:10px'>
                <option value="">-</option>
                <option value="brak dojazdu" {"selected" if z['reason']=="brak dojazdu" else ""}>Brak dojazdu</option>
                <option value="inny termin" {"selected" if z['reason']=="inny termin" else ""}>Inny termin</option>
            </select>

            Ilość (m³):<br>
            <input name='quantity' value='{z['quantity'] or ""}' style='width:100%;padding:10px;margin-bottom:10px'>

            Płatność:<br>
            <select name='payment' style='width:100%;padding:10px;margin-bottom:10px'>
                <option value="Gotówka" {"selected" if z['payment']=="Gotówka" else ""}>Gotówka</option>
                <option value="Przelew" {"selected" if z['payment']=="Przelew" else ""}>Przelew</option>
            </select>

            Kwota:<br>
            <input name='amount' value='{z['amount'] or ""}' style='width:100%;padding:10px;margin-bottom:10px'>

            Notatki:<br>
            <input name='notes' value='{z['notes'] or ""}' style='width:100%;padding:10px;margin-bottom:20px'>

            <button type='submit' style='width:100%;padding:12px;background:#2196f3;color:white;border:none;border-radius:6px'>
                Zaktualizuj zlecenie
            </button>
        </form>
        """
    html += "</body>"
    return html

if __name__=="__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
