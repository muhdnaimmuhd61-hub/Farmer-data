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
        states_lgas = [
    {"state":"Abia","lgas":["Aba North","Aba South","Arochukwu","Bende","Ikwuano","Isiala Ngwa North","Isiala Ngwa South","Isuikwuato","Obi Ngwa","Ohafia","Osisioma","Umuahia North","Umuahia South","Umu Nneochi"]},
    {"state":"Adamawa","lgas":["Demsa","Fufure","Ganye","Girei","Gombi","Guyuk","Hong","Jada","Lamurde","Madagali","Maiha","Mayo Belwa","Michika","Mubi North","Mubi South","Numan","Shelleng","Song","Toungo","Yola North","Yola South"]},
    {"state":"Akwa Ibom","lgas":["Abak","Eastern Obolo","Eket","Esit Eket","Essien Udim","Etim Ekpo","Etinan","Ibeno","Ibesikpo Asutan","Ibiono Ibom","Ikono","Ikot Abasi","Ikot Ekpene","Ini","Itu","Mbo","Mkpat Enin","Nsit Atai","Nsit Ibom","Nsit Ubium","Obot Akara","Okobo","Onna","Oron","Oruk Anam","Udung Uko","Ukanafun","Uruan","Urue-Offong/Oruko","Uyo"]},
    {"state":"Anambra","lgas":["Aguata","Anambra East","Anambra West","Anaocha","Awka North","Awka South","Ayamelum","Dunukofia","Ekwusigo","Idemili North","Idemili South","Ihiala","Njikoka","Nnewi North","Nnewi South","Ogbaru","Onitsha North","Onitsha South","Orumba North","Orumba South","Oyi"]},
    {"state":"Bauchi","lgas":["Bauchi","Bogoro","Damban","Darazo","Dass","Gamawa","Ganjuwa","Giade","Itas/Gadau","Jama’are","Katagum","Kirfi","Misau","Ningi","Shira","Tafawa Balewa","Toro","Warji","Zaki"]},
    {"state":"Bayelsa","lgas":["Brass","Ekeremor","Kolokuma/Opokuma","Nembe","Ogbia","Sagbama","Southern Ijaw","Yenagoa"]},
    {"state":"Benue","lgas":["Ado","Agatu","Apa","Buruku","Gboko","Guma","Gwer East","Gwer West","Katsina-Ala","Konshisha","Kwande","Logo","Makurdi","Obi","Ogbadibo","Ohimini","Oju","Okpokwu","Otukpo","Tarka","Ukum","Vandeikya"]},
    {"state":"Borno","lgas":["Abadam","Askira/Uba","Bama","Bayo","Biu","Chibok","Damboa","Dikwa","Gubio","Guzamala","Gwoza","Hawul","Jere","Kaga","Kala/Balge","Konduga","Kukawa","Kwaya Kusar","Mafa","Magumeri","Maiduguri","Marte","Mobbar","Monguno","Ngala","Nganzai","Shani"]},
    {"state":"Cross River","lgas":["Akpabuyo","Odukpani","Akamkpa","Biase","Abi","Ikom","Obanliku","Obubra","Obudu","Ogoja","Yala","Bekwara","Bakassi","Calabar Municipal","Calabar South","Etung","Boki","Tarkwa Bay"]},
    {"state":"Delta","lgas":["Oshimili North","Oshimili South","Aniocha North","Aniocha South","Ika North East","Ika South","Ndokwa East","Ndokwa West","Isoko North","Isoko South","Okpe","Oshimili South","Sapele","Udu","Ughelli North","Ughelli South","Uvwie","Warri North","Warri South","Warri South West"]},
    {"state":"Ebonyi","lgas":["Abakaliki","Afikpo North","Afikpo South","Ebonyi","Ezza North","Ezza South","Ikwo","Ishielu","Ivo","Izzi","Ohaozara","Ohaukwu","Onicha"]},
    {"state":"Edo","lgas":["Akoko-Edo","Egor","Esan Central","Esan North-East","Esan South-East","Esan West","Etsako Central","Etsako East","Etsako West","Igueben","Ikpoba-Okha","Oredo","Orhionmwon","Ovia North-East","Ovia South-West","Owan East","Owan West","Uhunmwonde"]},
    {"state":"Ekiti","lgas":["Ado","Efon","Ekiti East","Ekiti South-West","Ekiti West","Emure","Gbonyin","Ido-Osi","Ijero","Ikere","Ikole","Ilejemeje","Irepodun/Ifelodun","Ise/Orun","Moba","Oye"]},
    {"state":"Enugu","lgas":["Enugu East","Enugu North","Enugu South","Ezeagu","Igbo Etiti","Igbo Eze North","Igbo Eze South","Isi Uzo","Nkanu East","Nkanu West","Nsukka","Oji River","Udenu","Udi","Uzo Uwani"]},
    {"state":"Gombe","lgas":["Akko","Balanga","Billiri","Dukku","Funakaye","Gombe","Kaltungo","Kwami","Nafada/Bajoga","Shongom","Yamaltu/Deba"]},
    {"state":"Imo","lgas":["Aboh Mbaise","Ahiazu Mbaise","Ehime Mbano","Ezinihitte","Ideato North","Ideato South","Ihitte/Uboma","Ikeduru","Isiala Mbano","Isu","Mbaitoli","Ngor Okpala","Njaba","Nkwerre","Nwangele","Obowo","Oguta","Ohaji/Egbema","Okigwe","Orlu","Orsu","Oru East","Oru West","Owerri Municipal","Owerri North","Owerri West"]},
    {"state":"Jigawa","lgas":["Auyo","Babura","Biriniwa","Birnin Kudu","Buji","Dutse","Gagarawa","Garki","Gumel","Guri","Gwaram","Gwiwa","Hadejia","Jahun","Kafin Hausa","Kaugama","Kazaure","Kiri Kasama","Kiyawa","Maigatari","Malam Madori","Miga","Ringim","Roni","Sule Tankarkar","Taura","Yankwashi"]},
    {"state":"Kaduna","lgas":["Birnin Gwari","Chikun","Giwa","Igabi","Ikara","Jaba","Jema’a","Kachia","Kaduna North","Kaduna South","Kagarko","Kajuru","Kaura","Kauru","Kubau","Kudan","Lere","Makarfi","Sabon Gari","Sanga","Soba","Zangon Kataf","Zaria"]},
    {"state":"Kano","lgas":["Ajingi","Albasu","Bagwai","Bebeji","Bichi","Bunkure","Dala","Dambatta","Dawakin Kudu","Dawakin Tofa","Doguwa","Fagge","Gabasawa","Garko","Garun Mallam","Gaya","Gezawa","Gwale","Gwarzo","Kabo","Kano Municipal","Karaye","Kibiya","Kiru","Kumbotso","Kunchi","Kura","Madobi","Makoda","Minjibir","Nasarawa","Rano","Rimin Gado","Rogo","Shanono","Sumaila","Takai","Tarauni","Tofa","Tsanyawa","Tudun Wada","Ungogo","Warawa","Wudil"]},
    {"state":"Katsina","lgas":["Bakori","Batagarawa","Batsari","Baure","Bindawa","Charanchi","Dandume","Danja","Dan Musa","Daura","Dutsi","Dutsin Ma","Faskari","Funtua","Ingawa","Jibia","Kafur","Kaita","Kankara","Kankia","Katsina","Kurfi","Kusada","Mai’Adua","Malumfashi","Mani","Mashi","Matazu","Musawa","Rimi","Sabuwa","Safana","Sandamu","Zango"]},
    {"state":"Kebbi","lgas":["Aleiro","Arewa Dandi","Argungu","Augie","Bagudo","Birnin Kebbi","Bunza","Dandi","Fakai","Gwandu","Jega","Kalgo","Koko/Besse","Maiyama","Ngaski","Sakaba","Shanga","Suru","Wasagu/Danko","Yauri","Zuru"]},
    {"state":"Kogi","lgas":["Adavi","Ajaokuta","Ankpa","Bassa","Dekina","Ibaji","Idah","Ijumu","Kabba/Bunu","Kogi","Lokoja","Mopa-Muro","Ofu","Ogori/Magongo","Okehi","Okene","Olamaboro","Omala","Yagba East","Yagba West"]},
    {"state":"Kwara","lgas":["Asa","Baruten","Edu","Ekiti","Ifelodun","Ilorin East","Ilorin South","Ilorin West","Irepodun","Isin","Kaiama","Moro","Offa","Oke Ero","Oyun","Pategi"]},
    {"state":"Lagos","lgas":["Agege","Ajeromi-Ifelodun","Alimosho","Amuwo-Odofin","Apapa","Badagry","Epe","Eti-Osa","Ibeju-Lekki","Ifako-Ijaiye","Ikeja","Ikorodu","Kosofe","Lagos Island","Lagos Mainland","Mushin","Ojo","Oshodi-Isolo","Shomolu","Surulere"]},
    {"state":"Nasarawa","lgas":["Akwanga","Awe","Doma","Karu","Keana","Keffi","Kokona","Lafia","Nasarawa","Nasarawa Egon","Obi","Toto","Wamba"]},
    {"state":"Niger","lgas":["Agaie","Agwara","Bida","Borgu","Bosso","Chanchaga","Edati","Gbako","Gurara","Katcha","Kontagora","Lapai","Lavun","Magama","Mariga","Mashegu","Mokwa","Muya","Paikoro","Rafi","Rijau","Shiroro","Suleja","Tafa","Wushishi"]},
    {"state":"Ogun","lgas":["Abeokuta North","Abeokuta South","Ado-Odo/Ota","Egbado North","Egbado South","Ewekoro","Ifo","Ijebu East","Ijebu North","Ijebu North East","Ijebu Ode","Ikenne","Imeko Afon","Ipokia","Obafemi-Owode","Odogbolu","Ogun Waterside","Remo North","Shagamu"]},
    {"state":"Ondo","lgas":["Akoko North-East","Akoko North-West","Akoko South-East","Akoko South-West","Akure North","Akure South","Ese Odo","Idanre","Ifedore","Ilaje","Ile Oluji/Okeigbo","Irele","Odigbo","Okitipupa","Ondo East","Ondo West","Ose","Owo"]},
    {"state":"Osun","lgas":["Aiyedaade","Aiyedire","Atakumosa East","Atakumosa West","Boluwaduro","Boripe","Ede North","Ede South","Egbedore","Ejigbo","Ife Central","Ife East","Ife North","Ife South","Ifedayo","Ifelodun","Ila","Ilesa East","Ilesa West","Irepodun","Irewole","Isokan","Iwo","Obokun","Odo Otin","Ola Oluwa","Olorunda","Oriade","Orolu","Osogbo"]},
    {"state":"Oyo","lgas":["Afijio","Akinyele","Atiba","Atisbo","Egbeda","Ibadan North","Ibadan North-East","Ibadan North-West","Ibadan South-East","Ibadan South-West","Ibarapa Central","Ibarapa East","Ibarapa North","Ido","Irepo","Iseyin","Itesiwaju","Iwajowa","Kajola","Lagelu","Ogbomosho North","Ogbomosho South","Ogo Oluwa","Olorunsogo","Oluyole","Ona Ara","Orelope","Ori Ire","Oyo","Oyo East","Saki East","Saki West","Surulere"]},
    {"state":"Plateau","lgas":["Barkin Ladi","Bassa","Bokkos","Jos East","Jos North","Jos South","Kanam","Kanke","Langtang North","Langtang South","Mangu","Mikang","Pankshin","Qua’an Pan","Riyom","Shendam","Wase"]},
    {"state":"Rivers","lgas":["Abua/Odual","Ahoada East","Ahoada West","Akuku-Toru","Andoni","Asari-Toru","Bonny","Degema","Eleme","Emohua","Etche","Gokana","Ikwerre","Khana","Obio/Akpor","Ogba/Egbema/Ndoni","Ogu/Bolo","Okrika","Omuma","Opobo/Nkoro","Oyigbo","Port Harcourt","Tai"]},
    {"state":"Sokoto","lgas":["Binji","Bodinga","Dange Shuni","Gada","Goronyo","Gudu","Gwadabawa","Illela","Isa","Kebbe","Kware","Rabah","Sabon Birni","Shagari","Silame","Sokoto North","Sokoto South","Tambuwal","Tangaza","Tureta","Wamako","Wurno","Yabo"]},
    {"state":"Taraba","lgas":["Ardo Kola","Bali","Donga","Gashaka","Gassol","Ibi","Jalingo","Karim Lamido","Kumi","Lau","Sardauna","Takum","Ussa","Wukari","Yorro","Zing"]},
    {"state":"Yobe","lgas":["Bade","Bursari","Damaturu","Fika","Fune","Geidam","Gujba","Gulani","Jakusko","Karasuwa","Machina","Nangere","Nguru","Potiskum","Tarmuwa","Yunusari","Yusufari"]},
    {"state":"Zamfara","lgas":["Anka","Bakura","Birnin Magaji/Kiyaw","Bukkuyum","Bungudu","Gummi","Gusau","Kaura Namoda","Maradun","Maru","Shinkafi","Talata Mafara","Chafe","Zurmi"]}
]
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
