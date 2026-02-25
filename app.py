from flask import Flask, request, redirect, session
from datetime import date
import os

app = Flask(__name__)
app.secret_key = "supersekretnyklucz123"

# Użytkownicy
users = {
    "admin": {"password": "Turcja123", "role": "admin"},
    "leszek": {"password": "LKR18456", "role": "driver"},
    "tadeusz": {"password": "LKR54VN", "role": "driver"},
    "marcel": {"password": "LKR61886", "role": "driver"},
    "dyzio": {"password": "LKR40306", "role": "driver"},
    "emil": {"password": "Turcja123", "role": "driver"},
}

zlecenia = []

def is_logged():
    return "user" in session

def current_user():
    return session.get("user")

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login = request.form["login"]
        password = request.form["password"]

        if login in users and users[login]["password"] == password:
            session["user"] = login
            session["role"] = users[login]["role"]
            if users[login]["role"] == "admin":
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

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not is_logged() or session["role"] != "admin":
        return redirect("/")

    if request.method == "POST":
        nowe = {
            "id": len(zlecenia) + 1,
            "klient": request.form["klient"],
            "adres": request.form["adres"],
            "data": request.form["data"],
            "status": "DO REALIZACJI",
            "kierowca": request.form["kierowca"],
            "masa": None,
            "platnosc": None,
            "kwota": None,
            "notatki": ""
        }
        zlecenia.append(nowe)
        return redirect("/admin")

    html = f"""
    <body style='background:#f4f6f9;font-family:Arial;padding:30px'>
    <h2>📋 Panel Admin</h2>
    Zalogowany: {current_user()} | <a href='/logout'>Wyloguj</a><br><br>

    <h3>➕ Nowe zlecenie</h3>
    <form method='post' style='background:white;padding:20px;border-radius:10px;margin-bottom:30px'>
        Klient:<br>
        <input name='klient' style='width:100%;padding:10px;margin-bottom:10px'>
        Adres:<br>
        <input name='adres' style='width:100%;padding:10px;margin-bottom:10px'>
        Data:<br>
        <input type='date' name='data' value='{str(date.today())}' style='width:100%;padding:10px;margin-bottom:10px'>
        Kierowca:<br>
        <select name='kierowca' style='width:100%;padding:10px;margin-bottom:20px'>
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

    for z in zlecenia:
        html += f"""
        <div style='background:white;padding:15px;margin-bottom:10px;border-radius:8px'>
            <b>{z['klient']}</b> | {z['adres']} | {z['data']}<br>
            Kierowca: {z['kierowca']}<br>
            Status: {z['status']}<br>
            Masa: {z['masa']} m³ | Płatność: {z['platnosc']} | Kwota: {z['kwota']}
        </div>
        """

    html += "</body>"
    return html

@app.route("/driver", methods=["GET", "POST"])
def driver():
    if not is_logged() or session["role"] != "driver":
        return redirect("/")

    user = current_user()

    if request.method == "POST":
        z_id = int(request.form["zlecenie"])
        for z in zlecenia:
            if z["id"] == z_id and z["kierowca"] == user:
                z["status"] = "WYKONANE"
                z["masa"] = request.form["masa"]
                z["platnosc"] = request.form["platnosc"]
                z["kwota"] = request.form["kwota"]
                z["notatki"] = request.form["notatki"]
        return redirect("/driver")

    html = f"""
    <body style='background:#f4f6f9;font-family:Arial;padding:30px'>
    <h2>🚛 Panel Kierowcy</h2>
    Zalogowany: {user} | <a href='/logout'>Wyloguj</a><br><br>
    """

    for z in zlecenia:
        if z["kierowca"] == user:
            html += f"""
            <form method='post' style='background:white;padding:20px;margin-bottom:20px;border-radius:10px'>
                <b>{z['klient']}</b><br>
                {z['adres']} | {z['data']}<br>
                Status: {z['status']}<br><br>

                <input type='hidden' name='zlecenie' value='{z['id']}'>

                Masa (m³):<br>
                <input name='masa' style='width:100%;padding:10px;margin-bottom:10px'>

                Płatność:<br>
                <select name='platnosc' style='width:100%;padding:10px;margin-bottom:10px'>
                    <option>Gotówka</option>
                    <option>Przelew</option>
                </select>

                Kwota:<br>
                <input name='kwota' style='width:100%;padding:10px;margin-bottom:10px'>

                Notatki:<br>
                <input name='notatki' style='width:100%;padding:10px;margin-bottom:20px'>

                <button type='submit' style='width:100%;padding:12px;background:#2196f3;color:white;border:none;border-radius:6px'>
                    Zakończ zlecenie
                </button>
            </form>
            """

    html += "</body>"
    return html

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
