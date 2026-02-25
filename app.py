from flask import Flask, request, redirect, session
from datetime import date
import os
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = "supersekretnyklucz123"
app.debug = True

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("Brak DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

# =====================================================
# INICJALIZACJA BAZY (NIC NIE USUWAMY, TYLKO DODAJEMY)
# =====================================================

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
        driver TEXT
    );
    """)

    # brakujące kolumny
    columns = {
        "quantity": "REAL",
        "payment": "TEXT",
        "amount": "REAL",
        "notes": "TEXT",
        "reason": "TEXT",
        "position": "INTEGER DEFAULT 1"
    }

    for col, typ in columns.items():
        cur.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='orders' AND column_name='{col}'
            ) THEN
                ALTER TABLE orders ADD COLUMN {col} {typ};
            END IF;
        END $$;
        """)

    conn.commit()
    cur.close()
    conn.close()

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
    for u in users:
        cur.execute("INSERT INTO users (login,password,role) VALUES (%s,%s,%s) ON CONFLICT (login) DO NOTHING", u)
    conn.commit()
    cur.close()
    conn.close()

init_db()
create_default_users()

# =====================================================
# POMOCNICZE
# =====================================================

def is_admin():
    return session.get("role") == "admin"

def is_driver():
    return session.get("role") == "driver"

def status_icon(s):
    if s == "WYKONANE": return "✅"
    if s == "W TOKU": return "🟡"
    if s == "NIE WYKONANE": return "❌"
    return "⚪"

# =====================================================
# LOGIN
# =====================================================

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE login=%s AND password=%s",
                    (request.form["login"], request.form["password"]))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            session["user"] = user["login"]
            session["role"] = user["role"]
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

# =====================================================
# ADMIN – AKTYWNE
# =====================================================

@app.route("/admin", methods=["GET","POST"])
def admin():
    if not is_admin():
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        cur.execute("""
        UPDATE orders SET
            status=%s,
            driver=%s,
            date=%s,
            position=%s
        WHERE id=%s
        """, (
            request.form["status"],
            request.form["driver"],
            request.form["date"],
            request.form["position"],
            request.form["order_id"]
        ))
        conn.commit()

    cur.execute("""
    SELECT * FROM orders
    WHERE status != 'WYKONANE'
    ORDER BY date, driver, position
    """)
    orders = cur.fetchall()
    cur.close()
    conn.close()

    html = "<h2>🔵 AKTYWNE</h2>"
    html += "<a href='/admin/done'>WYKONANE</a><br><br>"

    for z in orders:
        html += f"""
        <form method='post' style='border:1px solid gray;padding:10px;margin:10px'>
        <b>{status_icon(z['status'])} {z['client']}</b> | {z['address']}<br>
        Data: <input type='date' name='date' value='{z['date']}'>
        Kierowca: <input name='driver' value='{z['driver']}'>
        Kolejność: <input name='position' value='{z['position']}'>
        Status:
        <select name='status'>
            <option {'selected' if z['status']=="DO REALIZACJI" else ""}>DO REALIZACJI</option>
            <option {'selected' if z['status']=="W TOKU" else ""}>W TOKU</option>
            <option {'selected' if z['status']=="WYKONANE" else ""}>WYKONANE</option>
            <option {'selected' if z['status']=="NIE WYKONANE" else ""}>NIE WYKONANE</option>
        </select>
        <input type='hidden' name='order_id' value='{z['id']}'>
        <button>Zapisz</button>
        </form>
        """

    return html

# =====================================================
# ADMIN – WYKONANE
# =====================================================

@app.route("/admin/done")
def admin_done():
    if not is_admin():
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE status='WYKONANE' ORDER BY date DESC")
    orders = cur.fetchall()
    cur.close()
    conn.close()

    html = "<h2>🟢 WYKONANE</h2>"
    html += "<a href='/admin'>AKTYWNE</a><br><br>"

    for z in orders:
        html += f"{z['date']} | {z['driver']} | {z['client']}<br>"

    return html

# =====================================================
# TRASÓWKA
# =====================================================

@app.route("/route/<driver>/<route_date>")
def route(driver, route_date):
    if not is_admin():
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT * FROM orders
    WHERE driver=%s AND date=%s
    ORDER BY position
    """, (driver.lower(), route_date))
    orders = cur.fetchall()
    cur.close()
    conn.close()

    html = f"<h2>🚛 Trasa {driver.capitalize()} - {route_date}</h2>"

    for z in orders:
        html += f"{z['position']}. {z['client']} - {z['address']}<br>"

    return html

# =====================================================
# PANEL KIEROWCY
# =====================================================

@app.route("/driver", methods=["GET","POST"])
def driver_panel():
    if not is_driver():
        return redirect("/")

    user = session["user"]

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        cur.execute("""
        UPDATE orders SET
            status=%s,
            quantity=%s,
            payment=%s,
            amount=%s,
            notes=%s,
            reason=%s
        WHERE id=%s AND driver=%s
        """, (
            request.form["status"],
            request.form["quantity"],
            request.form["payment"],
            request.form["amount"],
            request.form["notes"],
            request.form["reason"],
            request.form["order_id"],
            user
        ))
        conn.commit()

    cur.execute("""
    SELECT * FROM orders
    WHERE driver=%s
    ORDER BY date, position
    """, (user,))
    orders = cur.fetchall()
    cur.close()
    conn.close()

    html = f"<h2>🚛 Panel kierowcy: {user}</h2>"

    for z in orders:
        html += f"""
        <form method='post' style='border:1px solid gray;padding:10px;margin:10px'>
        <b>{status_icon(z['status'])} {z['client']}</b><br>
        Status:
        <select name='status'>
            <option>W TOKU</option>
            <option>WYKONANE</option>
            <option>NIE WYKONANE</option>
        </select><br>
        Ilość (m³): <input name='quantity' value='{z['quantity'] or ""}'><br>
        Płatność: <input name='payment' value='{z['payment'] or ""}'><br>
        Kwota: <input name='amount' value='{z['amount'] or ""}'><br>
        Powód: <input name='reason' value='{z['reason'] or ""}'><br>
        Notatki: <input name='notes' value='{z['notes'] or ""}'><br>
        <input type='hidden' name='order_id' value='{z['id']}'>
        <button>Zapisz</button>
        </form>
        """

    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
