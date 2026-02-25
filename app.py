from flask import Flask, request, redirect, session from datetime import date, datetime import os import psycopg2 import psycopg2.extras

app = Flask(name) app.secret_key = "supersecretkey"

DATABASE_URL = os.environ.get("DATABASE_URL") if not DATABASE_URL: raise Exception("Brak DATABASE_URL")

def db(): return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

===== INIT BAZY =====

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
    time_of_day TEXT,
    quantity REAL,
    payment_type TEXT,
    amount REAL,
    notes TEXT,
    reason TEXT
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

conn.commit(); cur.close(); conn.close()

def create_users(): conn = db(); cur = conn.cursor() users = [ ("admin","Turcja123","admin"), ("leszek","LKR18456","driver"), ("tadeusz","LKR54VN","driver"), ("marcel","LKR61886","driver"), ("dyzio","LKR40306","driver"), ("emil","Turcja123","driver") ] for u in users: cur.execute("INSERT INTO users (login,password,role) VALUES (%s,%s,%s) ON CONFLICT (login) DO NOTHING", u) conn.commit(); cur.close(); conn.close()

init_db() create_users()

===== POMOCNICZE =====

def is_admin(): return session.get("role") == "admin"

def is_driver(): return session.get("role") == "driver"

def status_color(status): colors = { "DO REALIZACJI":"#cce5ff", "W TOKU":"#fff3cd", "NIE WYKONANE":"#f8d7da", "WYKONANE":"#d4edda" } return colors.get(status,"#ffffff")

def sidebar(active=''): options = [ ('/admin','+ Nowe zlecenie'), ('/admin/active','Aktywne'), ('/admin/done','Wykonane'), ('/admin/routes','Trasówki') ] html = "<div style='width:200px;background:#e0f2f1;height:100vh;float:left;padding:20px'>" html += "<h3>ADMIN</h3>" for link,label in options: style = 'padding:8px;display:block;margin:5px 0;border-radius:6px;background:#b2dfdb;' if link==active else 'padding:8px;display:block;margin:5px 0;' html += f"<a href='{link}' style='{style} text-decoration:none;color:black'>{label}</a>" html += "<br><a href='/logout' style='color:red'>Wyloguj</a></div>" return html

===== LOGIN =====

@app.route('/', methods=['GET','POST']) def login(): if request.method=='POST': conn=db(); cur=conn.cursor() cur.execute("SELECT * FROM users WHERE login=%s AND password=%s", (request.form['login'], request.form['password'])) user=cur.fetchone(); cur.close(); conn.close() if user: session['user'] = user['login'] session['role'] = user['role'] return redirect('/admin' if user['role']=='admin' else '/driver') return """ <h2>Logowanie</h2> <form method='post'> Login:<br><input name='login'><br> Haslo:<br><input type='password' name='password'><br><br> <button>Zaloguj</button> </form> """

@app.route('/logout') def logout(): session.clear() return redirect('/')

===== ADMIN – NOWE ZLECENIE =====

@app.route('/admin', methods=['GET','POST']) def admin_new(): if not is_admin(): return redirect('/')

conn=db(); cur=conn.cursor()
cur.execute("SELECT login FROM users WHERE role='driver'"); drivers=[d['login'] for d in cur.fetchall()]; cur.close(); conn.close()

if request.method=='POST':
    conn=db(); cur=conn.cursor()
    cur.execute("INSERT INTO orders (client,address,date,status,driver,time_of_day) VALUES (%s,%s,%s,'DO REALIZACJI',%s,%s)",(
        request.form['client'], request.form['address'], request.form['date'], request.form['driver'], request.form['time_of_day']
    ))
    conn.commit(); cur.close(); conn.close()
    return redirect('/admin')

times_of_day = ['Rano (7-10)','Po poludniu (15-18)','Wieczorem (19-22)']

html=sidebar('/admin')+"<div style='margin-left:220px;padding:20px'><h2>+ Dodaj nowe zlecenie</h2><form method='post'>"
html+="Klient:<br><input name='client'><br>Adres:<br><input name='address'><br>Data:<br><input type='date' name='date' value='{0}'><br>Pora dnia:<br>".format(date.today())
html+="<select name='time_of_day'>"+"".join([f"<option>{t}</option>" for t in times_of_day]) + "</select><br>Kierowca:<br>"
html+="<select name='driver'>"+"".join([f"<option>{d}</option>" for d in drivers]) + "</select><br><br><button>Dodaj</button></form></div>"
return html

===== ADMIN – WYKONANE =====

@app.route('/admin/done') def admin_done(): if not is_admin(): return redirect('/') conn=db(); cur=conn.cursor() cur.execute("SELECT * FROM orders WHERE status='WYKONANE' ORDER BY date DESC") orders=cur.fetchall(); cur.close(); conn.close()

html=sidebar('/admin/done')+"<div style='margin-left:220px;padding:20px'><h2>Wykonane</h2>"
for o in orders:
    html+=f"<div style='background:{status_color(o['status'])};padding:10px;margin:5px;border-radius:6px'>{o['client']} | {o['address']} | {o.get('quantity','')} m3 | {o.get('amount','')} zl | {o['driver']} | {o['date']}</div>"
return html+"</div>"

===== ADMIN – TRASÓWKI =====

@app.route('/admin/routes', methods=['GET','POST']) def admin_routes(): if not is_admin(): return redirect('/')

conn=db(); cur=conn.cursor()
cur.execute("SELECT login FROM users WHERE role='driver'"); drivers=[d['login'] for d in cur.fetchall()]; cur.close(); conn.close()

html=sidebar('/admin/routes')+"<div style='margin-left:220px;padding:20px'><h2>Trasowki</h2>"
html+="<h4>Wybierz kierowce:</h4>"
for d in drivers:
    html+=f"<form method='post'><button name='driver' value='{d}'>{d.capitalize()}</button></form>"

if request.method=='POST' and 'driver' in request.form:
    session['route_driver'] = request.form['driver']
    return redirect('/admin/routes/date')

html+="</div>"
return html

@app.route('/admin/routes/date', methods=['GET','POST']) def admin_routes_date(): if not is_admin() or 'route_driver' not in session: return redirect('/admin/routes') driver=session['route_driver']

html=sidebar('/admin/routes')+f"<div style='margin-left:220px;padding:20px'><h2>Trasowki {driver.capitalize()}</h2>"
html+="<form method='post'>Wybierz date: <input type='date' name='date'><button>Pokaz</button></form></div>"

if request.method=='POST' and 'date' in request.form:
    return redirect(f"/admin/route/{driver}/{request.form['date']}")
return html

@app.route('/admin/route/<driver>/<rdate>') def admin_route_detail(driver,rdate): if not is_admin(): return redirect('/') conn=db(); cur=conn.cursor() cur.execute("SELECT * FROM orders WHERE driver=%s AND date=%s ORDER BY id",(driver,rdate)) orders=cur.fetchall() cur.execute("SELECT * FROM fuel_logs WHERE driver=%s AND date=%s",(driver,rdate)) fuels=cur.fetchall() cur.execute("SELECT * FROM driver_days WHERE driver=%s AND date=%s",(driver,rdate)) day=cur.fetchone(); cur.close(); conn.close()

html=sidebar('/admin/routes')+f"<div style='margin-left:220px;padding:20px'><h2>Trasa {driver.capitalize()} | {rdate}</h2>"
if day and day['closed']:
    html+="<b style='color:red'>Dzien zamkniety</b><br>"
for o in orders:
    html+=f"{o['client']} - {o['address']} | {o.get('quantity','')} m3 | {o.get('amount','')} zl<br>"
html+="<h3>Tankowania:</h3>"
for f in fuels:
    html+=f"Licznik: {f['mileage']} | Litry: {f['liters']}<br>"
return html+"</div>"

===== PANEL KIEROWCY =====

@app.route('/driver', methods=['GET','POST']) def driver_panel(): if not is_driver(): return redirect('/') user=session['user']; today=date.today()

conn=db(); cur=conn.cursor()
cur.execute("SELECT * FROM driver_days WHERE driver=%s AND date=%s",(user,today))
day=cur.fetchone()

if request.method=='POST':
    if 'start_day' in request.form:
        if not day:
            cur.execute("INSERT INTO driver_days (driver,date,closed,start_time) VALUES (%s,%s,FALSE,%s)",(user,today,datetime.now()))
        else:
            cur.execute("UPDATE driver_days SET start_time=%s,closed=FALSE,end_time=NULL WHERE driver=%s AND date=%s",(datetime.now(),user,today))
    if 'close_day' in request.form and day and not day['closed']:
        cur.execute("UPDATE driver_days SET closed=TRUE,end_time=%s WHERE driver=%s AND date=%s",(datetime.now(),user,today))
    conn.commit()

cur.execute("SELECT * FROM orders WHERE driver=%s AND date=%s ORDER BY id",(user,today))
orders=cur.fetchall(); cur.close(); conn.close()

html=f"<h2>Panel dzienny | {user.capitalize()} | {today}</h2>"
if day and day['closed']:
    html+="<b style='color:red'>DZIEN ZAMKNIETY</b><br>"

html+="<form method='post'>"
if not day:
    html+="<button name='start_day'>START DZIEN</button>"
elif not day['closed']:
    html+="<button name='close_day'>ZAKONCZ DZIEN</button>"
html+="</form><br>"

for o in orders:
    html+=f"""
    <form method='post' style='background:{status_color(o['status'])};padding:10px;margin:5px;border-radius:6px'>
    <b>{o['client']}</b> | {o['address']}<br>
    Ilosc: <input name='quantity' value='{o.get('quantity','')}'><br>
    Kwota: <input name='amount' value='{o.get('amount','')}'><br>
    Forma platnosci:<br>
    <select name='payment_type'>
        <option {'selected' if o.get('payment_type')=='Gotowka' else ''}>Gotowka</option>
        <option {'selected' if o.get('payment_type')=='Przelew' else ''}>Przelew</option>
    </select><br>
    Status:<select name='status'>
        <option {'selected' if o['status']=='W TOKU' else ''}>W TOKU</option>
        <option {'selected' if o['status']=='WYKONANE' else ''}>WYKONANE</option>
        <option {'selected' if o['status']=='NIE WYKONANE' else ''}>NIE WYKONANE</option>
    </select><br>
    <input type='hidden' name='id' value='{o['id']}'>
    <button name='update_order'>Zapisz</button>
    </form>
    """

html+="<br><a href='/logout'>Wyloguj</a>"
return html

if name == 'main': app.run(host='0.0.0.0', port=10000)
