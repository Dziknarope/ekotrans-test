from flask import Flask, request, redirect
from datetime import date

app = Flask(__name__)

# Lista kierowców (demo)
kierowcy = [
    {"id": 1, "imie": "Jan"},
    {"id": 2, "imie": "Piotr"},
    {"id": 3, "imie": "Marek"},
    {"id": 4, "imie": "Anna"},
]

# Demo lista zleceń
zlecenia = [
    {"id": 1, "klient": "Firma XYZ", "adres": "ul. A 1", "data": str(date.today()), 
     "status": "DO REALIZACJI", "kierowca": None, "masa": None, "platnosc": None, 
     "kwota": None, "notatki": ""},
    {"id": 2, "klient": "EcoTrans", "adres": "ul. B 2", "data": str(date.today()), 
     "status": "DO REALIZACJI", "kierowca": None, "masa": None, "platnosc": None, 
     "kwota": None, "notatki": ""},
]

@app.route("/")
def home():
    return """
    <h1>System EkoTrans</h1>
    <a href='/admin'>Panel Admin</a><br><br>
    <a href='/kierowca'>Panel Kierowcy</a>
    """

@app.route("/admin")
def admin():
    html = "<h2>Panel Admin</h2><a href='/'>Powrót</a><br><br>"
    for z in zlecenia:
        html += f"""
        <div style='border:1px solid black;padding:10px;margin:10px'>
        <b>Zlecenie ID: {z['id']}</b><br>
        Klient: {z['klient']}<br>
        Adres: {z['adres']}<br>
        Status: {z['status']}<br>
        Kierowca: {z['kierowca']}<br>
        Masa: {z['masa']} m³<br>
        Płatność: {z['platnosc']}<br>
        Kwota: {z['kwota']}<br>
        Notatki: {z['notatki']}<br>
        </div>
        """
    return html

@app.route("/kierowca", methods=["GET","POST"])
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

    html = "<h2>Panel Kierowcy</h2><a href='/'>Powrót</a><br><br>"
    for z in zlecenia:
        html += f"""
        <form method='post' style='border:1px solid black;padding:15px;margin:10px'>
        <b>{z['klient']} – {z['adres']}</b><br>
        Status: {z['status']}<br><br>
        <input type='hidden' name='zlecenie' value='{z['id']}'>
        Kierowca:<br>
        <select name='kierowca'>
            <option>Jan</option>
            <option>Piotr</option>
            <option>Marek</option>
            <option>Anna</option>
        </select><br>
        Masa (m³):<br>
        <input name='masa'><br>
        Płatność:<br>
        <select name='platnosc'>
            <option>Gotówka</option>
            <option>Przelew</option>
        </select><br>
        Kwota:<br>
        <input name='kwota'><br>
        Notatki:<br>
        <input name='notatki'><br><br>
        <button type='submit'>Zakończ zlecenie</button>
        </form>
        """
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
