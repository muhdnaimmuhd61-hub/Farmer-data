from flask import Flask, render_template_string, request, Response, redirect, url_for
import sqlite3
import csv
import io
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# === Upload configuration ===
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            phone TEXT,
            farmer_photo TEXT,
            farm_photo TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# === Registration form template ===
template = """
<!DOCTYPE html>
<html lang="ha">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Farmers Data App</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #f0f2f5; padding: 20px; font-family: Arial, sans-serif; }
        .card { max-width: 600px; margin: auto; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); background: white; }
        input, select, button { width: 100%; padding: 10px; margin-top: 8px; border-radius: 5px; border: 1px solid #ccc; }
        button { background: #10B981; color: white; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h2>{{ 'Farmers Registration Form' if lang=='en' else 'Fom ɗin Rijistar Manoma' }}</h2>
        <form method="POST" enctype="multipart/form-data">
            <label>{{ 'Full Name' if lang=='en' else 'Cikakken Suna' }}</label>
            <input type="text" name="name" required>

            <label>{{ 'Farming Location' if lang=='en' else 'Wurin Noma' }}</label>
            <input type="text" name="location" required>

            <label>{{ 'Type of Crop' if lang=='en' else 'Irin Amfanin Gona' }}</label>
            <input type="text" name="crop" required>

            <label>{{ 'Phone Number' if lang=='en' else 'Lambar Waya' }}</label>
            <input type="text" name="phone" required>

            <label>{{ 'Farmer Photo' if lang=='en' else 'Hoton Manomi' }}</label>
            <input type="file" name="farmer_photo" required>

            <label>{{ 'Farm Photo' if lang=='en' else 'Hoton Gona' }}</label>
            <input type="file" name="farm_photo" required>

            <button type="submit">{{ 'Submit' if lang=='en' else 'Tura' }}</button>
        </form>
        <p class="mt-3">
            🌐 <a href="/?lang=en">English</a> | <a href="/?lang=ha">Hausa</a>
        </p>

        {% if success %}
            <p style="color: green;">{{ 'Data saved successfully!' if lang=='en' else 'An adana bayananka cikin nasara!' }}</p>
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

        # Save farmer photo
        f_photo = request.files["farmer_photo"]
        f_filename = secure_filename(f_photo.filename)
        f_path = os.path.join(app.config['UPLOAD_FOLDER'], f_filename)
        f_photo.save(f_path)

        # Save farm photo
        farm_photo = request.files["farm_photo"]
        farm_filename = secure_filename(farm_photo.filename)
        farm_path = os.path.join(app.config['UPLOAD_FOLDER'], farm_filename)
        farm_photo.save(farm_path)

        conn = sqlite3.connect('farmers.db')
        c = conn.cursor()
        c.execute("INSERT INTO farmers (name, location, crop, phone, farmer_photo, farm_photo) VALUES (?, ?, ?, ?, ?, ?)",
                  (name, location, crop, phone, f_filename, farm_filename))
        conn.commit()
        conn.close()
        success = True

    return render_template_string(template, lang=lang, success=success)

# === Admin Dashboard ===
@app.route("/admin")
def admin():
    lang = request.args.get("lang", "ha")
    conn = sqlite3.connect('farmers.db')
    c = conn.cursor()
    c.execute("SELECT id, name, location, crop, phone, farmer_photo, farm_photo FROM farmers")
    farmers = c.fetchall()
    conn.close()

    dashboard_template = """
<!DOCTYPE html>
<html lang="ha">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ 'Admin Dashboard' if lang=='en' else 'Dashbod ɗin Admin' }}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body { background-color: #f0f2f5; padding: 20px; font-family: Arial, sans-serif; }
.card { padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); background: white; }
.table thead { background-color: #1E3A8A; color: white; }
.table-hover tbody tr:hover { background-color: #e0f7fa; }
.btn-download { background-color: #10B981; color: white; font-weight: bold; }
#searchInput { margin-bottom: 15px; }
th { cursor: pointer; }
img { max-width: 80px; border-radius: 5px; }
</style>
</head>
<body>
<div class="container">
<div class="d-flex justify-content-between align-items-center mb-4 flex-wrap">
<h2>{{ 'Admin Dashboard' if lang=='en' else 'Dashbod ɗin Admin' }}</h2>
<p class="mb-0">
🌐 <a href="/admin?lang=en">English</a> | <a href="/admin?lang=ha">Hausa</a>
</p>
</div>

<div class="d-flex justify-content-between mb-3 flex-wrap gap-2">
<a href="/download" class="btn btn-download">{{ 'Download CSV' if lang=='en' else 'Sauke CSV' }}</a>
<input type="text" id="searchInput" class="form-control flex-grow-1" placeholder="{{ 'Search by Name, Location, or Crop' if lang=='en' else 'Bincika da Suna, Wuri, ko Amfanin Gona' }}">
</div>

<div class="card table-responsive">
<table class="table table-striped table-hover" id="farmersTable">
<thead>
<tr>
<th onclick="sortTable(0)">ID</th>
<th onclick="sortTable(1)">{{ 'Name' if lang=='en' else 'Suna' }}</th>
<th onclick="sortTable(2)">{{ 'Location' if lang=='en' else 'Wuri' }}</th>
<th onclick="sortTable(3)">{{ 'Crop' if lang=='en' else 'Amfanin Gona' }}</th>
<th onclick="sortTable(4)">{{ 'Phone' if lang=='en' else 'Waya' }}</th>
<th>{{ 'Farmer Photo' if lang=='en' else 'Hoton Manomi' }}</th>
<th>{{ 'Farm Photo' if lang=='en' else 'Hoton Gona' }}</th>
</tr>
</thead>
<tbody>
{% for f in farmers %}
<tr>
<td>{{ f[0] }}</td>
<td>{{ f[1] }}</td>
<td>{{ f[2] }}</td>
<td>{{ f[3] }}</td>
<td>{{ f[4] }}</td>
<td><img src="/uploads/{{ f[5] }}"></td>
<td><img src="/uploads/{{ f[6] }}"></td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
// Search/filter
const searchInput = document.getElementById('searchInput');
const table = document.getElementById('farmersTable').getElementsByTagName('tbody')[0];

searchInput.addEventListener('keyup', function() {
const filter = searchInput.value.toLowerCase();
const rows = table.getElementsByTagName('tr');
for (let i = 0; i < rows.length; i++) {
    const cells = rows[i].getElementsByTagName('td');
    let match = false;
    for (let j = 1; j <= 3; j++) { // Name, Location, Crop
        if (cells[j].innerText.toLowerCase().indexOf(filter) > -1) {
            match = true;
            break;
        }
    }
    rows[i].style.display = match ? '' : 'none';
}
});

// Sort columns
function sortTable(n) {
let table = document.getElementById("farmersTable");
let switching = true;
let dir = "asc";
while (switching) {
    switching = false;
    let rows = table.rows;
    for (let i = 1; i < (rows.length - 1); i++) {
        let shouldSwitch = false;
        let x = rows[i].getElementsByTagName("TD")[n];
        let y = rows[i + 1].getElementsByTagName("TD")[n];
        if (dir=="asc") {
            if (x.innerText.toLowerCase() > y.innerText.toLowerCase()) {shouldSwitch=true; break;}
        } else if (dir=="desc") {
            if (x.innerText.toLowerCase() < y.innerText.toLowerCase()) {shouldSwitch=true; break;}
        }
    }
    if (shouldSwitch) {
        rows[i].parentNode.insertBefore(rows[i+1], rows[i]);
        switching=true;
    } else {
        if (dir=="asc") {dir="desc"; switching=true;}
    }
}
}
</script>
</body>
</html>
"""
    return render_template_string(dashboard_template, lang=lang, farmers=farmers)

# === Serve uploads folder ===
from flask import send_from_directory
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# === Download CSV route ===
@app.route("/download")
def download_csv():
    conn = sqlite3.connect('farmers.db')
    c = conn.cursor()
    c.execute("SELECT id, name, location, crop, phone FROM farmers")
    farmers = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Location', 'Crop', 'Phone'])
    writer.writerows(farmers)

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers["Content-Disposition"] = "attachment; filename=farmers_data.csv"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
