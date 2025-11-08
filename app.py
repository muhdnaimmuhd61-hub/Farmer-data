# app.py
from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory, jsonify, Response
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import io
import csv

app = Flask(__name__)

# -------------------------
# Configuration
# -------------------------
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
DB = 'farmers.db'

def allowed_file(filename):
    return filename and '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------------
# Initialize DB
# -------------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            state TEXT,
            lga TEXT,
            crop TEXT,
            phone TEXT,
            farmer_photo TEXT,
            farm_photo TEXT,
            date_added TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state TEXT,
            lga TEXT,
            crop TEXT,
            temperature REAL,
            rainfall REAL,
            season TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS lga_coords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state TEXT,
            lga TEXT,
            lat REAL,
            lng REAL
        )
    ''')
    conn.commit()

    # seed some sample LGAs & coords if empty (replace with real data later)
    c.execute("SELECT COUNT(*) FROM lga_coords")
    count = c.fetchone()[0]
    if count == 0:
        sample = [
            ("Lagos", "Ikeja", 6.6018, 3.3515),
            ("Lagos", "Epe", 6.5859, 3.9269),
            ("Kano", "Nassarawa", 12.0022, 8.5167),
            ("Kano", "Gwale", 11.9993, 8.5228),
            ("Rivers", "Port Harcourt", 4.8156, 7.0490),
            ("Kaduna", "Birnin Gwari", 10.5863, 6.5956)
        ]
        c.executemany("INSERT INTO lga_coords (state,lga,lat,lng) VALUES (?,?,?,?)", sample)
        conn.commit()
    conn.close()

init_db()

# helper DB query
def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(query, args)
    rv = c.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

# -------------------------
# Shared HTML pieces & translations
# -------------------------
def t(key, lang):
    # minimal translation mapping
    texts = {
        "welcome": {"en": "Welcome to Farmers Data Records", "ha": "Barka da zuwa Rijistar Bayanai na Manoma"},
        "select_state": {"en": "Select State", "ha": "Zaɓi Jihar"},
        "select_lga": {"en": "Select LGA", "ha": "Zaɓi Karamar Hukuma"},
        "go": {"en": "Go", "ha": "Je"},
        "view_map": {"en": "View Crop Distribution Map", "ha": "Duba Taswirar Noman Amfani"},
        "add_weather": {"en": "Add Weather Data", "ha": "Ƙara Bayanai na Yanayi"},
        "download_csv": {"en": "Download CSV", "ha": "Sauke CSV"},
        "total_farmers": {"en": "Total Farmers", "ha": "Jimillar Manoma"},
        "add_farmer": {"en": "Add New Farmer", "ha": "Ƙara Sabon Manomi"},
        "back": {"en": "Back", "ha": "Baya"},
        "name": {"en": "Name", "ha": "Suna"},
        "crop": {"en": "Crop", "ha": "Amfanin Gona"},
        "phone": {"en": "Phone", "ha": "Waya"},
        "farmer_photo": {"en": "Farmer Photo", "ha": "Hoton Manomi"},
        "farm_photo": {"en": "Farm Photo", "ha": "Hoton Gona"},
        "submit": {"en": "Submit", "ha": "Tura"},
        "no_weather": {"en":"No weather data yet for this LGA.", "ha":"Babu bayanan yanayi a wannan LGA har yanzu."},
        "search": {"en":"Search by Name, Crop, Phone", "ha":"Bincika da Suna, Amfani, Waya"},
        "language": {"en":"Hausa", "ha":"English"}
    }
    return texts.get(key, {}).get(lang, key)

# -------------------------
# Routes (single-file templates using render_template_string)
# -------------------------

# Home page
@app.route("/", methods=["GET","POST"])
def index():
    lang = request.args.get('lang', 'en')
    # states from lga_coords
    rows = query_db("SELECT DISTINCT state FROM lga_coords")
    states = [r[0] for r in rows] if rows else []
    lgas = []
    if request.method == "POST":
        state = request.form.get('state')
        lga = request.form.get('lga')
        if state and lga:
            return redirect(url_for('lga_summary', state=state, lga=lga, lang=lang))
    template = """
    <!doctype html>
    <html lang="{{lang}}">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{{welcome}}</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="p-4">
    <div class="container">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h1>{{welcome}}</h1>
        <div>
          <a href="/?lang={{'ha' if lang=='en' else 'en'}}" class="btn btn-outline-secondary btn-sm">{{ lang_toggle }}</a>
        </div>
      </div>

      <form method="POST" id="selectForm">
        <div class="row g-2">
          <div class="col-md-5">
            <label class="form-label">{{select_state}}</label>
            <select name="state" id="stateSelect" class="form-control" required>
              <option value="">{{select_state}}</option>
              {% for s in states %}<option value="{{s}}">{{s}}</option>{% endfor %}
            </select>
          </div>
          <div class="col-md-5">
            <label class="form-label">{{select_lga}}</label>
            <select name="lga" id="lgaSelect" class="form-control" required>
              <option value="">{{select_lga}}</option>
            </select>
          </div>
          <div class="col-md-2 d-flex align-items-end">
            <button class="btn btn-success w-100">{{go}}</button>
          </div>
        </div>
      </form>

      <hr class="my-4">

      <div class="d-flex gap-2">
        <a href="{{ url_for('map_view', lang=lang) }}" class="btn btn-primary">{{view_map}}</a>
        <a href="{{ url_for('add_weather', lang=lang) }}" class="btn btn-secondary">{{add_weather}}</a>
        <a href="{{ url_for('download_csv', lang=lang) }}" class="btn btn-info">{{download_csv}}</a>
      </div>
    </div>

    <script>
    document.getElementById('stateSelect').addEventListener('change', function(){
      const state = this.value;
      const lgaSelect = document.getElementById('lgaSelect');
      lgaSelect.innerHTML = '<option>Loading...</option>';
      if(!state){ lgaSelect.innerHTML = '<option value=\"\">{{select_lga}}</option>'; return; }
      fetch('/api/lgas/' + encodeURIComponent(state))
        .then(r => r.json())
        .then(data => {
          lgaSelect.innerHTML = '<option value=\"\">{{select_lga}}</option>';
          data.forEach(l => {
            const o = document.createElement('option'); o.value = l; o.text = l;
            lgaSelect.appendChild(o);
          });
        })
        .catch(err => { lgaSelect.innerHTML = '<option value=\"\">{{select_lga}}</option>'; });
    });
    </script>
    </body>
    </html>
    """
    return render_template_string(template,
                                  lang=lang,
                                  welcome=t("welcome", lang),
                                  select_state=t("select_state", lang),
                                  select_lga=t("select_lga", lang),
                                  go=t("go", lang),
                                  view_map=t("view_map", lang),
                                  add_weather=t("add_weather", lang),
                                  download_csv=t("download_csv", lang),
                                  lang_toggle=t("language", lang),
                                  states=states)

# API: list LGAs for a state
@app.route("/api/lgas/<state>")
def api_lgas(state):
    rows = query_db("SELECT lga FROM lga_coords WHERE state=?", (state,))
    lgas = [r[0] for r in rows]
    return jsonify(lgas)

# LGA summary page
@app.route("/lga/<state>/<lga>")
def lga_summary(state, lga):
    lang = request.args.get('lang', 'en')
    farmers = query_db("SELECT id, name, crop, phone, farmer_photo, farm_photo, date_added FROM farmers WHERE state=? AND lga=? ORDER BY date_added DESC", (state,lga))
    total = len(farmers)
    weather = query_db("SELECT crop, temperature, rainfall, season FROM weather WHERE state=? AND lga=?", (state,lga))
    coord = query_db("SELECT lat,lng FROM lga_coords WHERE state=? AND lga=?", (state,lga), one=True)
    latlng = {"lat": coord[0], "lng": coord[1]} if coord else None

    template = """
    <!doctype html>
    <html lang="{{lang}}">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{{lga}} - {{state}}</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="p-4">
    <div class="container">
      <div class="d-flex justify-content-between align-items-center">
        <h2>{{state}} → {{lga}}</h2>
        <div>
          <a href="/?lang={{lang}}" class="btn btn-outline-secondary btn-sm">Home</a>
          <a href="/?lang={{'ha' if lang=='en' else 'en'}}" class="btn btn-outline-secondary btn-sm">{{ lang_toggle }}</a>
        </div>
      </div>

      <p class="mt-2">{{total_label}}: <strong>{{total}}</strong></p>

      <div class="mb-3">
        <a href="{{ url_for('add_farmer', state=state, lga=lga, lang=lang) }}" class="btn btn-primary">{{add_farmer}}</a>
        <a href="{{ url_for('map_view', lang=lang) }}" class="btn btn-secondary">Map</a>
        <a href="{{ url_for('download_csv', lang=lang) }}" class="btn btn-info">{{download_csv}}</a>
      </div>

      <input id="searchInput" class="form-control mb-3" placeholder="{{search_placeholder}}">

      <div class="table-responsive">
        <table class="table table-striped" id="farmersTable">
          <thead><tr><th>ID</th><th>{{name_col}}</th><th>{{crop_col}}</th><th>{{phone_col}}</th><th>Farmer Photo</th><th>Farm Photo</th><th>Date Added</th></tr></thead>
          <tbody>
          {% for f in farmers %}
            <tr>
              <td>{{f[0]}}</td>
              <td>{{f[1]}}</td>
              <td>{{f[2]}}</td>
              <td>{{f[3]}}</td>
              <td>
                {% if f[4] %}
                  <img src="{{ url_for('uploaded_file', filename=f[4]) }}" style="max-width:80px;border-radius:5px;">
                {% else %} -
                {% endif %}
              </td>
              <td>
                {% if f[5] %}
                  <img src="{{ url_for('uploaded_file', filename=f[5]) }}" style="max-width:80px;border-radius:5px;">
                {% else %} -
                {% endif %}
              </td>
              <td>{{f[6]}}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>

      <hr>
      <h4>{{ 'Weather information (for this LGA)' if lang=='en' else 'Bayanan Yanayi (don wannan LGA)' }}</h4>
      {% if weather %}
        <table class="table table-sm">
          <thead><tr><th>Crop</th><th>Temp (°C)</th><th>Rainfall (mm)</th><th>Season</th></tr></thead>
          <tbody>
            {% for w in weather %}
              <tr><td>{{ w[0] }}</td><td>{{ w[1] }}</td><td>{{ w[2] }}</td><td>{{ w[3] }}</td></tr>
            {% endfor %}
          </tbody>
        </table>
      {% else %}
        <p><em>{{no_weather}}</em> <a href="{{ url_for('add_weather', lang=lang) }}">{{add_weather}}</a></p>
      {% endif %}

      {% if latlng %}
        <div id="map" style="height:300px;" class="mt-3"></div>
      {% endif %}
    </div>

    {% if latlng %}
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
      const lat = {{ latlng.lat }};
      const lng = {{ latlng.lng }};
      const map = L.map('map').setView([lat, lng], 12);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{ maxZoom:19 }).addTo(map);
      L.marker([lat,lng]).addTo(map).bindPopup("{{ lga }}, {{ state }}").openPopup();
    </script>
    {% endif %}

    <script>
      // Search/filter function
      const searchInput = document.getElementById('searchInput');
      const tableBody = document.getElementById('farmersTable').getElementsByTagName('tbody')[0];
      searchInput.addEventListener('keyup', function(){
        const filter = searchInput.value.toLowerCase();
        const rows = tableBody.getElementsByTagName('tr');
        for(let i=0;i<rows.length;i++){
          const cells = rows[i].getElementsByTagName('td');
          let match = false;
          for(let j=1;j<=3;j++){ // name, crop, phone
            if(cells[j] && cells[j].innerText.toLowerCase().indexOf(filter) > -1){ match = true; break; }
          }
          rows[i].style.display = match ? '' : 'none';
        }
      });
    </script>

    </body>
    </html>
    """
    return render_template_string(template,
                                  lang=lang,
                                  state=state,
                                  lga=lga,
                                  farmers=farmers,
                                  total=total,
                                  weather=weather,
                                  latlng=latlng,
                                  name_col=t("name", lang),
                                  crop_col=t("crop", lang),
                                  phone_col=t("phone", lang),
                                  add_farmer=t("add_farmer", lang),
                                  download_csv=t("download_csv", lang),
                                  total_label=t("total_farmers", lang),
                                  no_weather=t("no_weather", lang),
                                  add_weather=t("add_weather", lang),
                                  search_placeholder=t("search", lang),
                                  lang_toggle=t("language", lang))

# Add new farmer (upload files stored locally)
@app.route("/add_farmer/<state>/<lga>", methods=["GET","POST"])
def add_farmer(state, lga):
    lang = request.args.get('lang', 'en')
    if request.method == "POST":
        name = request.form.get('name')
        crop = request.form.get('crop')
        phone = request.form.get('phone')

        f_file = request.files.get('farmer_photo')
        farm_file = request.files.get('farm_photo')

        f_filename = None
        farm_filename = None

        if f_file and allowed_file(f_file.filename):
            f_filename = secure_filename(f"{int(datetime.now().timestamp())}_f_{f_file.filename}")
            f_file.save(os.path.join(app.config['UPLOAD_FOLDER'], f_filename))

        if farm_file and allowed_file(farm_file.filename):
            farm_filename = secure_filename(f"{int(datetime.now().timestamp())}_farm_{farm_file.filename}")
            farm_file.save(os.path.join(app.config['UPLOAD_FOLDER'], farm_filename))

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('''INSERT INTO farmers (name,state,lga,crop,phone,farmer_photo,farm_photo,date_added)
                     VALUES (?,?,?,?,?,?,?,?)''',
                  (name,state,lga,crop,phone,f_filename,farm_filename,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return redirect(url_for('lga_summary', state=state, lga=lga, lang=lang))

    template = """
    <!doctype html>
    <html lang="{{lang}}">
    <head>
      <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{{ add_farmer }} - {{ lga }}</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="p-4">
      <div class="container">
        <h3>{{ add_farmer }} - {{ lga }}, {{ state }}</h3>
        <form method="POST" enctype="multipart/form-data">
          <div class="mb-3"><label>{{name_col}}</label><input name="name" class="form-control" required></div>
          <div class="mb-3"><label>{{crop_col}}</label><input name="crop" class="form-control" required></div>
          <div class="mb-3"><label>{{phone_col}}</label><input name="phone" class="form-control" required></div>
          <div class="mb-3"><label>{{farmer_photo_col}}</label><input type="file" name="farmer_photo" class="form-control"></div>
          <div class="mb-3"><label>{{farm_photo_col}}</label><input type="file" name="farm_photo" class="form-control"></div>
          <button class="btn btn-success">{{submit}}</button>
          <a class="btn btn-secondary" href="{{ url_for('lga_summary', state=state, lga=lga, lang=lang) }}">{{back}}</a>
        </form>
      </div>
    </body>
    </html>
    """
    return render_template_string(template,
                                  lang=lang,
                                  state=state,
                                  lga=lga,
                                  add_farmer=t("add_farmer", lang),
                                  name_col=t("name", lang),
                                  crop_col=t("crop", lang),
                                  phone_col=t("phone", lang),
                                  farmer_photo_col=t("farmer_photo", lang),
                                  farm_photo_col=t("farm_photo", lang),
                                  submit=t("submit", lang),
                                  back=t("back", lang))

# Add weather data
@app.route("/add_weather", methods=["GET","POST"])
def add_weather():
    lang = request.args.get('lang', 'en')
    states_rows = query_db("SELECT DISTINCT state FROM lga_coords")
    states = [r[0] for r in states_rows] if states_rows else []
    if request.method == "POST":
        state = request.form.get('state')
        lga = request.form.get('lga')
        crop = request.form.get('crop')
        temp = request.form.get('temperature')
        rain = request.form.get('rainfall')
        season = request.form.get('season')
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO weather (state,lga,crop,temperature,rainfall,season) VALUES (?,?,?,?,?,?)",
                  (state,lga,crop, float(temp) if temp else None, float(rain) if rain else None, season))
        conn.commit()
        conn.close()
        return redirect(url_for('lga_summary', state=state, lga=lga, lang=lang))

    template = """
    <!doctype html>
    <html lang="{{lang}}">
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{{ add_weather }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="p-4">
    <div class="container">
      <h3>{{ add_weather }}</h3>
      <form method="POST">
        <div class="row g-2">
          <div class="col-md-4"><label>State</label>
            <select name="state" id="state" class="form-control" required>
              <option value="">Select State</option>
              {% for s in states %}<option value="{{s}}">{{s}}</option>{% endfor %}
            </select>
          </div>
          <div class="col-md-4"><label>LGA</label>
            <select name="lga" id="lga" class="form-control" required><option value="">Select LGA</option></select>
          </div>
          <div class="col-md-4"><label>Crop</label><input name="crop" class="form-control" required></div>
        </div>

        <div class="row g-2 mt-3">
          <div class="col-md-4"><label>Temperature (°C)</label><input name="temperature" class="form-control"></div>
          <div class="col-md-4"><label>Rainfall (mm)</label><input name="rainfall" class="form-control"></div>
          <div class="col-md-4"><label>Season</label><input name="season" class="form-control"></div>
        </div>

        <div class="mt-3">
          <button class="btn btn-primary">Save</button>
          <a href='/?lang={{lang}}' class='btn btn-secondary'>{{back}}</a>
        </div>
      </form>
    </div>

    <script>
    document.getElementById('state').addEventListener('change', function(){
      const state = this.value;
      const lgaSelect = document.getElementById('lga');
      lgaSelect.innerHTML = '<option>Loading...</option>';
      fetch('/api/lgas/' + encodeURIComponent(state)).then(r=>r.json()).then(data=>{
        lgaSelect.innerHTML = '<option value=\"\">Select LGA</option>';
        data.forEach(l=>{ const o=document.createElement('option'); o.value=l; o.text=l; lgaSelect.appendChild(o); });
      }).catch(()=> lgaSelect.innerHTML = '<option value=\"\">Select LGA</option>');
    });
    </script>
    </body>
    </html>
    """
    return render_template_string(template, lang=lang, states=states, add_weather=t("add_weather", lang), back=t("back", lang))

# Map data endpoint (counts per LGA + coords)
@app.route("/api/map_data")
def api_map_data():
    crop = request.args.get('crop')
    year = request.args.get('year')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    params = []
    q = "SELECT f.state, f.lga, COUNT(*) as cnt, lc.lat, lc.lng FROM farmers f JOIN lga_coords lc ON f.state=lc.state AND f.lga=lc.lga"
    if crop:
        q += " WHERE f.crop=?"
        params.append(crop)
    q += " GROUP BY f.state, f.lga"
    c.execute(q, params)
    rows = c.fetchall()
    conn.close()
    data = []
    for r in rows:
        data.append({"state": r[0], "lga": r[1], "count": r[2], "lat": r[3], "lng": r[4]})
    return jsonify(data)

# Map view
@app.route("/map")
def map_view():
    lang = request.args.get('lang', 'en')
    crops_rows = query_db("SELECT DISTINCT crop FROM farmers")
    crops = [r[0] for r in crops_rows if r[0]] if crops_rows else []
    template = """
    <!doctype html>
    <html lang="{{lang}}">
    <head>
      <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>Crop Distribution Map</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
      <style>#map{height:80vh;width:100%;}</style>
    </head>
    <body class="p-2">
    <div class="container-fluid">
      <div class="d-flex gap-2 mb-2">
        <select id="cropFilter" class="form-control w-auto">
          <option value="">{{ 'All crops' if lang=='en' else 'Dukkan Amfanoni' }}</option>
          {% for c in crops %}<option value="{{c}}">{{c}}</option>{% endfor %}
        </select>
        <button id="reload" class="btn btn-primary">Reload</button>
        <a href="/?lang={{lang}}" class="btn btn-secondary">Home</a>
      </div>
      <div id="map"></div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
      const map = L.map('map').setView([9.0820, 8.6753], 6);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 18}).addTo(map);
      let markers = [];
      function colorForCount(n){
        if(n<=0) return '#cccccc';
        if(n<3) return '#fee5d9';
        if(n<6) return '#fcae91';
        if(n<12) return '#fb6a4a';
        if(n<25) return '#de2d26';
        return '#a50f15';
      }
      function loadData(){
        markers.forEach(m=>map.removeLayer(m));
        markers = [];
        const crop = document.getElementById('cropFilter').value;
        const url = '/api/map_data' + (crop ? ('?crop=' + encodeURIComponent(crop)) : '');
        fetch(url).then(r=>r.json()).then(data=>{
          if(data.length===0) return;
          data.forEach(item=>{
            const c = colorForCount(item.count);
            const circle = L.circleMarker([item.lat, item.lng], {
              radius: 8 + Math.min(item.count, 25),
              fillColor: c,
              color: '#333',
              weight: 1,
              fillOpacity: 0.8
            }).addTo(map);
            circle.bindPopup(`<strong>${item.lga}, ${item.state}</strong><br/>Farmers: ${item.count}`);
            markers.push(circle);
          });
          const group = L.featureGroup(markers);
          map.fitBounds(group.getBounds(), {padding:[50,50]});
        });
      }
      document.getElementById('reload').addEventListener('click', loadData);
      loadData();
    </script>
    </body>
    </html>
    """
    return render_template_string(template, lang=lang, crops=crops)

# Download CSV (all farmers)
@app.route("/download")
def download_csv():
    lang = request.args.get('lang', 'en')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, name, state, lga, crop, phone, date_added FROM farmers")
    rows = c.fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID','Name','State','LGA','Crop','Phone','DateAdded'])
    writer.writerows(rows)
    resp = Response(output.getvalue(), mimetype='text/csv')
    resp.headers["Content-Disposition"] = "attachment; filename=farmers_data.csv"
    return resp

# Serve uploads (local)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Simple API: state summary counts
@app.route("/api/state_summary/<state>")
def api_state_summary(state):
    rows = query_db("SELECT lga, COUNT(*) FROM farmers WHERE state=? GROUP BY lga", (state,))
    return jsonify([{"lga": r[0], "count": r[1]} for r in rows])

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    # debug True for local testing; set to False in production
    app.run(host="0.0.0.0", port=5000, debug=True)
