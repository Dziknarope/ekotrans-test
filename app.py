from flask import Flask, request, redirect, session from datetime import date, datetime, timedelta import os import psycopg2 import psycopg2.extras

app = Flask(name) app.secret_key = "supersecretkey"

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
    reason TEXT,
    time_of_day TEXT
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

def create_users(): conn = db() cur = conn.cursor() users = [ ("admin","Turcja123","admin"), ("leszek","LKR18456","driver"), ("tadeusz","LKR54VN","driver"), ("marcel","LKR61886","driver"), ("dyzio","LKR40306","driver"), ("emil","Turcja123","driver") ] for u in users: cur.execute("INSERT INTO users (login,password,role) VALUES (%s,%s,%s) ON CONFLICT (login) DO NOTHING", u) conn.commit() cur.close() conn.close()

init_db() create_users()

=====================

POMOCNICZE

=====================

def is_admin(): return session.get("role") == "admin"

def is_driver(): return session.get("role") == "driver"

def status_color(status): colors = { "DO REALIZACJI":"#cce5ff", "W TOKU":"#fff3cd", "NIE WYKONANE":"#f8d7da", "WYKONANE":"#d4edda" } return colors.get(status,"#ffffff")

def sidebar(active=''): options = [ ('/admin','Nowe zlecenie'), ('/admin/active','Aktywne'), ('/admin/done','Wykonane'), ('/admin/routes','Trasówki') ] html = "<div style='width:220px;background:#b2dfdb;height:100vh;float:left;padding:20px'>" html += "<h3>ADMIN</h3>" for link,label in options: style = 'padding:8px;display:block;margin:5px 0;border-radius:6px;background:#80cbc4;' if link==active else 'padding:8px;display:block;margin:5px 0;' html += f"<a href='{link}' style='{style} text-decoration:none;color:black'>{label}</a>" html += "<br><a href='/logout' style='color:red'>Wyloguj</a></div>" return html

=====================

LOGIN

=====================

@app.route('/', methods=['GET','POST']) def login(): if request.method=='POST': conn=db() cur=conn.cursor() cur.execute("SELECT * FROM users WHERE login=%s AND password=%s", (request.form['login'], request.form['password'])) user=cur.fetchone() cur.close(); conn.close() if user: session['user'] = user['login'] session['role'] = user['role'] return redirect('/admin' if user['role']=='admin' else '/driver') return """ <h2>Logowanie</h2> <form method='post'> Login:<br><input name='login'><br> Haslo:<br><input type='password' name='password'><br><br> <button>Zaloguj</button> </form> """

@app.route('/logout') def logout(): session.clear() return redirect('/')

=====================

ADMIN – NOWE ZLECENIE

=====================

@app.route('/admin', methods=['GET','POST']) def admin_new(): if not is_admin(): return redirect('/')

conn=db()
cur=conn.cursor()
cur.execute("SELECT login FROM users WHERE role='driver'")
drivers=[d['login'] for d in cur.fetchall()]
cur.close(); conn.close()

times_of_day = ['Rano','Po 15:00','Wieczor']

if request.method=='POST':
    conn=db(); cur=conn.cursor()
    cur.execute("INSERT INTO orders (client,address,date,status,driver,time_of_day) VALUES (%s,%s,%s,'DO REALIZACJI',%s,%s)",(
        request.form['client'], request.form['address'], request.form['date'], request.form['driver'], request.form['time_of_day']
    ))
    conn.commit(); cur.close(); conn.close()
    return redirect('/admin')

html=sidebar('/admin')+"<div style='margin-left:250px;padding:20px'><h2>Dodaj nowe zlecenie</h2><form method='post'>"
html+="Client:<br><input name='client'><br>Address:<br><input name='address'><br>Date:<br><input type='date' name='date' value='{0}'><br>Time of day:<br>".format(date.today())
html+="<select name='time_of_day'>"+"".join([f"<option>{t}</option>" for t in times_of_day]) + "</select><br>Driver:<br>"
html+="<select name='driver'>"+"".join([f"<option>{d}</option>" for d in drivers]) + "</select><br><br><button>Add</button></form></div>"
return html

=====================

ADMIN – AKTYWNE

=====================

@app.route('/admin/active', methods=['GET','POST']) def admin_active(): if not is_admin(): return redirect('/') conn=db(); cur=conn.cursor() if request.method=='POST': cur.execute("UPDATE orders SET status=%s, driver=%s, time_of_day=%s WHERE id=%s", (request.form['status'], request.form['driver'], request.form['time_of_day'], request.form['id'])) conn.commit() cur.execute("SELECT * FROM orders WHERE status!='WYKONANE' ORDER BY date, driver, time_of_day") orders=cur.fetchall(); cur.close(); conn.close()

html=sidebar('/admin/active')+"<div style='margin-left:250px;padding:20px'><h2>Aktywne</h2>"
for o in orders:
    html+=f"""
    <form method='post' style='background:{status_color(o['status'])};padding:10px;margin:10px;border-radius:6px'>
    <b>{o['client']}</b><br>{o['address']} | {o['date']}<br>
    Driver:<select name='driver'><option>{o['driver']}</option></select><br>
    Time of day:<select name='time_of_day'><option>{o['time_of_day']}</option></select><br>
    Status:<select name='status'>
    <option {'selected' if o['status']=='DO REALIZACJI' else ''}>DO REALIZACJI</option>
    <option {'selected' if o['status']=='W TOKU' else ''}>W TOKU</option>
    <option {'selected' if o['status']=='NIE WYKONANE' else ''}>NIE WYKONANE</option>
    <option {'selected' if o['status']=='WYKONANE' else ''}>WYKONANE</option>
    </select>
    <input type='hidden' name='id' value='{o['id']}'>
    <button>Save</button>
    </form>
    """
return html+"</div>"

=====================

ADMIN – WYKONANE

=====================

@app.route('/admin/done') def admin_done(): if not is_admin(): return redirect('/') conn=db(); cur=conn.cursor() cur.execute("SELECT * FROM orders WHERE status='WYKONANE' ORDER BY date DESC") orders=cur.fetchall(); cur.close(); conn.close()

html=sidebar('/admin/done')+"<div style='margin-left:250px;padding:20px'><h2>Wykonane</h2>"
for o in orders:
    html+=f"<div style='background:{status_color(o['status'])};padding:10px;margin:10px'>{o['date']} | {o['driver']} | {o['client']} | {o['address']} | {o['quantity']} m3 | {o['amount']}</div>"
return html+"</div>"

=====================

ADMIN – TRASÓWKI

=====================

@app.route('/admin/routes') def admin_routes(): if not is_admin(): return redirect('/') conn=db(); cur=conn.cursor() cur.execute("SELECT DISTINCT driver,date FROM orders ORDER BY date DESC") routes=cur.fetchall(); cur.close(); conn.close()

html=sidebar('/admin/routes')+"<div style='margin-left:250px;padding:20px'><h2>Trasówki</h2>"
for r in routes:
    html+=f"<a href='/admin/route/{r['driver']}/{r['date']}'>{r['driver']} | {r['date']}</a><br>"
return html+"</div>"

@app.route('/admin/route/<driver>/<rdate>') def admin_route_detail(driver,rdate): if not is_admin(): return redirect('/') conn=db(); cur=conn.cursor() cur.execute("SELECT * FROM orders WHERE driver=%s AND date=%s ORDER BY time_of_day",(driver,rdate)) orders=cur.fetchall() cur.close(); conn.close()

html=sidebar()+f"<div style='margin-left:250px;padding:20px'><h2>Trasa {driver} | {rdate}</h2>"
for o in orders:
    html+=f"{o['time_of_day']} - {o['client']} | {o['address']} | {o.get('quantity','')} m3 | {o.get('amount','')}<br>"
return html+"</div>"

=====================

PANEL KIEROWCY

=====================

@app.route('/driver', methods=['GET','POST']) def driver_panel(): if not is_driver(): return redirect('/') user=session['user']; today=date.today() conn=db(); cur=conn.cursor()

cur.execute("SELECT * FROM driver_days WHERE driver=%s AND date=%s",(user,today))
day=cur.fetchone()

if request.method=='POST' and 'close_day' in request.form:
    if not day:
        cur.execute("INSERT INTO driver_days (driver,date,closed,end_time) VALUES (%s,%s,TRUE,%s)",(user,today,datetime.now()))
    else:
        cur.execute("UPDATE driver_days SET closed=TRUE,end_time=%s WHERE driver=%s AND date=%s",(datetime.now(),user,today))
    conn.commit()

cur.execute("SELECT * FROM orders WHERE driver=%s AND date=%s ORDER BY time_of_day",(user,today))
orders=cur.fetchall(); cur.close(); conn.close()

html=f"<h2>Panel dzienny | {user.capitalize()} | {today}</h2>"
if day and day['closed']:
    html+="<b style='color:red'>DZIEŃ ZAMKNIĘTY</b><br>"

for o in orders:
    html+=f"""
    <form method='post' style='background:{status_color(o['status'])};padding:10px;margin:10px;border-radius:6px'>
    <b>{o['client']}</b><br>{o['address']}<br>
    Status:<select name='status'>
    <option {'selected' if o['status']=='W TOKU' else ''}>W TOKU</option>
    <option {'selected' if o['status']=='WYKONANE' else ''}>WYKONANE</option>
    <option {'selected' if o['status']=='NIE WYKONANE' else ''}>NIE WYKONANE</option>
    </select><br>
    Ilość:<input name='quantity' value='{o['quantity'] or ''}'><br>
    Kwota:<input name='amount' value='{o['amount'] or ''}'><br>
    Notatki:<input name='notes' value='{o['notes'] or ''}'><br>
    Forma platnosci:<select name='payment'>
        <option {'selected' if o.get('payment')=='Gotowka' else ''}>Gotowka</option>
        <option {'selected' if o.get('payment')=='Przelew' else ''}>Przelew</option>
    </select><br>
    <input type='hidden' name='id' value='{o['id']}'>
    <button name='update_order'>Zapisz</button>
    </form>
    """

if not (day and day['closed']):
    html+="<form method='post'><button name='close_day'>Zakoncz dzien</button></form>"

html+="<br><a href='/logout'>Wyloguj</a>"
return html

if name=='main': app.run(host='0.0.0.0', port=10000)
