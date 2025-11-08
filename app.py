# app.py
from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory, jsonify, Response
import sqlite3, os, io, csv
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# -------------------------
# Configuration
# -------------------------
DB = "farmers.db"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return filename and '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------------
# Initialize DB (farmers, weather, lga_coords)
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
            location TEXT,
            crop TEXT,
            date_planted TEXT,
            expected_harvest TEXT,
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
            season TEXT,
            date_recorded TEXT
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

    # seed some sample LGA coords if empty (replace with full dataset later)
    c.execute("SELECT COUNT(*) FROM lga_coords")
    if c.fetchone()[0] == 0:
        sample = [
            ("Lagos","Ikeja",6.6018,3.3515),
            ("Lagos","Epe",6.5859,3.9269),
            ("Kano","Nassarawa",12.0022,8.5167),
            ("Kano","Gwale",11.9993,8.5228),
            ("Rivers","Port Harcourt",4.8156,7.0490),
            ("Kaduna","Birnin Gwari",10.5863,6.5956)
        ]
        c.executemany("INSERT INTO lga_coords (state,lga,lat,lng) VALUES (?,?,?,?)", sample)
        conn.commit()
    conn.close()

init_db()

# -------------------------
# Helpers
# -------------------------
def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(query, args)
    rv = c.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def t(key, lang):
    # translations used in this app (extend as needed)
    texts = {
        "welcome": {"en":"Welcome to Smart Farmers Data Portal","ha":"Barka da zuwa Cibiyar Bayanai ta Manoma"},
        "register_farm": {"en":"Register Farm","ha":"Rajistar Gona"},
        "view_farms": {"en":"View Farms","ha":"Duba Gonaki"},
        "weather_advice": {"en":"Weather Advisory","ha":"Shawarwarin Yanayi"},
        "map": {"en":"Map","ha":"Taswira"},
        "download": {"en":"Download CSV","ha":"Sauke CSV"},
        "states": {"en":"All States","ha":"Duk Jihohi"},
        "lgas": {"en":"LGAs","ha":"Kananan Hukumomi"},
        "search": {"en":"Search by name, crop or LGA","ha":"Bincika da suna, amfanin gona ko LGA"},
        "language_toggle": {"en":"Hausa", "ha":"English"}
    }
    return texts.get(key, {}).get(lang, key)

# Basic planting rules per common crops (months as abbreviations)
CROP_RULES = {
    "maize": {"best_planting":"May-June", "note":"Maize usually planted at start of rainy season."},
    "rice": {"best_planting":"June-July", "note":"Rice needs flooded/irrigated fields; start with rains."},
    "groundnut": {"best_planting":"March-May", "note":"Prefer early rains and well-drained soils."},
    "soybean": {"best_planting":"May-June", "note":"Plant at onset of reliable rainfall."},
    "millet": {"best_planting":"June-July", "note":"Adapted to drier parts; plant with early rains."},
    "yam": {"best_planting":"April-May", "note":"Plant yam tubers at start of rainy season."}
}

def advisory_for(state,lga,crop):
    # simple advisory combining rules + last weather record if exists
    crop_key = (crop or "").strip().lower()
    rule = CROP_RULES.get(crop_key)
    w = query_db("SELECT temperature, rainfall, season, date_recorded FROM weather WHERE state=? AND lga=? AND crop=? ORDER BY date_recorded DESC LIMIT 1", (state,lga,crop))
    msg = ""
    if rule:
        msg += f"Recommended planting window for {crop.title()}: {rule['best_planting']}. {rule['note']}"
    else:
        msg += f"No specific calendar rule for {crop}. Use local advisory."

    if w:
        temp, rain, season, date_recorded = w[0][0], w[0][1], w[0][2], w[0][3]
        msg += f" Last recorded weather ({date_recorded}): Temp={temp}°C, Rainfall={rain}mm, Season={season}."
        # naive advisory
        if rain is not None and rain < 20:
            msg += " Current rainfall low — consider irrigation or delay planting small-seeded crops."
        elif rain is not None and rain > 200:
            msg += " High rainfall recorded — risk of waterlogging; pick tolerant varieties."
    else:
        msg += " No recent weather data for this location."
    return msg

# -------------------------
# Routes
# -------------------------

# Home / dashboard
@app.route("/", methods=["GET","POST"])
def index():
    lang = request.args.get('lang','en')
    states = [r[0] for r in query_db("SELECT DISTINCT state FROM lga_coords")] or []
    if request.method == "POST":
        state = request.form.get('state')
        lga = request.form.get('lga')
        if state and lga:
            return redirect(url_for('lga_view', state=state, lga=lga, lang=lang))
    template = """
    <!doctype html>
    <html lang="{{lang}}">
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{{welcome}}</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="p-4">
      <div class="container">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h1>{{welcome}}</h1>
          <div>
            <a href="/?lang={{'ha' if lang=='en' else 'en'}}" class="btn btn-outline-secondary btn-sm">{{lang_toggle}}</a>
          </div>
        </div>

        <form method="POST">
          <div class="row g-2">
            <div class="col-md-5">
              <label class="form-label">{{'State' if lang=='en' else 'Jihar'}}</label>
              <select name="state" id="stateSelect" class="form-control" required>
                <option value="">{{'Select State' if lang=='en' else 'Zaɓi Jihar'}}</option>
                {% for s in states %}<option value="{{s}}">{{s}}</option>{% endfor %}
              </select>
            </div>
            <div class="col-md-5">
              <label class="form-label">{{'LGA' if lang=='en' else 'Karamar Hukuma'}}</label>
              <select name="lga" id="lgaSelect" class="form-control" required>
                <option value="">{{'Select LGA' if lang=='en' else 'Zaɓi LGA'}}</option>
              </select>
            </div>
            <div class="col-md-2 d-flex align-items-end">
              <button class="btn btn-success w-100">{{'Go' if lang=='en' else 'Je'}}</button>
            </div>
          </div>
        </form>

        <hr class="my-3">

        <div class="d-flex gap-2">
          <a href="{{ url_for('register_farm', lang=lang) }}" class="btn btn-primary">{{'Register Farm' if lang=='en' else 'Rajistar Gona'}}</a>
          <a href="{{ url_for('farms_list', lang=lang) }}" class="btn btn-secondary">{{'View All Farms' if lang=='en' else 'Duba Duk Gonaki'}}</a>
          <a href="{{ url_for('map_view', lang=lang) }}" class="btn btn-info">Map</a>
          <a href="{{ url_for('add_weather', lang=lang) }}" class="btn btn-outline-primary">{{'Add Weather' if lang=='en' else 'Ƙara Bayanai Yanayi'}}</a>
          <a href="{{ url_for('download_all_csv', lang=lang) }}" class="btn btn-success">{{'Download CSV' if lang=='en' else 'Sauke CSV'}}</a>
        </div>
      </div>

      <script>
        document.getElementById('stateSelect').addEventListener('change', function(){
          const state = this.value;
          const lgaSelect = document.getElementById('lgaSelect');
          lgaSelect.innerHTML = '<option>Loading...</option>';
          if(!state){ lgaSelect.innerHTML = '<option value=\"\">Select LGA</option>'; return; }
          fetch('/api/lgas/' + encodeURIComponent(state))
            .then(r => r.json())
            .then(data => {
              lgaSelect.innerHTML = '<option value=\"\">Select LGA</option>';
              data.forEach(l => { const o = document.createElement('option'); o.value = l; o.text = l; lgaSelect.appendChild(o); });
            }).catch(()=> lgaSelect.innerHTML = '<option value=\"\">Select LGA</option>');
        });
      </script>
    </body>
    </html>
    """
    return render_template_string(template, lang=lang, welcome=t("welcome",lang), states=states, lang_toggle=t("language_toggle",lang))

# API: LGAs for a state
@app.route("/api/lgas/<state>")
def api_lgas(state):
    rows = query_db("SELECT lga FROM lga_coords WHERE state=?", (state,))
    return jsonify([r[0] for r in rows])

# Register farm
@app.route("/register", methods=["GET","POST"])
def register_farm():
    lang = request.args.get('lang','en')
    states = [r[0] for r in query_db("SELECT DISTINCT state FROM lga_coords")] or []
    if request.method == "POST":
        name = request.form.get('name')
        state = request.form.get('state')
        lga = request.form.get('lga')
        location = request.form.get('location')  # textual or lat,lng
        crop = request.form.get('crop')
        date_planted = request.form.get('date_planted')
        expected_harvest = request.form.get('expected_harvest')
        phone = request.form.get('phone')

        f_photo = request.files.get('farmer_photo')
        farm_photo = request.files.get('farm_photo')
        f_filename = None
        farm_filename = None
        if f_photo and allowed_file(f_photo.filename):
            f_filename = secure_filename(f"{int(datetime.now().timestamp())}_f_{f_photo.filename}")
            f_photo.save(os.path.join(UPLOAD_FOLDER, f_filename))
        if farm_photo and allowed_file(farm_photo.filename):
            farm_filename = secure_filename(f"{int(datetime.now().timestamp())}_farm_{farm_photo.filename}")
            farm_photo.save(os.path.join(UPLOAD_FOLDER, farm_filename))

        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute('''INSERT INTO farmers (name,state,lga,location,crop,date_planted,expected_harvest,phone,farmer_photo,farm_photo,date_added)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                  (name,state,lga,location,crop,date_planted,expected_harvest,phone,f_filename,farm_filename,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
        return redirect(url_for('lga_view', state=state, lga=lga, lang=lang))

    template = """
    <!doctype html>
    <html lang="{{lang}}">
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{{'Register Farm' if lang=='en' else 'Rajistar Gona'}}</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="p-4">
      <div class="container">
        <h2>{{'Register Farm' if lang=='en' else 'Rajistar Gona'}}</h2>
        <form method="POST" enctype="multipart/form-data">
          <div class="mb-3"><label>{{'Full Name' if lang=='en' else 'Cikakken Suna'}}</label><input name="name" class="form-control" required></div>
          <div class="row g-2">
            <div class="col-md-6">
              <label>{{'State' if lang=='en' else 'Jihar'}}</label>
              <select name="state" id="state" class="form-control" required>
                <option value="">{{'Select State' if lang=='en' else 'Zaɓi Jihar'}}</option>
                {% for s in states %}<option value="{{s}}">{{s}}</option>{% endfor %}
              </select>
            </div>
            <div class="col-md-6">
              <label>{{'LGA' if lang=='en' else 'Karamar Hukuma'}}</label>
              <select name="lga" id="lga" class="form-control" required><option value="">{{'Select LGA' if lang=='en' else 'Zaɓi LGA'}}</option></select>
            </div>
          </div>
          <div class="mb-3"><label>{{'Farm location (village or lat,lng)' if lang=='en' else 'Wurin Gona (ƙauye ko lat,lng)'}} </label><input name="location" class="form-control"></div>
          <div class="mb-3"><label>{{'Crop' if lang=='en' else 'Amfanin Gona'}}</label><input name="crop" class="form-control" required></div>
          <div class="row g-2">
            <div class="col-md-6"><label>{{'Date Planted' if lang=='en' else 'Ranar Shuka'}}</label><input type="date" name="date_planted" class="form-control"></div>
            <div class="col-md-6"><label>{{'Expected Harvest' if lang=='en' else 'Ranar Girbi'}}</label><input type="date" name="expected_harvest" class="form-control"></div>
          </div>
          <div class="mb-3"><label>{{'Phone' if lang=='en' else 'Lambar Waya'}}</label><input name="phone" class="form-control"></div>
          <div class="mb-3"><label>{{'Farmer Photo' if lang=='en' else 'Hoton Manomi'}}</label><input type="file" name="farmer_photo" class="form-control"></div>
          <div class="mb-3"><label>{{'Farm Photo' if lang=='en' else 'Hoton Gona'}}</label><input type="file" name="farm_photo" class="form-control"></div>
          <button class="btn btn-success">{{'Submit' if lang=='en' else 'Tura'}}</button>
          <a class="btn btn-secondary" href="/?lang={{lang}}">{{'Back' if lang=='en' else 'Baya'}}</a>
        </form>
      </div>

      <script>
        document.getElementById('state').addEventListener('change', function(){
          const state = this.value; const lga = document.getElementById('lga');
          lga.innerHTML = '<option>Loading...</option>';
          fetch('/api/lgas/' + encodeURIComponent(state)).then(r=>r.json()).then(data=>{
            lga.innerHTML = '<option value=\"\">Select LGA</option>';
            data.forEach(v=>{ const o=document.createElement('option'); o.value=v; o.text=v; lga.appendChild(o); });
          }).catch(()=> lga.innerHTML = '<option value=\"\">Select LGA</option>');
        });
      </script>
    </body>
    </html>
    """
    return render_template_string(template, lang=lang, states=states)

# View all farms (with filters)
@app.route("/farms")
def farms_list():
    lang = request.args.get('lang','en')
    state = request.args.get('state')
    lga = request.args.get('lga')
    crop = request.args.get('crop')
    params = []
    q = "SELECT id,name,state,lga,location,crop,date_planted,expected_harvest,phone,farmer_photo,farm_photo,date_added FROM farmers"
    filters = []
    if state:
        filters.append(" state=? "); params.append(state)
    if lga:
        filters.append(" lga=? "); params.append(lga)
    if crop:
        filters.append(" lower(crop)=? "); params.append(crop.lower())
    if filters:
        q += " WHERE " + " AND ".join(filters)
    q += " ORDER BY date_added DESC"
    rows = query_db(q, tuple(params))
    states = [r[0] for r in query_db("SELECT DISTINCT state FROM lga_coords")] or []
    template = """
    <!doctype html>
    <html lang="{{lang}}">
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{{'Farms' if lang=='en' else 'Gonaki'}}</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="p-4">
      <div class="container">
        <div class="d-flex justify-content-between">
          <h2>{{'Farms' if lang=='en' else 'Gonaki'}}</h2>
          <a href="/?lang={{lang}}" class="btn btn-secondary">Home</a>
        </div>

        <form class="row g-2 my-3">
          <div class="col-md-3"><select id="state" class="form-control"><option value="">{{'All States' if lang=='en' else 'Duk Jihohi'}}</option>{% for s in states %}<option>{{s}}</option>{% endfor %}</select></div>
          <div class="col-md-3"><input id="lga" class="form-control" placeholder="{{'LGA' if lang=='en' else 'LGA'}}"></div>
          <div class="col-md-3"><input id="crop" class="form-control" placeholder="{{'Crop' if lang=='en' else 'Amfanin Gona'}}"></div>
          <div class="col-md-3"><button id="filterBtn" class="btn btn-primary w-100">Filter</button></div>
        </form>

        <table class="table table-striped">
          <thead><tr><th>ID</th><th>Name</th><th>State</th><th>LGA</th><th>Crop</th><th>Planted</th><th>Phone</th><th>Photos</th></tr></thead>
          <tbody>
            {% for r in rows %}
              <tr>
                <td>{{r[0]}}</td><td>{{r[1]}}</td><td>{{r[2]}}</td><td>{{r[3]}}</td><td>{{r[5]}}</td><td>{{r[6]}}</td><td>{{r[8]}}</td>
                <td>
                  {% if r[9] %}<img src="{{ url_for('uploaded_file', filename=r[9]) }}" style="max-width:60px; border-radius:4px;">{% endif %}
                  {% if r[10] %}<img src="{{ url_for('uploaded_file', filename=r[10]) }}" style="max-width:60px; border-radius:4px;">{% endif %}
                </td>
              </tr>
            {% endfor %}
          </tbody>
        </table>

        <a class="btn btn-success" href="{{ url_for('download_all_csv', lang=lang) }}">{{'Download CSV' if lang=='en' else 'Sauke CSV'}}</a>
      </div>

    <script>
      document.getElementById('filterBtn').addEventListener('click', function(e){
        e.preventDefault();
        const s = document.getElementById('state').value;
        const l = document.getElementById('lga').value;
        const c = document.getElementById('crop').value;
        const params = new URLSearchParams();
        if(s) params.append('state', s);
        if(l) params.append('lga', l);
        if(c) params.append('crop', c);
        location.href = '/farms?lang={{lang}}&' + params.toString();
      });
    </script>
    </body></html>
    """
    return render_template_string(template, lang=lang, rows=rows, states=states)

# View by state -> list LGAs & counts
@app.route("/states")
def states_view():
    lang = request.args.get('lang','en')
    rows = query_db("SELECT state, COUNT(*) FROM farmers GROUP BY state")
    lgas = query_db("SELECT state,lga FROM lga_coords ORDER BY state,lga")
    template = """
    <!doctype html>
    <html lang="{{lang}}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{{'States' if lang=='en' else 'Jihohi'}}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
    <body class="p-4"><div class="container">
      <h2>{{'States & Farmers' if lang=='en' else 'Jihohi & Manoma'}}</h2>
      <table class="table table-striped">
        <thead><tr><th>State</th><th>Farmer Count</th><th>LGAs</th></tr></thead>
        <tbody>
        {% for r in rows %}
          <tr>
            <td>{{r[0]}}</td><td>{{r[1]}}</td>
            <td>
              {% for l in lgas %}
                {% if l[0]==r[0] %}<a href="{{ url_for('lga_view', state=l[0], lga=l[1], lang=lang) }}">{{l[1]}}</a>,
                {% endif %}
              {% endfor %}
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
      <a class="btn btn-secondary" href="/?lang={{lang}}">Home</a>
    </div></body></html>
    """
    return render_template_string(template, lang=lang, rows=rows, lgas=lgas)

# View LGA (detailed) - includes advisory
@app.route("/lga/<state>/<lga>")
def lga_view(state,lga):
    lang = request.args.get('lang','en')
    farmers = query_db("SELECT id,name,crop,date_planted,expected_harvest,phone,farmer_photo,farm_photo,date_added,location FROM farmers WHERE state=? AND lga=? ORDER BY date_added DESC", (state,lga))
    total = len(farmers)
    weather = query_db("SELECT crop,temperature,rainfall,season,date_recorded FROM weather WHERE state=? AND lga=? ORDER BY date_recorded DESC", (state,lga))
    # simple aggregated crop counts
    crop_counts = query_db("SELECT crop, COUNT(*) FROM farmers WHERE state=? AND lga=? GROUP BY crop", (state,lga))
    # advisory for top crop if any
    top_crop = crop_counts[0][0] if crop_counts else None
    advice = advisory_for(state,lga,top_crop) if top_crop else "No crop data to advise."
    coord = query_db("SELECT lat,lng FROM lga_coords WHERE state=? AND lga=?", (state,lga), one=True)
    latlng = {"lat":coord[0],"lng":coord[1]} if coord else None

    template = """
    <!doctype html>
    <html lang="{{lang}}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{{lga}} - {{state}}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
    <body class="p-4"><div class="container">
      <div class="d-flex justify-content-between">
        <h2>{{state}} → {{lga}}</h2>
        <div><a class="btn btn-secondary" href="/?lang={{lang}}">Home</a></div>
      </div>
      <p>{{'Total Farmers' if lang=='en' else 'Jimillar Manoma'}}: <strong>{{total}}</strong></p>

      <div class="mb-3">
        <a class="btn btn-primary" href="{{ url_for('register_farm', lang=lang) }}">{{'Register Farm' if lang=='en' else 'Rajistar Gona'}}</a>
        <a class="btn btn-info" href="{{ url_for('download_lga_csv', state=state, lga=lga, lang=lang) }}">{{'Download CSV (LGA)' if lang=='en' else 'Sauke CSV (LGA)'}} </a>
      </div>

      <h4>{{'Farms' if lang=='en' else 'Gonaki'}}</h4>
      <table class="table table-striped">
        <thead><tr><th>ID</th><th>{{'Name' if lang=='en' else 'Suna'}}</th><th>{{'Crop' if lang=='en' else 'Amfanin Gona'}}</th><th>{{'Planted' if lang=='en' else 'Ranar Shuka'}}</th><th>Phone</th><th>Photos</th></tr></thead>
        <tbody>
        {% for f in farmers %}
          <tr>
            <td>{{f[0]}}</td><td>{{f[1]}}</td><td>{{f[2]}}</td><td>{{f[3]}}</td><td>{{f[5]}}</td>
            <td>
              {% if f[6] %}<img src="{{ url_for('uploaded_file', filename=f[6]) }}" style="max-width:60px;">{% endif %}
              {% if f[7] %}<img src="{{ url_for('uploaded_file', filename=f[7]) }}" style="max-width:60px;">{% endif %}
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>

      <hr>
      <h4>{{'Weather data & Advisory' if lang=='en' else 'Bayanan Yanayi & Shawara'}}</h4>
      <p><strong>Top crop:</strong> {{ top_crop or '—' }}</p>
      <p><em>{{ advice }}</em></p>

      {% if weather %}
        <table class="table table-sm">
          <thead><tr><th>Crop</th><th>Temp(°C)</th><th>Rain(mm)</th><th>Season</th><th>Date</th></tr></thead>
          <tbody>
          {% for w in weather %}
            <tr><td>{{w[0]}}</td><td>{{w[1]}}</td><td>{{w[2]}}</td><td>{{w[3]}}</td><td>{{w[4]}}</td></tr>
          {% endfor %}
          </tbody>
        </table>
      {% else %}
        <p><em>{{'No weather data yet for this LGA.' if lang=='en' else 'Babu bayanan yanayi a wannan LGA.'}}</em></p>
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
      const map = L.map('map').setView([lat,lng], 12);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{ maxZoom:19 }).addTo(map);
      L.marker([lat,lng]).addTo(map).bindPopup("{{ lga }}, {{ state }}").openPopup();
    </script>
    {% endif %}
    </body></html>
    """
    return render_template_string(template, lang=lang, state=state, lga=lga, farmers=farmers, total=total, weather=weather, top_crop=top_crop, advice=advice, latlng=latlng)

# Add weather data (admin)
@app.route("/add_weather", methods=["GET","POST"])
def add_weather():
    lang = request.args.get('lang','en')
    states = [r[0] for r in query_db("SELECT DISTINCT state FROM lga_coords")] or []
    if request.method == "POST":
        state = request.form.get('state'); lga = request.form.get('lga'); crop = request.form.get('crop')
        temp = request.form.get('temperature'); rain = request.form.get('rainfall'); season = request.form.get('season')
        date_recorded = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("INSERT INTO weather (state,lga,crop,temperature,rainfall,season,date_recorded) VALUES (?,?,?,?,?,?,?)",
                  (state,lga,crop, float(temp) if temp else None, float(rain) if rain else None, season, date_recorded))
        conn.commit(); conn.close()
        return redirect(url_for('lga_view', state=state, lga=lga, lang=lang))
    template = """
    <!doctype html><html lang="{{lang}}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{{'Add Weather' if lang=='en' else 'Ƙara Yanayi'}}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
    <body class="p-4"><div class="container">
      <h3>{{'Add Weather Data' if lang=='en' else 'Ƙara Bayanai na Yanayi'}}</h3>
      <form method="POST">
        <div class="row g-2">
          <div class="col-md-4"><label>State</label><select id="state" name="state" class="form-control" required><option value="">Select</option>{% for s in states %}<option>{{s}}</option>{% endfor %}</select></div>
          <div class="col-md-4"><label>LGA</label><select id="lga" name="lga" class="form-control" required><option value="">Select</option></select></div>
          <div class="col-md-4"><label>Crop</label><input name="crop" class="form-control" required></div>
        </div>
        <div class="row g-2 mt-3"><div class="col-md-4"><label>Temperature (°C)</label><input name="temperature" class="form-control"></div><div class="col-md-4"><label>Rainfall (mm)</label><input name="rainfall" class="form-control"></div><div class="col-md-4"><label>Season</label><input name="season" class="form-control"></div></div>
        <div class="mt-3"><button class="btn btn-primary">Save</button> <a class="btn btn-secondary" href="/?lang={{lang}}">Home</a></div>
      </form>
    </div>
    <script>
      document.getElementById('state').addEventListener('change', function(){
        const state = this.value; const lga = document.getElementById('lga'); lga.innerHTML = '<option>Loading...</option>';
        fetch('/api/lgas/'+encodeURIComponent(state)).then(r=>r.json()).then(data=>{ lga.innerHTML = '<option value=\"\">Select</option>'; data.forEach(v=>{ const o=document.createElement('option'); o.value=v; o.text=v; lga.appendChild(o); }); }).catch(()=> lga.innerHTML = '<option value=\"\">Select</option>');
      });
    </script>
    </body></html>
    """
    return render_template_string(template, lang=lang, states=states)

# Map endpoints and view
@app.route("/api/map_data")
def api_map_data():
    crop = request.args.get('crop')
    params = []
    q = "SELECT f.state, f.lga, COUNT(*) as cnt, lc.lat, lc.lng FROM farmers f JOIN lga_coords lc ON f.state=lc.state AND f.lga=lc.lga"
    if crop:
        q += " WHERE lower(f.crop)=?"; params.append(crop.lower())
    q += " GROUP BY f.state, f.lga"
    rows = query_db(q, tuple(params))
    data = [{"state":r[0],"lga":r[1],"count":r[2],"lat":r[3],"lng":r[4]} for r in rows]
    return jsonify(data)

@app.route("/map")
def map_view():
    lang = request.args.get('lang','en')
    crops = [r[0] for r in query_db("SELECT DISTINCT crop FROM farmers") if r[0]]
    template = """
    <!doctype html><html lang="{{lang}}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>Map</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><style>#map{height:80vh;}</style></head>
    <body class="p-2"><div class="container-fluid">
      <div class="d-flex gap-2 mb-2">
        <select id="cropFilter" class="form-control w-auto"><option value="">{{'All crops' if lang=='en' else 'Dukkan Amfanoni'}}</option>{% for c in crops %}<option value="{{c}}">{{c}}</option>{% endfor %}</select>
        <button id="reload" class="btn btn-primary">Reload</button>
        <a href="/?lang={{lang}}" class="btn btn-secondary">Home</a>
      </div>
      <div id="map"></div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
      const map = L.map('map').setView([9.0820,8.6753],6);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
      let markers = [];
      function colorForCount(n){
        if(n<=0) return '#cccccc'; if(n<3) return '#fee5d9'; if(n<6) return '#fcae91'; if(n<12) return '#fb6a4a'; if(n<25) return '#de2d26'; return '#a50f15';
      }
      function loadData(){
        markers.forEach(m=>map.removeLayer(m)); markers = [];
        const crop = document.getElementById('cropFilter').value;
        const url = '/api/map_data' + (crop?('?crop='+encodeURIComponent(crop)):'');
        fetch(url).then(r=>r.json()).then(data=>{
          if(!data.length) return;
          data.forEach(item=>{
            const c = colorForCount(item.count);
            const circle = L.circleMarker([item.lat,item.lng],{radius:8+Math.min(item.count,25),fillColor:c,color:'#333',weight:1,fillOpacity:0.8}).addTo(map);
            circle.bindPopup(`<strong>${item.lga}, ${item.state}</strong><br/>Farmers: ${item.count}`);
            markers.push(circle);
          });
          const group = L.featureGroup(markers); map.fitBounds(group.getBounds(), {padding:[50,50]});
        });
      }
      document.getElementById('reload').addEventListener('click', loadData);
      loadData();
    </script>
    </body></html>
    """
    return render_template_string(template, lang=lang, crops=crops)

# CSV downloads: all, per state, per lga
@app.route("/download/all")
def download_all_csv():
    lang = request.args.get('lang','en')
    rows = query_db("SELECT id,name,state,lga,location,crop,date_planted,expected_harvest,phone,date_added FROM farmers")
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(['ID','Name','State','LGA','Location','Crop','DatePlanted','ExpectedHarvest','Phone','DateAdded'])
    writer.writerows(rows)
    resp = Response(output.getvalue(), mimetype='text/csv'); resp.headers["Content-Disposition"] = "attachment; filename=farmers_all.csv"
    return resp

@app.route("/download/state/<state>")
def download_state_csv(state):
    rows = query_db("SELECT id,name,state,lga,location,crop,date_planted,expected_harvest,phone,date_added FROM farmers WHERE state=?", (state,))
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(['ID','Name','State','LGA','Location','Crop','DatePlanted','ExpectedHarvest','Phone','DateAdded'])
    writer.writerows(rows)
    resp = Response(output.getvalue(), mimetype='text/csv'); resp.headers["Content-Disposition"] = f"attachment; filename=farmers_{state}.csv"
    return resp

@app.route("/download/lga/<state>/<lga>")
def download_lga_csv(state,lga):
    rows = query_db("SELECT id,name,state,lga,location,crop,date_planted,expected_harvest,phone,date_added FROM farmers WHERE state=? AND lga=?", (state,lga))
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(['ID','Name','State','LGA','Location','Crop','DatePlanted','ExpectedHarvest','Phone','DateAdded'])
    writer.writerows(rows)
    resp = Response(output.getvalue(), mimetype='text/csv'); resp.headers["Content-Disposition"] = f"attachment; filename=farmers_{state}_{lga}.csv"
    return resp

# Serve local uploads
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# API: state summary (counts per lga)
@app.route("/api/state_summary/<state>")
def api_state_summary(state):
    rows = query_db("SELECT lga, COUNT(*) FROM farmers WHERE state=? GROUP BY lga", (state,))
    return jsonify([{"lga":r[0],"count":r[1]} for r in rows])

# Run
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
