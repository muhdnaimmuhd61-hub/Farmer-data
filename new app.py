from flask import Flask, render_template_string, request, redirect, url_for, jsonify, send_file
import sqlite3, csv, random, os

app = Flask(__name__)
DB_FILE = "agrosmart.db"

# ==============================
# WEATHER & FLOOD SIMULATION
# ==============================
def get_weather_indicator():
    weather_data = [
        {"condition": "Sunny", "seed": "Maize", "risk": "Low"},
        {"condition": "Rainy", "seed": "Rice", "risk": "Medium"},
        {"condition": "Heavy Rain", "seed": "Sugarcane", "risk": "High"},
        {"condition": "Dry", "seed": "Millet", "risk": "Low"},
        {"condition": "Cloudy", "seed": "Cassava", "risk": "Medium"}
    ]
    return random.choice(weather_data)

# ==============================
# DATABASE INITIALIZATION
# ==============================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS states(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS lgas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        state_id INTEGER NOT NULL,
        FOREIGN KEY(state_id) REFERENCES states(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS farmers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        state TEXT,
        lga TEXT,
        crop TEXT,
        rainfall REAL DEFAULT 0,
        flood_risk TEXT DEFAULT 'Low'
    )""")

    conn.commit()

    # Example data: replace later with all 36 states + LGAs
    c.execute("SELECT COUNT(*) FROM states")
    if c.fetchone()[0] == 0:
        sample_states = {
            "Abia": ["Aba North", "Aba South", "Umuahia North", "Umuahia South"],
            "Kano": ["Kano Municipal", "Fagge", "Gwale", "Nasarawa"],
            "Lagos": ["Ikeja", "Surulere", "Epe", "Alimosho"]
        }
        for s, lgas in sample_states.items():
            c.execute("INSERT OR IGNORE INTO states(name) VALUES (?)", (s,))
            c.execute("SELECT id FROM states WHERE name=?", (s,))
            sid = c.fetchone()[0]
            for l in lgas:
                c.execute("INSERT INTO lgas(name,state_id) VALUES(?,?)", (l, sid))
        conn.commit()
    conn.close()

init_db()

# ==============================
# ROUTES
# ==============================
@app.route('/')
def home():
    indicator = get_weather_indicator()
    return render_template_string("""
    <body style="background:linear-gradient(to bottom right,#a8e063,#56ab2f);font-family:sans-serif;color:#fff;text-align:center;padding:50px;">
        <h1>🌾 Welcome to AgroSmart</h1>
        <p>Your intelligent farming assistant.</p>
        <h3>🌦 Weather: {{indicator.condition}} | 🌱 Recommended Seed: {{indicator.seed}} | 🌊 Flood Risk: {{indicator.risk}}</h3>
        <div style="margin-top:30px;">
            <a href="{{url_for('form')}}" style="background:white;color:#2d6a4f;padding:10px 20px;border-radius:10px;text-decoration:none;">Register Farmer</a>
            <a href="{{url_for('dashboard')}}" style="background:white;color:#2d6a4f;padding:10px 20px;margin-left:10px;border-radius:10px;text-decoration:none;">Dashboard</a>
        </div>
    </body>
    """, indicator=indicator)

# ==============================
# REGISTER FARMER
# ==============================
@app.route('/form', methods=['GET','POST'])
def form():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name FROM states ORDER BY name")
    states = [r[0] for r in c.fetchall()]

    if request.method == "POST":
        name = request.form['name']
        state = request.form['state']
        lga = request.form['lga']
        crop = request.form['crop']
        weather = get_weather_indicator()
        rainfall = random.uniform(10, 100)
        flood_risk = weather['risk']
        c.execute("INSERT INTO farmers(name,state,lga,crop,rainfall,flood_risk) VALUES(?,?,?,?,?,?)",
                  (name, state, lga, crop, rainfall, flood_risk))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    conn.close()

    return render_template_string("""
    <body style="background:#d4edda;font-family:sans-serif;text-align:center;padding:40px;">
        <h2>🧑‍🌾 Register Farmer</h2>
        <form method="POST" style="background:white;padding:20px;border-radius:10px;display:inline-block;">
            <input name="name" placeholder="Full Name" required><br><br>
            <select name="state" id="state" required onchange="fetchLGAs()">
                <option value="">Select State</option>
                {% for s in states %}
                    <option value="{{s}}">{{s}}</option>
                {% endfor %}
            </select><br><br>
            <select name="lga" id="lga" required>
                <option value="">Select LGA</option>
            </select><br><br>
            <input name="crop" placeholder="Crop Type" required><br><br>
            <button type="submit" style="background:#2d6a4f;color:white;padding:10px 20px;border:none;border-radius:8px;">Submit</button>
        </form>
        <br><br>
        <a href="{{url_for('home')}}">🏠 Back Home</a>

        <script>
        function fetchLGAs(){
            const state=document.getElementById("state").value;
            fetch('/api/lgas?state='+state)
            .then(res=>res.json())
            .then(data=>{
                const lgaSelect=document.getElementById("lga");
                lgaSelect.innerHTML="";
                data.lgas.forEach(l=>{
                    const opt=document.createElement('option');
                    opt.value=l;
                    opt.text=l;
                    lgaSelect.appendChild(opt);
                });
            })
        }
        </script>
    </body>
    """, states=states)

@app.route('/api/lgas')
def api_lgas():
    state = request.args.get('state')
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM states WHERE name=?",(state,))
    row = c.fetchone()
    if not row:
        return jsonify({"lgas":[]})
    sid = row[0]
    c.execute("SELECT name FROM lgas WHERE state_id=?",(sid,))
    lgas = [r[0] for r in c.fetchall()]
    conn.close()
    return jsonify({"lgas":lgas})

# ==============================
# DASHBOARD
# ==============================
@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT state, COUNT(*) FROM farmers GROUP BY state")
    data = c.fetchall()
    c.execute("SELECT name,state,lga,crop,flood_risk FROM farmers ORDER BY id DESC LIMIT 20")
    farmers = c.fetchall()
    conn.close()

    labels = [d[0] for d in data]
    counts = [d[1] for d in data]

    return render_template_string("""
    <body style="background:#d4edda;font-family:sans-serif;text-align:center;padding:30px;">
        <h2>📊 Farmers Dashboard</h2>
        <canvas id="chart" width="600" height="300"></canvas>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
        const ctx=document.getElementById('chart');
        new Chart(ctx,{type:'bar',data:{labels:{{labels|tojson}},datasets:[{label:'Farmers per State',data:{{counts|tojson}},backgroundColor:'rgba(75,192,192,0.6)'}]},options:{scales:{y:{beginAtZero:true}}}});
        </script>

        <h3>Recent Farmers</h3>
        <table border="1" cellpadding="6" style="margin:auto;background:white;">
            <tr><th>Name</th><th>State</th><th>LGA</th><th>Crop</th><th>Flood Risk</th></tr>
            {% for f in farmers %}
            <tr><td>{{f[0]}}</td><td>{{f[1]}}</td><td>{{f[2]}}</td><td>{{f[3]}}</td><td>{{f[4]}}</td></tr>
            {% endfor %}
        </table>

        <br>
        <a href="{{url_for('download_csv')}}" style="color:#2d6a4f;">⬇ Download CSV</a> |
        <a href="{{url_for('home')}}" style="color:#2d6a4f;">🏠 Back Home</a>
    </body>
    """, labels=labels, counts=counts, farmers=farmers)

# ==============================
# CSV DOWNLOAD
# ==============================
@app.route('/download')
def download_csv():
    filename = "farmers_export.csv"
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM farmers")
    rows = c.fetchall()
    headers = [desc[0] for desc in c.description]
    conn.close()

    with open(filename,'w',newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return send_file(filename, as_attachment=True)

# ==============================
if __name__ == '__main__':
    app.run(debug=True)
