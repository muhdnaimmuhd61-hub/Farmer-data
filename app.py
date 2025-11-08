from flask import Flask, render_template_string, request
import sqlite3

app = Flask(__name__)

# === Create database automatically ===
def init_db():
    conn = sqlite3.connect('farmers.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            location TEXT,
            crop TEXT,
            phone TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# === HTML template (Hausa & English) ===
template = """
<!DOCTYPE html>
<html lang="ha">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Farmers Data App</title>
    <style>
        body { font-family: Arial; background: #f5f5f5; padding: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; max-width: 400px; margin: auto; box-shadow: 0 0 10px #ccc; }
        input, select, button { width: 100%; padding: 10px; margin-top: 8px; border-radius: 5px; border: 1px solid #ccc; }
        button { background: green; color: white; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h2>{{ 'Farmers Registration Form' if lang == 'en' else 'Fom ɗin Rijistar Manoma' }}</h2>
        <form method="POST">
            <label>{{ 'Full Name' if lang == 'en' else 'Cikakken Suna' }}</label>
            <input type="text" name="name" required>

            <label>{{ 'Farming Location' if lang == 'en' else 'Wurin Noma' }}</label>
            <input type="text" name="location" required>

            <label>{{ 'Type of Crop' if lang == 'en' else 'Irin Amfanin Gona' }}</label>
            <input type="text" name="crop" required>

            <label>{{ 'Phone Number' if lang == 'en' else 'Lambar Waya' }}</label>
            <input type="text" name="phone" required>

            <button type="submit">{{ 'Submit' if lang == 'en' else 'Tura' }}</button>
        </form>

        <p style="margin-top:15px;">
            🌐 <a href="/?lang=en">English</a> | <a href="/?lang=ha">Hausa</a>
        </p>

        {% if success %}
            <p style="color: green;">{{ 'Data saved successfully!' if lang == 'en' else 'An adana bayananka cikin nasara!' }}</p>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    lang = request.args.get("lang", "ha")
    success = False
    if request.method == "POST":
        name = request.form["name"]
        location = request.form["location"]
        crop = request.form["crop"]
        phone = request.form["phone"]
        conn = sqlite3.connect('farmers.db')
        c = conn.cursor()
        c.execute("INSERT INTO farmers (name, location, crop, phone) VALUES (?, ?, ?, ?)",
                  (name, location, crop, phone))
        conn.commit()
        conn.close()
        success = True
    return render_template_string(template, lang=lang, success=success)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
