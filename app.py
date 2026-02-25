from flask import Flask, request, redirect
from datetime import date
import os

app = Flask(__name__)

kierowcy = ["Jan", "Piotr", "Marek", "Anna"]

zlecenia = [
    {"id": 1, "klient": "Firma XYZ", "adres": "ul. A 1",
     "data": str(date.today()), "status": "DO REALIZACJI",
     "kierowca": None, "masa": None, "platnosc": None,
     "kwota": None, "notatki": ""}
]

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
    <body style='background:#111;color:white;font-family:Arial;text-align:center;padding:40px'>
        <h1>🚛 EkoTrans System</h1>
        <br>
        <a href='/admin' style='padding:15px 30px;background:#4caf50;color:white;text-decoration:none;border-radius:8px;font-size:18px'>Panel Admin</a>
        <br><br>
        <a href='/kierowca' style='padding:15px 30px;background:#2196f3;color:white;text-decoration:none;border-radius:8px;font-size:18px'>Panel Kierowcy</a>
    </body>
    """

@app.route("/admin")
def admin():
    html = """
    <body style='background:#111;color:white;font-family:Arial;padding:20px'>
    <h2>📋 Panel Admin</h2>
    <a href='/' style='color:#4caf50'>⬅ Powrót</a><br><br>
    """

    for z in zlecenia:
        html += f"""
        <div style='background:#1e1e1e;padding:20px;margin-bottom:20px;border-radius:12px'>
            <h3>{z['klient']}</h3>
            <p>{z['adres']}</p>
            <p>Status: <span style='color:{status_color(z['status'])}'><b>{z['status']}</b></span></p>
            <p>Kierowca: {z['kierowca']}</p>
            <p>Masa: {z['masa']} m³</p>
            <p>Płatność: {z['platnosc']}</p>
            <p>Kwota: {z['kwota']}</p>
            <p>Notatki: {z['notatki']}</p>
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
    <body style='background:#111;color:white;font-family:Arial;padding:20px'>
    <h2>🚛 Panel Kierowcy</h2>
    <a href='/' style='color:#4caf50'>⬅ Powrót</a><br><br>
    """

    for z in zlecenia:
        html += f"""
        <form method='post' style='background:#1e1e1e;padding:20px;margin-bottom:20px;border-radius:12px'>
            <h3>{z['klient']}</h3>
            <p>{z['adres']}</p>
            <p>Status: <span style='color:{status_color(z['status'])}'>{z['status']}</span></p>

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

            <button type='submit' style='width:100%;padding:15px;background:#4caf50;color:white;border:none;border-radius:8px;font-size:16px'>
                Zakończ zlecenie
            </button>
        </form>
        """

    html += "</body>"
    return html

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
