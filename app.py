from flask import Flask, render_template_string, request, send_file
import sqlite3, os, csv, random
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/photos'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# === Initialize database with full Nigerian States + LGAs ===
def init_db():
    conn = sqlite3.connect('farmers.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS farmers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        state TEXT,
        lga TEXT,
        location TEXT,
        crop TEXT,
        phone TEXT,
        photo_path TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS lga_coords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        state TEXT,
        lga TEXT
    )''')

    c.execute("SELECT COUNT(*) FROM lga_coords")
    if c.fetchone()[0]==0:
        # Full Nigeria States + LGAs dictionary (shortened for brevity, fill all)
        all_locations = {
            "Abia": ["Aba North","Aba South","Umuahia North","Umuahia South"],
            "Adamawa": ["Yola North","Yola South"],
            "FCT": ["Abaji","AMAC","Bwari","Gwagwalada","Kuje","Kwali"],
            # ... add all remaining states + LGAs
        }
        for state, lgas in all_locations.items():
            for lga in lgas:
                c.execute("INSERT INTO lga_coords(state,lga) VALUES (?,?)", (state,lga))
        conn.commit()
    conn.close()

init_db()

# === Multi-language strings ===
lang_dict = {
    "en": {"title":"Farmers Registration Form","full_name":"Full Name","state":"State",
           "lga":"Local Government Area (LGA)","location":"Farming Location","crop":"Type of Crop",
           "phone":"Phone Number","submit":"Submit","select_state":"Select State","select_lga":"Select LGA",
           "data_saved":"Data saved successfully!","dashboard":"Dashboard","filter_state":"Filter by State",
           "filter_lga":"Filter by LGA","weather_alert":"Weather / Flood Alert","recommended_crop":"Recommended Crop"},
    "ha": {"title":"Fom ɗin Rijistar Manoma","full_name":"Cikakken Suna","state":"Jihar",
           "lga":"Karamar Hukuma (LGA)","location":"Wurin Noma","crop":"Irin Amfanin Gona",
           "phone":"Lambar Waya","submit":"Tura","select_state":"Zaɓi Jihar","select_lga":"Zaɓi LGA",
           "data_saved":"An adana bayananka cikin nasara!","dashboard":"Dashboard","filter_state":"Filter Jihar",
           "filter_lga":"Filter LGA","weather_alert":"Yanayi / Ambaliya","recommended_crop":"Amfanin gona da ya dace"}
}

# === HTML templates ===
form_template = """<!DOCTYPE html><html lang='{{lang}}'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>{{strings['title']}}</title><style>body{font-family:Arial;background:#f5f5f5;padding:20px;} .card{background:white;padding:20px;border-radius:10px;max-width:500px;margin:auto;box-shadow:0 0 10px #ccc;} input,select,button{width:100%;padding:10px;margin-top:8px;border-radius:5px;border:1px solid #ccc;} button{background:green;color:white;font-weight:bold;} img{max-width:100px;border-radius:5px;margin:5px;}</style></head><body><div class='card'><h2>{{strings['title']}}</h2><form method='POST' enctype='multipart/form-data'><label>{{strings['full_name']}}</label><input type='text' name='name' required><label>{{strings['state']}}</label><select name='state' id='state' required onchange='populateLGAs()'><option value=''>{{strings['select_state']}}</option>{% for s in states %}<option value='{{s}}'>{{s}}</option>{% endfor %}</select><label>{{strings['lga']}}</label><select name='lga' id='lga' required><option value=''>{{strings['select_lga']}}</option></select><label>{{strings['location']}}</label><input type='text' name='location' required><label>{{strings['crop']}}</label><input type='text' name='crop' required><label>{{strings['phone']}}</label><input type='text' name='phone' required><label>Photo</label><input type='file' name='photo' accept='image/*' required><button type='submit'>{{strings['submit']}}</button></form>{% if success %}<p style='color:green;'>{{strings['data_saved']}}</p>{% endif %}<p><a href='/dashboard?lang={{lang}}'>{{strings['dashboard']}}</a> | <a href='/download'>Download CSV</a></p><p>Language: <a href='/?lang=en'>EN</a> | <a href='/?lang=ha'>HA</a></p><script>const lga_data={{ lga_json|
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
