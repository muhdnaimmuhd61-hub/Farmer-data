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
    # Farmers table
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
    if c.fetchone()[0] == 0:
    print("Babu sakamakon da aka samu")
# Multi-language
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
    all_locations = {
    "Abia": ["Aba North","Aba South","Umuahia North","Umuahia South","Isiala Ngwa North","Isiala Ngwa South",
             "Isuikwuato","Obi Ngwa","Ohafia","Arochukwu","Bende","Ugwunagbo","Ukwa East","Ukwa West"],
    "Adamawa": ["Demsa","Fufore","Ganye","Girei","Gombi","Guyuk","Hong","Jada","Lamurde","Madagali",
                "Maiha","Mayo Belwa","Michika","Mubi North","Mubi South","Numan","Shelleng","Song","Toungo","Yola North","Yola South"],
    "Akwa Ibom": ["Abak","Eastern Obolo","Eket","Esit Eket","Essien Udim","Etim Ekpo","Etinan","Ibeno",
                  "Ibesikpo Asutan","Ibiono-Ibom","Ikono","Ikot Abasi","Ikot Ekpene","Ini","Itu","Mbo",
                  "Mkpat-Enin","Nsit-Atai","Nsit-Ibom","Nsit-Ubium","Obot Akara","Okobo","Onna","Oron",
                  "Oruk Anam","Udung-Uko","Ukanafun","Uruan","Urue-Offong/Oruko","Uyo"],
    "Anambra": ["Aguata","Anambra East","Anambra West","Anaocha","Awka North","Awka South","Ayamelum",
                "Dunukofia","Ekwusigo","Idemili North","Idemili South","Ihiala","Njikoka","Nnewi North",
                "Nnewi South","Ogbaru","Onitsha North","Onitsha South","Orumba North","Orumba South","Oyi"],
    "Bauchi": ["Alkaleri","Bauchi","Bogoro","Damban","Darazo","Dass","Gamawa","Ganjuwa","Giade",
               "Itas/Gadau","Jamaare","Katagum","Kirfi","Misau","Ningi","Shira","Tafawa Balewa","Toro","Warji","Zaki"],
    "Bayelsa": ["Brass","Ekeremor","Kolokuma/Opokuma","Nembe","Ogbia","Sagbama","Southern Ijaw","Yenagoa"],
    "Benue": ["Ado","Agatu","Apa","Buruku","Gboko","Guma","Gwer East","Gwer West","Katsina-Ala",
              "Konshisha","Kwande","Logo","Makurdi","Obi","Ogbadibo","Ohimini","Oju","Okpokwu","Otukpo","Tarka","Ukum","Vandeikya"],
    "Borno": ["Abadam","Askira/Uba","Bama","Bayo","Biu","Chibok","Damboa","Dikwa","Gubio","Guzamala",
              "Gwoza","Hawul","Jere","Kaga","Kala/Balge","Konduga","Kukawa","Kwaya Kusar","Mafa","Magumeri",
              "Maiduguri","Marte","Mobbar","Monguno","Ngala","Nganzai","Shani"],
    "Cross River": ["Abi","Akamkpa","Akpabuyo","Bakassi","Bekwarra","Biase","Boki","Calabar Municipal","Calabar South",
                     "Etung","Ikom","Obanliku","Obubra","Obudu","Odukpani","Ogoja","Yakuur","Bekwarra"],
    "Delta": ["Aniocha North","Aniocha South","Bomadi","Burutu","Ethiope East","Ethiope West","Ika North East",
              "Ika South","Isoko North","Isoko South","Ndokwa East","Ndokwa West","Okpe","Oshimili North","Oshimili South",
              "Patani","Sapele","Udu","Ughelli North","Ughelli South","Ukwuani","Uvwie","Warri North","Warri South","Warri South West"],
    "Ebonyi": ["Abakaliki","Afikpo North","Afikpo South","Ebonyi","Ezza North","Ezza South","Ikwo","Ishielu",
               "Ivo","Izzi","Ohaozara","Ohaukwu","Onicha"],
    "Edo": ["Akoko-Edo","Egor","Esan Central","Esan North-East","Esan South-East","Esan West","Etsako Central",
            "Etsako East","Etsako West","Igueben","Ikpoba-Okha","Oredo","Orhionmwon","Ovia North-East","Ovia South-West","Owan East","Owan West","Uhunmwonde"],
    "Ekiti": ["Ado-Ekiti","Efon","Ekiti East","Ekiti South-West","Ekiti West","Emure","Gbonyin","Ido-Osi",
              "Ijero","Ikere","Ikole","Ilejemeje","Irepodun/Ifelodun","Ise/Orun","Moba","Oye"],
    "Enugu": ["Awgu","Enugu East","Enugu North","Enugu South","Ezeagu","Igbo Etiti","Igbo Eze North",
              "Igbo Eze South","Isi Uzo","Nkanu East","Nkanu West","Nsukka","Oji River","Udenu","Udi","Uzo-Uwani"],
    "Gombe": ["Akko","Balanga","Billiri","Dukku","Funakaye","Gombe","Kaltungo","Kwami","Nafada/Bajoga","Shongom","Yamaltu/Deba"],
    "Imo": ["Aboh Mbaise","Ahiazu Mbaise","Ehime Mbano","Ezinihitte","Ideato North","Ideato South","Ihitte/Uboma",
            "Ikeduru","Isiala Mbano","Isu","Mbaitoli","Ngor Okpala","Njaba","Nkwerre","Nwangele","Obowo","Oguta","Ohaji/Egbema","Okigwe","Onuimo","Orlu","Orsu","Oru East","Oru West","Owerri Municipal","Owerri North","Owerri West"],
    "Jigawa": ["Auyo","Babura","Biriniwa","Birnin Kudu","Buji","Dutse","Gagarawa","Garki","Gumel","Guri",
               "Gwaram","Gwiwa","Hadejia","Jahun","Kafin Hausa","Kaugama","Kazaure","Kiri Kasama","Kiyawa","Maigatari",
               "Malam Madori","Miga","Ringim","Roni","Sule Tankarkar","Taura","Yankwashi"],
    "Kaduna": ["Birnin Gwari","Chikun","Giwa","Igabi","Ikara","Jaba","Jema'a","Kachia","Kaduna North","Kaduna South",
               "Kagarko","Kajuru","Kaura","Kauru","Kubau","Kudan","Lere","Makarfi","Sabon Gari","Sanga","Soba","Zangon Kataf","Zaria"],
    "Kano": ["Ajingi","Albasu","Bagwai","Bebeji","Bichi","Bunkure","Dala","Dambatta","Dawakin Kudu","Dawakin Tofa",
             "Doguwa","Fagge","Gabasawa","Garko","Garun Mallam","Gaya","Gezawa","Gwale","Gwarzo","Kabo",
             "Kano Municipal","Karaye","Kibiya","Kiru","Kumbotso","Kunchi","Kura","Madobi","Makoda","Minjibir",
             "Nasarawa","Rano","Rimin Gado","Rogo","Shanono","Sumaila","Takai","Tarauni","Tofa","Tsanyawa","Tudun Wada","Ungogo","Warawa","Wudil"],
    "Katsina": ["Bakori","Batagarawa","Batsari","Baure","Bindawa","Charanchi","Dandume","Danja","Daura",
                "Dutsi","Dutsin Ma","Faskari","Funtua","Ingawa","Jibia","Kafur","Kaita","Kankara","Kankia","Katsina",
                "Kurfi","Kusada","Mai Adua","Malumfashi","Mani","Mashi","Matazu","Musawa","Rimi","Sabuwa","Safana","Sandamu","Zango"],
    "Kebbi": ["Aleiro","Arewa Dandi","Argungu","Augie","Bagudo","Birnin Kebbi","Bunza","Dandi","Fakai","Gwandu",
              "Jega","Kalgo","Koko/Besse","Maiyama","Ngaski","Sakaba","Shanga","Suru","Wasagu/Danko","Yauri","Zuru"],
    "Kogi": ["Adavi","Ajaokuta","Ankpa","Bassa","Dekina","Ibaji","Idah","Igalamela-Odolu","Ijumu","Kabba/Bunu",
             "Kogi","Lokoja","Mopa-Muro","Ofu","Ogori/Magongo","Okehi","Okene","Olamaboro","Omala","Yagba East","Yagba West"],
    "Kwara": ["Asa","Baruten","Edu","Ekiti","Ifelodun","Ilorin East","Ilorin South","Ilorin West","Irepodun",
              "Isin","Kaiama","Moro","Offa","Oke Ero","Oyun","Pategi"],
    "Lagos": ["Agege","Ajeromi-Ifelodun","Alimosho","Amuwo-Odofin","Apapa","Badagry","Epe","Eti Osa","Ibeju-Lekki",
              "Ifako-Ijaiye","Ikeja","Ikorodu","Kosofe","Lagos Island","Lagos Mainland","Mushin","Ojo","Oshodi-Isolo",
              "Shomolu","Surulere"],
    "Nasarawa": ["Akwanga","Awe","Doma","Karu","Keana","Keffi","Kokona","Lafia","Nasarawa","Nasarawa Egon",
                 "Obi","Toto","Wamba"],
    "Niger": ["Agaie","Agwara","Bida","Borgu","Bosso","Chanchaga","Edati","Gbako","Gurara","Katcha","Kontagora",
              "Lapai","Lavun","Magama","Mariga","Mashegu","Mokwa","Muya","Paikoro","Rafi","Rijau","Shiroro","Suleja","Tafa","Wushishi"],
    "Ogun": ["Abeokuta North","Abeokuta South","Ado-Odo/Ota","Egbado North","Egbado South","Ewekoro","Ifo","Ijebu East",
             "Ijebu North","Ijebu North East","Ijebu Ode","Ikenne","Imeko Afon","Ipokia","Obafemi-Owode","Odeda",
             "Odogbolu","Ogun Waterside","Remo North","Shagamu"],
    "Ondo": ["Akoko North-East","Akoko North-West","Akoko South-East","Akoko South-West","Akure North","Akure South",
             "Ese Odo","Idanre","Ifedore","Ilaje","Ile Oluji/Okeigbo","Irele","Odigbo","Okitipupa","Ondo East",
             "Ondo West","Ose","Owo"],
    "Osun": ["Aiyedade","Aiyedire","Atakunmosa East","Atakunmosa West","Boluwaduro","Boripe","Ede North","Ede South",
             "Egbedore","Ejigbo","Ife Central","Ife East","Ife North","Ife South","Ifedayo","Ifelodun","Ila","Ilesa East",
             "Ilesa West","Irepodun","Irewole","Isokan","Iwo","Obokun","Odo Otin","Ola Oluwa","Olorunda","Oriade",
             "Orolu","Osogbo"],
    "Oyo": ["Afijio","Akinyele","Atiba","Atisbo","Egbeda","Ibadan North","Ibadan North-East","Ibadan North-West",
            "Ibadan South-East","Ibadan South-West","Ibarapa Central","Ibarapa East","Ibarapa North","Ido","Irepo",
            "Iseyin","Itesiwaju","Iwajowa","Kajola","Lagelu","Ogbomosho North","Ogbomosho South","Ogo Oluwa",
            "Olorunsogo","Oluyole","Ona Ara","Orelope","Orire","Oru","Oyo East","Oyo West","Saki East","Saki West","Surulere"],
    "Plateau": ["Barkin Ladi","Bassa","Bokkos","Jos East","Jos North","Jos South","Kanam","Kanke","Langtang North",
                "Langtang South","Mangu","Mikang","Pankshin","Qua'an Pan","Riyom","Shendam","Wase"],
    "Rivers": ["Abua/Odual","Ahoada East","Ahoada West","Akuku-Toru","Andoni","Asari-Toru","Bonny","Degema","Eleme",
               "Emohua","Etche","Gokana","Ikwerre","Khana","Obio/Akpor","Ogba/Egbema/Ndoni","Ogu/Bolo","Okrika",
               "Omuma","Opobo/Nkoro","Oyigbo","Port Harcourt","Tai"],
    "Sokoto": ["Binji","Bodinga","Dange Shuni","Gada","Goronyo","Gudu","Gwadabawa","Illela","Kebbe","Kware",
               "Rabah","Sabon Birni","Shagari","Sokoto North","Sokoto South","Tambuwal","Tangaza","Tureta","Wamako","Wurno","Yabo"],
    "Taraba": ["Ardo Kola","Bali","Donga","Gashaka","Gassol","Ibi","Jalingo","Karim Lamido","Kumi","Lau","Sardauna",
               "Takum","Ussa","Wukari","Yorro","Zing"],
    "Yobe": ["Bade","Bursari","Damaturu","Fika","Fune","Geidam","Gujba","Gulani","Jakusko","Karasuwa","Machina",
             "Nangere","Nguru","Potiskum","Tarmuwa","Yunusari","Yusufari"],
    "Zamfara": ["Anka","Bakura","Birnin Magaji/Kiyaw","Bukkuyum","Bungudu","Gummi","Gusau","Kaura Namoda","Maradun",
                "Maru","Shinkafi","Talata Mafara","Tsafe","Zurmi"],
    "FCT": ["Abaji","Bwari","Gwagwalada","Kuje","Kwali","AMAC"]
}
