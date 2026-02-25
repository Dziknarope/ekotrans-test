from flask import Flask, request, redirect
from datetime import date
import os

app = Flask(__name__)

kierowcy = ["Jan", "Piotr", "Marek", "Anna"]

zlecenia = []

def status_color(status):
    if status == "DO REALIZACJI":
        return "#ff9800"
    if status == "W TOKU":
        return "#2196f3"
    if status == "WYKONANE":
        return "#4caf50"
    return "#999"

@app.route("/")
def home():
    return """
    <body style='background:#f4f6f9;font-family:Arial;text-align:center;padding:40px'>
        <h1>🚛 EkoTrans System</h1>
        <br>
        <a href='/admin' style='padding:15px 30px;background:#4caf50;color:white;text-decoration:none;border-radius:8px;font-size:18px'>Panel Admin</a>
        <br><br>
        <a href='/kierowca' style='padding:15px 30px;background:#2196f3;color:white;text-decoration:none;border-radius:8px;font-size:18px'>Panel Kierowcy</a>
    </body>
    """

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        nowe = {
            "id": len(zlecenia) + 1,
            "klient": request.form["klient"],
            "adres": request.form["adres"],
            "data": request.form["data"],
            "priorytet": request.form["priorytet"],
            "godziny": request.form["godziny"],
            "status": "DO REALIZACJI",
            "kierowca": None,
            "masa": None,
            "platnosc": None,
            "kwota": None,
            "notatki": ""
        }
        zlecenia.append(nowe)
        return redirect("/admin")

    html = """
    <body style='background:#f4f6f9;font-family:Arial;padding:30px'>
    <h2>📋 Panel Admin</h2>
    <a href='/'>⬅ Powrót</a>
    <h3>➕ Dodaj nowe zlecenie</h3>
    <form method='post' style='background:white;padding:20px;border-radius:10px;margin-bottom:30px'>
        Klient:<br>
        <input name='klient' style='width:100%;padding:10px;margin-bottom:10px'>
        Adres:<br>
        <input name='adres' style='width:100%;padding:10px;margin-bottom:10px'>
        Data:<br>
        <input type='date' name='data' value='""" + str(date.today()) + """' style='width:100%;padding:10px;margin-bottom:10px'>
        Priorytet:<br>
        <select name='priorytet' style='width:100%;padding:10px;margin-bottom:10px'>
            <option>Normalne</option>
            <option>PILNE</option>
        </select>
        Godziny odbioru:<br>
        <input name='godziny' placeholder='np. 8:00-12:00 lub RANO' style='width:100%;padding:10px;margin-bottom:20px'>
        <button type='submit' style='padding:12px 20px;background:#4caf50;color:white;border:none;border-radius:6px'>
            Dodaj zlecenie
        </button>
    </form>
    <h3>📦 Lista zleceń</h3>
    """

    for z in zlecenia:
        html += f"""
        <div style='background:white;padding:20px;margin-bottom:15px;border-radius:10px'>
            <b>{z['klient']}</b><br>
            {z['adres']}<br>
            Data: {z['data']}<br>
            Priorytet: {z['priorytet']}<br>
            Godziny: {z['godziny']}<br>
            Status: <span style='color:{status_color(z['status'])}'><b>{z['status']}</b></span><br>
            Kierowca: {z['kierowca']}<br>
            Masa: {z['masa']} m³<br>
            Płatność: {z['platnosc']}<br>
            Kwota: {z['kwota']}<br>
            Notatki: {z['notatki']}
        </div>
        """

    html += "</body>"
    return html

@app.route("/kierowca", methods=["GET", "POST"])
def kierowca():
    if request.method == "POST":
        z_id = int(request.form["zlecenie"])
        for z in zlecenia:
            if z["id"] == z_id:
                z["status"] = "WYKONANE"
                z["masa"] = request.form["masa"]
                z["platnosc"] = request.form["platnosc"]
                z["kwota"] = request.form["kwota"]
                z["notatki"] = request.form["notatki"]
                z["kierowca"] = request.form["kierowca"]
        return redirect("/kierowca")

    html = """
    <body style='background:#f4f6f9;font-family:Arial;padding:30px'>
    <h2>🚛 Panel Kierowcy</h2>
    <a href='/'>⬅ Powrót</a><br><br>
    """

    for z in zlecenia:
        html += f"""
        <form method='post' style='background:white;padding:20px;margin-bottom:20px;border-radius:10px'>
            <b>{z['klient']}</b><br>
            {z['adres']}<br>
            Data: {z['data']}<br>
            Priorytet: {z['priorytet']}<br>
            Godziny: {z['godziny']}<br>
            Status: <span style='color:{status_color(z['status'])}'>{z['status']}</span><br><br>

            <input type='hidden' name='zlecenie' value='{z['id']}'>

            Kierowca:<br>
            <select name='kierowca' style='width:100%;padding:10px;margin-bottom:10px'>
                {''.join([f"<option>{k}</option>" for k in kierowcy])}
            </select>

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
