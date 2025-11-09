from flask import Flask, render_template_string, request, send_file
import sqlite3, os, csv, random
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'static/photos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DB = 'farmers.db'

# === Initialize database ===
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # farmers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS farmers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            state TEXT,
            lga TEXT,
            crop TEXT,
            phone TEXT,
            photo_path TEXT
        )
    ''')
    # LGA coordinates
    c.execute('''
        CREATE TABLE IF NOT EXISTS lga_coords(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state TEXT,
            lga TEXT
        )
    ''')
    # Populate LGAs if empty
    c.execute("SELECT COUNT(*) FROM lga_coords")
    if c.fetchone()[0]==0:
        all_locations = {
            "Abia": ["Aba North","Aba South","Umuahia North","Umuahia South"],
            "Adamawa": ["Yola North","Yola South","Mubi North","Mubi South"],
            "FCT": ["Abaji","Gwagwalada","Kuje","Kwali","AMAC"]
            # ... add all 36 states + LGAs
        }
        for state, lgas in all_locations.items():
            for lga in lgas:
                c.execute("INSERT INTO lga_coords(state,lga) VALUES (?,?)",(state,lga))
        conn.commit()
    conn.close()

init_db()

# === Multi-language strings ===
lang_dict = {
    "en": {"welcome":"Smart Farmers Data Portal","name":"Full Name","phone":"Phone Number","state":"State","lga":"LGA",
           "crop":"Type of Crop","submit":"Submit","dashboard":"Dashboard","select_state":"Select State","select_lga":"Select LGA",
           "data_saved":"Data saved successfully!","weather":"Weather Indicator","recommended":"Recommended Crop"},
    "ha": {"welcome":"Smart Farmers Data Portal","name":"Cikakken Suna","phone":"Lambar Waya","state":"Jihar","lga":"Karamar Hukuma",
           "crop":"Irin Amfanin Gona","submit":"Tura","dashboard":"Dashboard","select_state":"Zaɓi Jihar","select_lga":"Zaɓi LGA",
           "data_saved":"An adana bayananka cikin nasara!","weather":"Yanayin Yanayi","recommended":"Amfanin Gona da ya dace"},
    "yo": {"welcome":"Smart Farmers Data Portal","name":"Orúkọ Kíkún","phone":"Nọ́mbà Fóònù","state":"Ìpínlẹ̀","lga":"LGA",
           "crop":"Iru Ọgbin","submit":"Firanṣẹ","dashboard":"Dashboard","select_state":"Yan Ìpínlẹ̀","select_lga":"Yan LGA",
           "data_saved":"Fipamọ data ni aṣeyọri!","weather":"Ọjọ́ Òjò","recommended":"Ọgbin to dara"},
    "ig": {"welcome":"Smart Farmers Data Portal","name":"Aha zuru ezu","phone":"Nọmba ekwentị","state":"Steeti","lga":"LGA",
           "crop":"Uru ugbo","submit":"Zipu","dashboard":"Dashboard","select_state":"Họrọ Steeti","select_lga":"Họrọ LGA",
           "data_saved":"Echekwara data nke ọma!","weather":"Ọnọdụ Ọnwụ̀","recommended":"Uru Ugbo kwesiri"}
}

# === Templates ===
form_template = """
<!DOCTYPE html>
<html lang="{{lang}}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{strings['welcome']}}</title>
<style>
body{font-family:Arial;background:#F5DEB3;padding:20px;}
.card{background:white;padding:20px;border-radius:10px;max-width:500px;margin:auto;box-shadow:0 0 10px #ccc;}
input,select,button{width:100%;padding:10px;margin-top:8px;border-radius:5px;border:1px solid #ccc;}
button{background:green;color:white;font-weight:bold;}
img{max-width:100px;margin:5px;border-radius:5px;}
</style>
</head>
<body>
<div class="card">
<h2>{{strings['welcome']}}</h2>
<form method="POST" enctype="multipart/form-data">
<label>{{strings['name']}}</label><input type="text" name="name" required>
<label>{{strings['state']}}</label>
<select name="state" id="state" required onchange="populateLGAs()">
<option value="">{{strings['select_state']}}</option>{% for s in states %}<option value="{{s}}">{{s}}</option>{% endfor %}
</select>
<label>{{strings['lga']}}</label>
<select name="lga" id="lga" required><option value="">{{strings['select_lga']}}</option></select>
<label>{{strings['crop']}}</label><input type="text" name="crop" required>
<label>{{strings['phone']}}</label><input type="text" name="phone" required>
<label>Photo</label><input type="file" name="photo" accept="image/*" required>
<button type="submit">{{strings['submit']}}</button>
</form>
{% if success %}<p style="color:green;">{{strings['data_saved']}}</p>{% endif %}
<p><a href="/dashboard?lang={{lang}}">{{strings['dashboard']}}</a></p>
<p>Language: <a href="/?lang=en">EN</a> | <a href="/?lang=ha">HA</a> | <a href="/?lang=yo">YO</a> | <a href="/?lang=ig">IG</a></p>
<script>
const lga_data={{ lga_json|safe }};
function populateLGAs(){
let st=document.getElementById('state').value;
let sel=document.getElementById('lga');
sel.innerHTML='<option value="">{{strings["select_lga"]}}</option>';
if(st in lga_data){lga_data[st].forEach(l=>{let o=document.createElement('option');o.value=l;o.innerHTML=l; sel.appendChild(o);});}
}
</script>
</div></body></html>
"""

dashboard_template = """
<!DOCTYPE html>
<html lang="{{lang}}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{strings['dashboard']}}</title>
<style>
body{font-family:Arial;background:#F5DEB3;padding:20px;}
table{border-collapse:collapse;width:100%;}
th,td{border:1px solid #ccc;padding:5px;text-align:center;}
img{max-width:80px;border-radius:5px;}
</style>
</head>
<body>
<h2>{{strings['dashboard']}}</h2>
<form method="GET">
<label>{{strings['state']}}</label>
<select name="filter_state" onchange="this.form.submit()">
<option value="">All States</option>{% for s in states %}<option value="{{s}}" {% if s==selected_state %}selected{% endif %}>{{s}}</option>{% endfor %}
</select>
<label>{{strings['lga']}}</label>
<select name="filter_lga" onchange="this.form.submit()">
<option value="">All LGAs</option>{% for l in lgas %}<option value="{{l}}" {% if l==selected_lga %}selected{% endif %}>{{l}}</option>{% endfor %}
</select>
</form>
<table>
<tr><th>{{strings['name']}}</th><th>{{strings['state']}}</th><th>{{strings['lga']}}</th><th>{{strings['crop']}}</th><th>{{strings['phone']}}</th><th>{{strings['weather']}}</th><th>{{strings['recommended']}}</th><th>Photo</th></tr>
{% for f in farmers %}
<tr>
<td>{{f['name']}}</td>
<td>{{f['state']}}</td>
<td>{{f['lga']}}</td>
<td>{{f['crop']}}</td>
<td>{{f['phone']}}</td>
<td>{{f['weather']}}</td>
<td>{{f['recommended']}}</td>
<td>{% if f['photo'] %}<img src="{{f['photo']}}">{% endif %}</td>
</tr>
{% endfor %}
</table>
<p><a href="/?lang={{lang}}">Back</a> | <a href="/download">Download CSV</a></p>
</body>
</html>
"""

# === Routes ===
@app.route("/", methods=["GET","POST"])
def home():
    lang = request.args.get("lang","ha")
    strings = lang_dict.get(lang, lang_dict["ha"])
    success = False
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT DISTINCT state FROM lga_coords ORDER BY state")
    states = [r[0] for r in c.fetchall()]
    if request.method=="POST":
        name = request.form["name"]
        state = request.form["state"]
        lga = request.form["lga"]
        crop = request.form["crop"]
        phone = request.form["phone"]
        photo = request.files["photo"]
        filename = secure_filename(photo.filename)
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(photo_path)
        c.execute("INSERT INTO farmers(name,state,lga,crop,phone,photo_path) VALUES(?,?,?,?,?,?)",
                  (name,state,lga,crop,phone,photo_path))
        conn.commit()
        success=True
    c.execute("SELECT state,lga FROM lga_coords")
    lga_json={}
    for s,l in c.fetchall(): lga_json.setdefault(s,[]).append(l)
    conn.close()
    return render_template_string(form_template, lang=lang, strings=strings, states=states, lga_json=lga_json, success=success)

@app.route("/dashboard")
def dashboard():
    lang = request.args.get("lang","ha")
    strings = lang_dict.get(lang, lang_dict["ha"])
    selected_state = request.args.get("filter_state","")
    selected_lga = request.args.get("filter_lga","")
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    query = "SELECT name,state,lga,crop,phone,photo_path FROM farmers WHERE 1=1"
    params=[]
    if selected_state: query+=" AND state=?"; params.append(selected_state)
    if selected_lga: query+=" AND lga=?"; params.append(selected_lga)
    c.execute(query, params)
    rows=c.fetchall()
    farmers=[]
    for r in rows:
        farmers.append({"name":r[0],"state":r[1],"lga":r[2],"crop":r[3],"phone":r[4],
                        "photo":r[5],"weather":random.choice(["Dry","Normal","Flood risk"]),
                        "recommended":random.choice(["Maize","Rice","Yam","Vegetables"])})
    c.execute("SELECT DISTINCT state FROM lga_coords ORDER BY state")
    states=[r[0] for r in c.fetchall()]
    lgas=[]
    if selected_state:
        c.execute("SELECT lga FROM lga_coords WHERE state=?",(selected_state,))
        lgas=[r[0] for r in c.fetchall()]
    conn.close()
    return render_template_string(dashboard_template, lang=lang, strings=strings, farmers=farmers,
                                  states=states, lgas=lgas, selected_state=selected_state, selected_lga=selected_lga)

@app.route("/download")
def download_csv():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT name,state,lga,crop,phone,photo_path FROM farmers")
    rows=c.fetchall()
    conn.close()
    path="farmers_data.csv"
    with open(path,"w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f)
        writer.writerow(["Name","State","LGA","Crop","Phone","Photo"])
        writer.writerows(rows)
    return send_file(path, as_attachment=True)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000)
