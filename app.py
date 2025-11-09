from flask import Flask, render_template_string, request, send_file import sqlite3, os, csv, random from werkzeug.utils import secure_filename

app = Flask(name) app.config['UPLOAD_FOLDER'] = 'static/photos' os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

=== Initialize database with 36 States + LGAs ===

def init_db(): conn = sqlite3.connect('farmers.db') c = conn.cursor() c.execute('''CREATE TABLE IF NOT EXISTS farmers ( id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, state TEXT, lga TEXT, location TEXT, crop TEXT, phone TEXT, photo_path TEXT )''') c.execute('''CREATE TABLE IF NOT EXISTS lga_coords ( id INTEGER PRIMARY KEY AUTOINCREMENT, state TEXT, lga TEXT )''')

c.execute("SELECT COUNT(*) FROM lga_coords")
if c.fetchone()[0]==0:
    # Full Nigeria states + example LGAs (shortened for brevity, you can expand all 36 states + LGAs)
    all_locations = {
        "Abia": ["Aba North", "Aba South", "Umuahia North", "Umuahia South"],
        "Adamawa": ["Yola North", "Yola South", "Demsa", "Fufore"],
        "Akwa Ibom": ["Uyo", "Eket", "Ikot Ekpene"],
        "Anambra": ["Awka North", "Awka South", "Onitsha North", "Onitsha South"],
        "Bauchi": ["Bauchi", "Darazo", "Ningi"],
        # ... add all remaining 31 states + LGAs ...
        "FCT": ["Abaji", "AMAC", "Bwari", "Gwagwalada", "Kuje", "Kwali"]
    }
    for state, lgas in all_locations.items():
        for lga in lgas:
            c.execute("INSERT INTO lga_coords(state,lga) VALUES (?,?)", (state,lga))
    conn.commit()
conn.close()

init_db()

=== Multi-language strings ===

lang_dict = { "en": {"title":"Farmers Registration","state":"State","lga":"LGA","name":"Full Name","crop":"Crop Type", "location":"Farming Location","phone":"Phone","submit":"Submit","dashboard":"Dashboard", "filter_state":"Filter by State","filter_lga":"Filter by LGA","filter_name":"Filter by Name", "weather_alert":"Weather/Flood Alert","recommended_crop":"Recommended Crop"}, "ha": {"title":"Rijistar Manoma","state":"Jihar","lga":"Karamar Hukuma (LGA)","name":"Cikakken Suna", "crop":"Irin Amfanin Gona","location":"Wurin Noma","phone":"Lambar Waya","submit":"Tura", "dashboard":"Dashboard","filter_state":"Filter Jihar","filter_lga":"Filter LGA","filter_name":"Filter Suna", "weather_alert":"Yanayi / Ambaliya","recommended_crop":"Amfanin gona da ya dace"}, "yo": {"title":"Ìforúkọsílẹ̀ Ọ̀gbìn","state":"Ìpínlẹ̀","lga":"Agbegbe","name":"Orúkọ","crop":"Irú Ọ̀gbìn", "location":"Àgbègbè Ọ̀gbìn","phone":"Fóònù","submit":"Firanṣẹ","dashboard":"Dashboard", "filter_state":"Ṣàlẹ̀ Jihà","filter_lga":"Ṣàlẹ̀ Agbegbe","filter_name":"Ṣàlẹ̀ Orúkọ", "weather_alert":"Ìkìlọ̀ Òjò / Àdánwò","recommended_crop":"Ọ̀gbìn Tó Dára"}, "ig": {"title":"Ndebanye Ndị Ọgwụ","state":"Steeti","lga":"LGA","name":"Aha","crop":"Ụdị Ọgwụ", "location":"Ebe A na-akụ","phone":"Ekwentị","submit":"Zipu","dashboard":"Dashboard", "filter_state":"Nyocha Steeti","filter_lga":"Nyocha LGA","filter_name":"Nyocha Aha", "weather_alert":"Ilu / Miri","recommended_crop":"Ụdị Ọgwụ Dị Mma"} }

=== HTML templates simplified for dashboard + registration ===

form_template = """<!DOCTYPE html><html lang='{{lang}}'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>{{strings['title']}}</title><style>body{font-family:Arial;background:#f5f5f5;padding:20px;} .card{background:white;padding:20px;border-radius:10px;max-width:500px;margin:auto;box-shadow:0 0 10px #ccc;} input,select,button{width:100%;padding:10px;margin-top:8px;border-radius:5px;border:1px solid #ccc;} button{background:green;color:white;font-weight:bold;} img{max-width:100px;border-radius:5px;margin:5px;}</style></head><body><div class='card'><h2>{{strings['title']}}</h2><form method='POST' enctype='multipart/form-data'><label>{{strings['name']}}</label><input type='text' name='name' required><label>{{strings['state']}}</label><select name='state' id='state' required onchange='populateLGAs()'><option value=''>{{strings['state']}}</option>{% for s in states %}<option value='{{s}}'>{{s}}</option>{% endfor %}</select><label>{{strings['lga']}}</label><select name='lga' id='lga' required><option value=''>{{strings['lga']}}</option></select><label>{{strings['location']}}</label><input type='text' name='location' required><label>{{strings['crop']}}</label><input type='text' name='crop' required><label>{{strings['phone']}}</label><input type='text' name='phone' required><label>Photo</label><input type='file' name='photo' accept='image/*' required><button type='submit'>{{strings['submit']}}</button></form>{% if success %}<p style='color:green;'>Data saved successfully!</p>{% endif %}<p><a href='/dashboard?lang={{lang}}'>{{strings['dashboard']}}</a> | <a href='/download'>Download CSV</a></p><p>Language: <a href='/?lang=en'>EN</a> | <a href='/?lang=ha'>HA</a> | <a href='/?lang=yo'>YO</a> | <a href='/?lang=ig'>IG</a></p><script>const lga_data={{ lga_json|safe }}; function populateLGAs(){let state=document.getElementById('state').value;let lgaSelect=document.getElementById('lga');lgaSelect.innerHTML='<option value="">{{strings["lga"]}}</option>';if(state in lga_data){lga_data[state].forEach(lga=>{let opt=document.createElement('option');opt.value=lga;opt.innerHTML=lga;lgaSelect.appendChild(opt);});}}</script></div></body></html>"""

Dashboard template

dashboard_template = """<!DOCTYPE html><html lang='{{lang}}'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>{{strings['dashboard']}}</title><style>body{font-family:Arial;background:#f5f5f5;padding:20px;} img{max-width:80px;border-radius:5px;}</style></head><body><h2>{{strings['dashboard']}}</h2><form method='GET'><label>{{strings['filter_state']}}</label><select name='filter_state' onchange='this.form.submit()'><option value=''>All States</option>{% for s in states %}<option value='{{s}}' {% if s==selected_state %}selected{% endif %}>{{s}}</option>{% endfor %}</select><label>{{strings['filter_lga']}}</label><select name='filter_lga' onchange='this.form.submit()'><option value=''>All LGAs</option>{% for l in lgas %}<option value='{{l}}' {% if l==selected_lga %}selected{% endif %}>{{l}}</option>{% endfor %}</select><label>{{strings['filter_name']}}</label><input type='text' name='filter_name' value='{{selected_name}}' onchange='this.form.submit()'></form><table border='1' cellpadding='5' cellspacing='0'><tr><th>{{strings['name']}}</th><th>{{strings['state']}}</th><th>{{strings['lga']}}</th><th>{{strings['crop']}}</th><th>{{strings['location']}}</th><th>{{strings['phone']}}</th><th>{{strings['weather_alert']}}</th><th>{{strings['recommended_crop']}}</th><th>Photo</th></tr>{% for f in farmers %}<tr><td>{{f['name']}}</td><td>{{f['state']}}</td><td>{{f['lga']}}</td><td>{{f['crop']}}</td><td>{{f['location']}}</td><td>{{f['phone']}}</td><td>{{f['alert']}}</td><td>{{f['recommendation']}}</td><td>{% if f['photo_path'] %}<img src='{{f['photo_path']}}'>{% endif %}</td></tr>{% endfor %}</table><p><a href='/?lang={{lang}}'>Back to Registration</a></p></body></html>"""

@app.route('/', methods=['GET','POST']) def home(): lang = request.args.get('lang','ha') strings = lang_dict.get(lang, lang_dict['ha']) success = False conn = sqlite3.connect('farmers.db') c = conn.cursor() c.execute("SELECT DISTINCT state FROM lga_coords ORDER BY state") states = [r[0] for r in c.fetchall()]

if request.method=='POST':
    name = request.form['name']
    state = request.form['state']
    lga = request.form['lga']
    location = request.form['location']
    crop = request.form['crop']
    phone = request.form['phone']
    photo = request.files['photo']
    filename = secure_filename(photo.filename)
    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    photo.save(photo_path)
    c.execute("INSERT INTO farmers(name,state,lga,location,crop,phone,photo_path) VALUES(?,?,?,?,?,?,?)",
              (name,state,lga,location,crop,phone,photo_path))
    conn.commit()
    success = True

c.execute("SELECT state,lga FROM lga_coords")
lga_json = {}
for s,l in c.fetchall(): lga_json.setdefault(s,[]).append(l)
conn.close()
return render_template_string(form_template, lang=lang, strings=strings, states=states, lga_json=lga_json, success=success)

@app.route('/dashboard') def dashboard(): lang = request.args.get('lang','ha') strings = lang_dict.get(lang, lang_dict['ha']) selected_state = request.args.get('filter_state','') selected_lga = request.args.get('filter_lga','') selected_name = request.args.get('filter_name','')

conn = sqlite3.connect('farmers.db')
c = conn.cursor()
query = "SELECT name,state,lga,crop,location,phone,photo_path FROM farmers WHERE 1=1"
params = []
if selected_state: query += " AND state=?"; params.append(selected_state)
if selected_lga: query += " AND lga=?"; params.append(selected_lga)
if selected_name: query += " AND name LIKE ?"; params.append(f"%{selected_name}%")
c.execute(query, params)
farmers_raw = c.fetchall()

farmers = []
for f in farmers_raw:
    alert=random.choice(["Flood risk","Dry area","Normal"])
    rec=random.choice(["Maize","Rice","Yam","Vegetables","Cassava"])
    farmers.append({"name":f[0],"state":f[1],"lga":f[2],"crop":f[3],"location":f[4],"phone":f[5],"photo_path":f[6],"alert":alert,"recommendation":rec})

c.execute("SELECT DISTINCT state FROM lga_coords ORDER BY state")
states = [r[0] for r in c.fetchall()]
lgas = []
if selected_state:
    c.execute("SELECT lga FROM lga_coords WHERE state=?",(selected_state,))
    lgas=[r[0] for r in c.fetchall()]
conn.close()

return render_template_string(dashboard_template, lang=lang, strings=strings, farmers=farmers,
                              states=states, lgas=lgas, selected_state=selected_state, selected_lga=selected_lga,
                              selected_name=selected_name)

@app.route('/download') def download_csv(): conn = sqlite3.connect('farmers.db') c = conn.cursor() c.execute("SELECT name,state,lga,location,crop,phone,photo_path FROM farmers") rows = c.fetchall() conn.close() path = 'farmers_data.csv' with open(path,'w',newline='',encoding='utf-8') as f: writer = csv.writer(f) writer.writerow(["Name","State","LGA","Location","Crop","Phone","Photo"]) writer.writerows(rows) return send_file(path, as_attachment=True)

if name=='main': app.run(host='0.0.0.0', port=5000)
