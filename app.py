from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import argostranslate.package
import argostranslate.translate
import os
import re
import fitz  # PyMuPDF
import docx
import pandas as pd
from urllib.parse import quote
import requests # Import the requests library

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app) # Enable Cross-Origin Resource Sharing

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Argos Translate Setup ---
print("Checking for language model updates...")
argostranslate.package.update_package_index()
available_packages = argostranslate.package.get_available_packages()
LANGUAGES_TO_INSTALL = ["en", "es", "hi"]
installed_langs = [lang.code for lang in argostranslate.translate.get_installed_languages()]
print(f"Installed languages found: {installed_langs}")
for lang_code in LANGUAGES_TO_INSTALL:
    if lang_code not in installed_langs:
        package_to_install = next(filter(lambda x: x.from_code == lang_code and x.to_code == "en", available_packages), None)
        if package_to_install:
            print(f"Downloading and installing language package: {lang_code}")
            package_to_install.install()
        else:
            print(f"Could not find package for: {lang_code}")
    else:
        print(f"Language package already installed: {lang_code}")

# --- Medical Glossary and Mappings ---
medical_glossary = {
    "fever": {"en": "fever", "hi": "बुखार", "es": "fiebre", "de": "Fieber", "fr": "fièvre"},
    "cancer": {"en": "cancer", "hi": "कैंसर", "es": "cáncer", "de": "Krebs", "fr": "cancer"},
    "headache": {"en": "headache", "hi": "सिरदर्द", "es": "dolor de cabeza", "de": "Kopfschmerzen", "fr": "mal de tête"},
    "diabetes": {"en": "diabetes", "hi": "मधुमेह", "es": "diabetes", "de": "Diabetes", "fr": "diabète"},
    "pain": {"en": "pain", "hi": "दर्द", "es": "dolor", "de": "Schmerz", "fr": "douleur"},
    "heart attack": {"en": "heart attack", "hi": "दिल का दौरा", "es": "ataque al corazón", "de": "Herzinfarkt", "fr": "crise cardiaque"},
    "cough": {"en": "cough", "hi": "खांसी", "es": "tos", "de": "Husten", "fr": "toux"},
    "fracture": {"en": "fracture", "hi": "फ्रैक्चर", "es": "fractura", "de": "Fraktur", "fr": "fracture"},
    "dizziness": {"en": "dizziness", "hi": "चक्कर", "es": "mareo", "de": "Schwindel", "fr": "vertige"},
    "nausea": {"en": "nausea", "hi": "मतली", "es": "náusea", "de": "Übelkeit", "fr": "nausée"},
    "vomiting": {"en": "vomiting", "hi": "उल्टी", "es": "vómito", "de": "Erbrechen", "fr": "vomissement"},
    "stroke": {"en": "stroke", "hi": "स्ट्रोक", "es": "derrame cerebral", "de": "Schlaganfall", "fr": "AVC"},
    "allergy": {"en": "allergy", "hi": "एलर्जी", "es": "alergia", "de": "Allergie", "fr": "allergie"},
    "infection": {"en": "infection", "hi": "संक्रमण", "es": "infección", "de": "Infektion", "fr": "infection"},
    "cold": {"en": "cold", "hi": "सर्दी", "es": ["resfriado", "frío"], "de": "Erkältung", "fr": "rhume"},
}

symptom_to_department = {
    "fever": ["General Medicine"],
    "headache": ["Neurology", "General Medicine"],
    "pain": ["General Medicine", "Orthopedics"],
    "heart attack": ["Cardiology", "Emergency"],
    "cancer": ["Oncology"],
    "diabetes": ["Endocrinology"],
    "cough": ["Pulmonology", "General Medicine"],
    "fracture": ["Orthopedics", "Emergency"],
    "dizziness": ["Neurology", "ENT"],
    "nausea": ["Gastroenterology"],
    "vomiting": ["Gastroenterology", "Emergency"],
    "stroke": ["Neurology", "Emergency"],
    "allergy": ["Allergy & Immunology"],
    "infection": ["Infectious Disease", "General Medicine"],
    "cold": ["General Medicine", "ENT"],
}

department_translations = {
    "General Medicine": {"en": "General Medicine", "hi": "सामान्य चिकित्सा", "es": "Medicina General", "de": "Allgemeinmedizin"},
    "Neurology": {"en": "Neurology", "hi": "तंत्रिका-विज्ञान", "es": "Neurología", "de": "Neurologie"},
    "Orthopedics": {"en": "Orthopedics", "hi": "हड्डी रोग", "es": "Ortopedia", "de": "Orthopädie"},
    "Emergency": {"en": "Emergency", "hi": "आपातकालीन", "es": "Emerencia", "de": "Notaufnahme"},
    "Cardiology": {"en": "Cardiology", "hi": "हृदय रोग विज्ञान", "es": "Cardiología", "de": "Kardiologie"},
    "Oncology": {"en": "Oncology", "hi": "कैंसर विज्ञान", "es": "Oncología", "de": "Onkologie"},
    "Endocrinology": {"en": "Endocrinology", "hi": "अंतःस्त्राविका", "es": "Endocrinología", "de": "Endokrinologie"},
    "Pulmonology": {"en": "Pulmonology", "hi": "फेफड़ा विज्ञान", "es": "Neumología", "de": "Pneumologie"},
    "ENT": {"en": "ENT", "hi": "ईएनटी", "es": "Otorrinolaringología", "de": "HNO"},
    "Gastroenterology": {"en": "Gastroenterology", "hi": "जठरांत्र विज्ञान", "es": "Gastroenterología", "de": "Gastroenterologie"},
    "Allergy & Immunology": {"en": "Allergy & Immunology", "hi": "एलर्जी और इम्यूनोलॉजी", "es": "Alergia e Inmunología", "de": "Allergologie und Immunologie"},
    "Infectious Disease": {"en": "Infectious Disease", "hi": "संक्रामक रोग", "es": "Enfermedades Infecciosas", "de": "Infektionskrankheiten"},
}

# --- Helper Functions ---
def find_medical_keywords(text, source_lang):
    found_keywords = []
    lower_text = text.lower()
    for english_term, translations in medical_glossary.items():
        if source_lang in translations:
            terms_to_find = translations[source_lang]
            if not isinstance(terms_to_find, list):
                terms_to_find = [terms_to_find]
            for term in terms_to_find:
                pattern = r'\b' + r'\s*'.join(re.escape(word) for word in term.lower().split()) + r'\b'
                if re.search(pattern, lower_text):
                    found_keywords.append(english_term)
                    break 
    return list(set(found_keywords))

def process_file(filepath):
    _, extension = os.path.splitext(filepath)
    text = ""
    try:
        if extension == '.pdf':
            with fitz.open(filepath) as doc:
                for page in doc:
                    text += page.get_text()
        elif extension == '.docx':
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + '\n'
        elif extension == '.csv':
            df = pd.read_csv(filepath)
            text = df.to_string()
        elif extension == '.txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            return "Unsupported file type."
    except Exception as e:
        print(f"Error processing file {filepath}: {e}")
        return f"Error reading file: {e}"
    return text

# --- API Endpoints ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/languages', methods=['GET'])
def get_languages():
    installed_languages = argostranslate.translate.get_installed_languages()
    lang_list = [{"name": lang.name, "code": lang.code} for lang in installed_languages]
    return jsonify(lang_list)

@app.route('/api/translate', methods=['POST'])
def translate_text_route():
    data = request.get_json()
    text_to_translate = data.get('text')
    source_lang = data.get('source_lang', 'en')
    target_lang = data.get('target_lang', 'es')
    if not text_to_translate.strip():
        return jsonify({"translated_text": "", "keywords": [], "recommendations": []})
    try:
        keywords_in_english = find_medical_keywords(text_to_translate, source_lang)
        translated_text = argostranslate.translate.translate(text_to_translate, source_lang, target_lang)
        keywords_data = []
        if keywords_in_english:
            for english_keyword in keywords_in_english:
                query = f'"{english_keyword}" medical diagram anatomy'
                search_url = f"https://www.google.com/search?tbm=isch&q={quote(query)}"
                if target_lang in medical_glossary.get(english_keyword, {}):
                    translated_terms = medical_glossary[english_keyword][target_lang]
                    if not isinstance(translated_terms, list):
                        translated_terms = [translated_terms]
                    for term in translated_terms:
                        pattern = r'\b' + re.escape(term) + r'\w*\b'
                        match = re.search(pattern, translated_text, re.IGNORECASE)
                        if match:
                            actual_term_in_text = match.group(0)
                            keywords_data.append({"term": actual_term_in_text, "english": english_keyword, "visual_aid_search": search_url})
                            break
        recommendations = []
        if keywords_in_english:
            departments = set()
            for keyword in keywords_in_english:
                if keyword in symptom_to_department:
                    for dept in symptom_to_department[keyword]:
                        departments.add(dept)
            for dept in departments:
                if target_lang in department_translations.get(dept, {}):
                    recommendations.append(department_translations[dept][target_lang])
        return jsonify({"translated_text": translated_text, "keywords": keywords_data, "recommendations": recommendations})
    except Exception as e:
        print(f"Translation Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/translate-file', methods=['POST'])
def translate_file_route():
    if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({'error': 'No selected file'}), 400
    try:
        target_lang = request.form.get('target_lang', 'es')
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        processed_text = process_file(filepath)
        source_lang_of_file = 'en'
        keywords_in_english = find_medical_keywords(processed_text, source_lang_of_file)
        translated_text = argostranslate.translate.translate(processed_text, source_lang_of_file, target_lang)
        keywords_data = []
        if keywords_in_english:
            for english_keyword in keywords_in_english:
                query = f'"{english_keyword}" medical diagram anatomy'
                search_url = f"https://www.google.com/search?tbm=isch&q={quote(query)}"
                if target_lang in medical_glossary.get(english_keyword, {}):
                    translated_terms = medical_glossary[english_keyword][target_lang]
                    if not isinstance(translated_terms, list):
                        translated_terms = [translated_terms]
                    for term in translated_terms:
                        pattern = r'\b' + re.escape(term) + r'\w*\b'
                        match = re.search(pattern, translated_text, re.IGNORECASE)
                        if match:
                            actual_term_in_text = match.group(0)
                            keywords_data.append({"term": actual_term_in_text, "english": english_keyword, "visual_aid_search": search_url})
                            break
        os.remove(filepath)
        return jsonify({'translated_text': translated_text, 'keywords': keywords_data})
    except Exception as e:
        print(f"File Translation Error: {e}")
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

@app.route('/api/nearby-hospitals-osm', methods=['POST'])
def nearby_hospitals_osm():
    data = request.get_json()
    if not data or 'lat' not in data or 'lon' not in data:
        return jsonify({"error": "Latitude or longitude not provided"}), 400
    lat = data['lat']
    lon = data['lon']
    overpass_query = f"""
    [out:json];(node["amenity"="hospital"](around:10000,{lat},{lon});way["amenity"="hospital"](around:10000,{lat},{lon});relation["amenity"="hospital"](around:10000,{lat},{lon}););out center;
    """
    overpass_url = "http://overpass-api.de/api/interpreter"
    try:
        response = requests.post(overpass_url, data=overpass_query)
        response.raise_for_status()
        hospital_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Overpass API Error: {e}")
        return jsonify({"error": "Could not connect to map service to find hospitals."}), 500
    hospitals = []
    for element in hospital_data.get('elements', []):
        tags = element.get('tags', {})
        name = tags.get('name', 'Unnamed Hospital')
        if element['type'] == 'node':
            h_lat, h_lon = element.get('lat'), element.get('lon')
        else:
            center = element.get('center', {})
            h_lat, h_lon = center.get('lat'), center.get('lon')
        if h_lat and h_lon:
            hospitals.append({"id": element['id'], "name": name, "lat": h_lat, "lon": h_lon})
    if not hospitals:
        return jsonify({"error": "No hospitals found nearby."}), 404
    osrm_base_url = "http://router.project-osrm.org/route/v1/driving/"
    results = []
    for hospital in hospitals[:5]:
        try:
            coords = f"{lon},{lat};{hospital['lon']},{hospital['lat']}"
            osrm_url = f"{osrm_base_url}{coords}?overview=full&geometries=geojson"
            route_response = requests.get(osrm_url)
            route_response.raise_for_status()
            route_data = route_response.json()
            if route_data['code'] == 'Ok' and route_data.get('routes'):
                route_info = route_data['routes'][0]
                hospital['distance'] = route_info.get('distance', 0)
                hospital['duration'] = route_info.get('duration', 0)
                hospital['geometry'] = route_info.get('geometry')
                results.append(hospital)
        except requests.exceptions.RequestException as e:
            print(f"OSRM API Error for {hospital['name']}: {e}")
            hospital['distance'] = -1
            hospital['duration'] = -1
            results.append(hospital)
    results.sort(key=lambda x: x.get('distance', float('inf')))
    return jsonify(results)

# --- Main Execution ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
