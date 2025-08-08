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
import requests
from PIL import Image
import io

# --- Google Gemini API Integration ---
# To use this, you must install the library: pip install -q google-generativeai
# Then, get your API key from Google AI Studio and set it here.
import google.generativeai as genai

# --- PLEASE CONFIGURE YOUR API KEY HERE ---
# It is strongly recommended to use environment variables for security.
# For example: genai.configure(api_key=os.environ["GEMINI_API_KEY"])
try:
    # Replace "YOUR_API_KEY" with your actual Google Gemini API key
    genai.configure(api_key="AIzaSyDfLuKcudtSD2FIZ8LTwytkeqiFPL_cG4Q") 
    # Initialize the Gemini Pro Vision model
    # Replace it with this line
    vision_model = genai.GenerativeModel('gemini-1.5-flash-latest')
    print("Gemini Vision model initialized successfully.")
except Exception as e:
    vision_model = None
    print(f"!!! Gemini API Error: Could not configure the API. Please check your API key. Error: {e}")
    print("!!! Image processing will not be available.")


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
LANGUAGES_TO_INSTALL = ["en", "es", "hi", "bn", "ur", "el"] # Added more languages
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
    "hypertension": {"en": "hypertension", "hi": "उच्च रक्तचाप", "es": "hipertensión", "de": "Hypertonie", "fr": "hypertension"},
    "asthma": {"en": "asthma", "hi": "दमा", "es": "asma", "de": "Asthma", "fr": "asthme"},
    "thyroid": {"en": "thyroid", "hi": "थायराइड", "es": "tiroides", "de": "Schilddrüse", "fr": "thyroïde"},
    "arthritis": {"en": "arthritis", "hi": "गठिया", "es": "artritis", "de": "Arthritis", "fr": "arthrite"},
    "anemia": {"en": "anemia", "hi": "खून की कमी", "es": "anemia", "de": "Anämie", "fr": "anémie"},
    "migraine": {"en": "migraine", "hi": "माइग्रेन", "es": "migraña", "de": "Migräne", "fr": "migraine"},
    "pneumonia": {"en": "pneumonia", "hi": "निमोनिया", "es": "neumonía", "de": "Lungenentzündung", "fr": "pneumonie"},
    "ulcer": {"en": "ulcer", "hi": "अल्सर", "es": "úlcera", "de": "Geschwür", "fr": "ulcère"},
    "kidney stone": {"en": "kidney stone", "hi": "गुर्दे की पथरी", "es": "cálculo renal", "de": "Nierenstein", "fr": "calcul rénal"},
    "hepatitis": {"en": "hepatitis", "hi": "यकृत शोथ", "es": "hepatitis", "de": "Hepatitis", "fr": "hépatite"},
    "bronchitis": {"en": "bronchitis", "hi": "श्वासनलीशोथ", "es": "bronquitis", "de": "Bronchitis", "fr": "bronchite"},
    "gastritis": {"en": "gastritis", "hi": "जठरशोथ", "es": "gastritis", "de": "Gastritis", "fr": "gastrite"},
    "dementia": {"en": "dementia", "hi": "मनोभ्रंश", "es": "demencia", "de": "Demenz", "fr": "démence"},
    "multiple sclerosis": {"en": "multiple sclerosis", "hi": "मल्टीपल स्केलेरोसिस", "es": "esclerosis múltiple", "de": "Multiple Sklerose", "fr": "sclérose en plaques"},
    "epilepsy": {"en": "epilepsy", "hi": "मिर्गी", "es": "epilepsia", "de": "Epilepsie", "fr": "épilepsie"},
    "osteoporosis": {"en": "osteoporosis", "hi": "अस्थिसुषिरता", "es": "osteoporosis", "de": "Osteoporose", "fr": "ostéoporose"},
    "pneumothorax": {"en": "pneumothorax", "hi": "वातुरस", "es": "neumotórax", "de": "Pneumothorax", "fr": "pneumothorax"},
    "appendicitis": {"en": "appendicitis", "hi": "आंत्रपुच्छशोथ", "es": "apendicitis", "de": "Blinddarmentzündung", "fr": "appendicite"},
    "cataract": {"en": "cataract", "hi": "मोतियाबिंद", "es": "catarata", "de": "Katarakt", "fr": "cataracte"},
    "glaucoma": {"en": "glaucoma", "hi": "काला मोतिया", "es": "glaucoma", "de": "Glaukom", "fr": "glaucome"},
    "cirrhosis": {"en": "cirrhosis", "hi": "यकृत का सिरोसिस", "es": "cirrosis", "de": "Zirrhose", "fr": "cirrhose"},
    "biopsy": {"en": "biopsy", "hi": "जीवोप्सी", "es": "biopsia", "de": "Biopsie", "fr": "biopsie"},
    "defibrillator": {"en": "defibrillator", "hi": "डीफिब्रिलेटर", "es": "desfibrilador", "de": "Defibrillator", "fr": "défibrillateur"},
    "sutures": {"en": "sutures", "hi": "टांके", "es": "suturas", "de": "Nähte", "fr": "sutures"},
    "transplant": {"en": "transplant", "hi": "प्रत्यारोपण", "es": "trasplante", "de": "Transplantation", "fr": "greffe"},
    "contusion": {"en": "contusion", "hi": "चोट", "es": "contusión", "de": "Prellung", "fr": "contusion"},
    "edema": {"en": "edema", "hi": "शोफ", "es": "edema", "de": "Ödem", "fr": "œdème"},
    "malignant": {"en": "malignant", "hi": "घातक", "es": "maligno", "de": "bösartig", "fr": "malin"},
    "benign": {"en": "benign", "hi": "सौम्य", "es": "benigno", "de": "gutartig", "fr": "bénin"},
    "chronic": {"en": "chronic", "hi": "पुराना", "es": "crónico", "de": "chronisch", "fr": "chronique"},
    "acute": {"en": "acute", "hi": "तीव्र", "es": "agudo", "de": "akut", "fr": "aigu"},
    "cardiology": {"en": "cardiology", "hi": "हृदय रोग विज्ञान", "es": "cardiología", "de": "Kardiologie", "fr": "cardiologie"},
    "hematology": {"en": "hematology", "hi": "रुधिर विज्ञान", "es": "hematología", "de": "Hämatologie", "fr": "hématologie"},
    "geriatrics": {"en": "geriatrics", "hi": "वृद्धावस्था चिकित्सा", "es": "geriatría", "de": "Geriatrie", "fr": "gériatrie"},
    "neurology": {"en": "neurology", "hi": "तंत्रिका-विज्ञान", "es": "neurología", "de": "Neurologie", "fr": "neurologie"},
    "oncology": {"en": "oncology", "hi": "कैंसर विज्ञान", "es": "oncología", "de": "Onkologie", "fr": "oncologie"},
    "pediatrics": {"en": "pediatrics", "hi": "बाल रोग", "es": "pediatría", "de": "Pädiatrie", "fr": "pédiatrie"},
    "urology": {"en": "urology", "hi": "मूत्रविज्ञान", "es": "urología", "de": "Urologie", "fr": "urologie"},
    "gastroenterology": {"en": "gastroenterology", "hi": "जठरांत्र विज्ञान", "es": "gastroenterología", "de": "Gastroenterologie", "fr": "gastro-entérologie"},
    "dermatology": {"en": "dermatology", "hi": "त्वचा विज्ञान", "es": "dermatología", "de": "Dermatologie", "fr": "dermatologie"},
    "x-ray": {"en": "x-ray", "hi": "एक्स-रे", "es": "radiografía", "de": "Röntgenaufnahme", "fr": "radiographie"},
    "mri": {"en": "mri", "hi": "एमआरआई", "es": "resonancia magnética", "de": "MRT", "fr": "IRM"},
    "ct scan": {"en": "ct scan", "hi": "सीटी स्कैन", "es": "tomografía computarizada", "de": "CT-Scan", "fr": "scanner"},
    "ultrasound": {"en": "ultrasound", "hi": "अल्ट्रासाउंड", "es": "ecografía", "de": "Ultraschall", "fr": "échographie"},
    "blood pressure": {"en": "blood pressure", "hi": "रक्तचाप", "es": "presión arterial", "de": "Blutdruck", "fr": "tension artérielle"},
    "heart rate": {"en": "heart rate", "hi": "हृदय गति", "es": "frecuencia cardíaca", "de": "Herzfrequenz", "fr": "rythme cardiaque"},
    "sepsis": {"en": "sepsis", "hi": "पूति", "es": "sepsis", "de": "Sepsis", "fr": "sepsis"},
    "anaphylaxis": {"en": "anaphylaxis", "hi": "तीव्रगाहिता", "es": "anafilaxia", "de": "Anaphylaxie", "fr": "anaphylaxie"},
    "arrhythmia": {"en": "arrhythmia", "hi": "अतालता", "es": "arritmia", "de": "Arrhythmie", "fr": "arythmie"},
    "emphysema": {"en": "emphysema", "hi": "वातास्फीति", "es": "enfisema", "de": "Emphysem", "fr": "emphysème"},
    "electrocardiogram": {"en": "electrocardiogram", "hi": "इलेक्ट्रोकार्डियोग्राम", "es": "electrocardiograma", "de": "Elektrokardiogramm", "fr": "électrocardiogramme"},
    "endoscopy": {"en": "endoscopy", "hi": "एंडोस्कोपी", "es": "endoscopia", "de": "Endoskopie", "fr": "endoscopie"},
    "colonoscopy": {"en": "colonoscopy", "hi": "कोलोनोस्कोपी", "es": "colonoscopia", "de": "Koloskopie", "fr": "coloscopie"},
    "biopsy": {"en": "biopsy", "hi": "बायोप्सी", "es": "biopsia", "de": "Biopsie", "fr": "biopsie"},
    "chemotherapy": {"en": "chemotherapy", "hi": "कीमोथेरेपी", "es": "quimioterapia", "de": "Chemotherapie", "fr": "chimiothérapie"},
    "radiation therapy": {"en": "radiation therapy", "hi": "विकिरण चिकित्सा", "es": "radioterapia", "de": "Strahlentherapie", "fr": "radiothérapie"},
    "surgery": {"en": "surgery", "hi": "शल्य चिकित्सा", "es": "cirugía", "de": "Chirurgie", "fr": "chirurgie"},
    "anesthesia": {"en": "anesthesia", "hi": "संज्ञाहरण", "es": "anestesia", "de": "Anästhesie", "fr": "anesthésie"},
    "catheter": {"en": "catheter", "hi": "कैथेटर", "es": "catéter", "de": "Katheter", "fr": "cathéter"},
    "stretcher": {"en": "stretcher", "hi": "स्ट्रेचर", "es": "camilla", "de": "Trage", "fr": "brancard"},
    "wheelchair": {"en": "wheelchair", "hi": "व्हीलचेयर", "es": "silla de ruedas", "de": "Rollstuhl", "fr": "fauteuil roulant"},
    "ventilator": {"en": "ventilator", "hi": "वेंटिलेटर", "es": "respirador", "de": "Beatmungsgerät", "fr": "respirateur"},
    "scalpel": {"en": "scalpel", "hi": "स्कैल्पेल", "es": "bisturí", "de": "Skalpell", "fr": "scalpel"},
    "heart": {"en": "heart", "hi": "हृदय", "es": "corazón", "de": "Herz", "fr": "cœur"},
    "lungs": {"en": "lungs", "hi": "फेफड़े", "es": "pulmones", "de": "Lungen", "fr": "poumons"},
    "brain": {"en": "brain", "hi": "मस्तिष्क", "es": "cerebro", "de": "Gehirn", "fr": "cerveau"},
    "liver": {"en": "liver", "hi": "यकृत", "es": "hígado", "de": "Leber", "fr": "foie"},
    "stomach": {"en": "stomach", "hi": "पेट", "es": "estómago", "de": "Magen", "fr": "estomac"},
    "kidneys": {"en": "kidneys", "hi": "गुर्दे", "es": "riñones", "de": "Nieren", "fr": "reins"},
    "intestines": {"en": "intestines", "hi": "आंतें", "es": "intestinos", "de": "Darm", "fr": "intestins"},
    "spine": {"en": "spine", "hi": "रीढ़", "es": "columna vertebral", "de": "Wirbelsäule", "fr": "colonne vertébrale"}
}
symptom_to_department = {
    "fever": ["General Medicine"], "headache": ["Neurology", "General Medicine"], "pain": ["General Medicine", "Orthopedics"], "heart attack": ["Cardiology", "Emergency"], "cancer": ["Oncology"], "diabetes": ["Endocrinology"], "cough": ["Pulmonology", "General Medicine"], "fracture": ["Orthopedics", "Emergency"], "dizziness": ["Neurology", "ENT"], "nausea": ["Gastroenterology"], "vomiting": ["Gastroenterology", "Emergency"], "stroke": ["Neurology", "Emergency"], "allergy": ["Allergy & Immunology"], "infection": ["Infectious Disease", "General Medicine"], "cold": ["General Medicine", "ENT"], "hypertension": ["Cardiology", "General Medicine"], "asthma": ["Pulmonology"], "thyroid": ["Endocrinology"], "arthritis": ["Rheumatology", "Orthopedics"], "anemia": ["Hematology", "General Medicine"], "migraine": ["Neurology"], "pneumonia": ["Pulmonology", "Infectious Disease"], "ulcer": ["Gastroenterology"], "kidney stone": ["Urology", "Nephrology"], "hepatitis": ["Gastroenterology", "Hepatology"], "bronchitis": ["Pulmonology"], "gastritis": ["Gastroenterology"], "dementia": ["Neurology", "Geriatrics"], "multiple sclerosis": ["Neurology"], "epilepsy": ["Neurology"], "osteoporosis": ["Orthopedics", "Endocrinology"], "pneumothorax": ["Pulmonology", "Emergency"], "appendicitis": ["General Surgery", "Emergency"], "cataract": ["Ophthalmology"], "glaucoma": ["Ophthalmology"], "cirrhosis": ["Hepatology", "Gastroenterology"], "sepsis": ["Infectious Disease", "Emergency", "General Medicine"], "anaphylaxis": ["Allergy & Immunology", "Emergency"], "arrhythmia": ["Cardiology"], "emphysema": ["Pulmonology"], "contusion": ["Orthopedics", "General Medicine"], "edema": ["General Medicine", "Cardiology", "Nephrology"]
}
department_translations = {
    "General Medicine": {"en": "General Medicine", "hi": "सामान्य चिकित्सा", "es": "Medicina General", "de": "Allgemeinmedizin"}, "Neurology": {"en": "Neurology", "hi": "तंत्रिका-विज्ञान", "es": "Neurología", "de": "Neurologie"}, "Orthopedics": {"en": "Orthopedics", "hi": "हड्डी रोग", "es": "Ortopedia", "de": "Orthopädie"}, "Emergency": {"en": "Emergency", "hi": "आपातकालीन", "es": "Emerencia", "de": "Notaufnahme"}, "Cardiology": {"en": "Cardiology", "hi": "हृदय रोग विज्ञान", "es": "Cardiología", "de": "Kardiologie"}, "Oncology": {"en": "Oncology", "hi": "कैंसर विज्ञान", "es": "Oncología", "de": "Onkologie"}, "Endocrinology": {"en": "Endocrinology", "hi": "अंतःस्त्राविका", "es": "Endocrinología", "de": "Endokrinologie"}, "Pulmonology": {"en": "Pulmonology", "hi": "फेफड़ा विज्ञान", "es": "Neumología", "de": "Pneumologie"}, "ENT": {"en": "ENT", "hi": "ईएनटी", "es": "Otorrinolaringología", "de": "HNO"}, "Gastroenterology": {"en": "Gastroenterology", "hi": "जठरांत्र विज्ञान", "es": "Gastroenterología", "de": "Gastroenterologie"}, "Allergy & Immunology": {"en": "Allergy & Immunology", "hi": "एलर्जी और इम्यूनोलॉजी", "es": "Alergia e Inmunología", "de": "Allergologie und Immunologie"}, "Infectious Disease": {"en": "Infectious Disease", "hi": "संक्रामक रोग", "es": "Enfermedades Infecciosas", "de": "Infektionskrankheiten"}, "Rheumatology": {"en": "Rheumatology", "hi": "संधिवातीयशास्त्र", "es": "Reumatología", "de": "Rheumatologie"}, "Hematology": {"en": "Hematology", "hi": "रुधिर विज्ञान", "es": "Hematología", "de": "Hämatologie"}, "Urology": {"en": "Urology", "hi": "मूत्रविज्ञान", "es": "Urología", "de": "Urologie"}, "Nephrology": {"en": "Nephrology", "hi": "गुर्दा रोग विज्ञान", "es": "Nefrología", "de": "Nephrologie"}, "Hepatology": {"en": "Hepatology", "hi": "यकृत विज्ञान", "es": "Hepatología", "de": "Hepatologie"}, "Geriatrics": {"en": "Geriatrics", "hi": "वृद्धावस्था चिकित्सा", "es": "Geriatría", "de": "Geriatrie"}, "General Surgery": {"en": "General Surgery", "hi": "सामान्य शल्य चिकित्सा", "es": "Cirugía General", "de": "Allgemeinchirurgie"}, "Ophthalmology": {"en": "Ophthalmology", "hi": "नेत्र विज्ञान", "es": "Oftalmología", "de": "Augenheilkunde"}, "Dermatology": {"en": "Dermatology", "hi": "त्वचा विज्ञान", "es": "Dermatología", "de": "Dermatologie"}
}

def get_text_from_image(image_bytes):
    """
    Calls the Gemini Vision API to get structured text from an image.
    """
    if not vision_model:
        print("Vision model not available. Returning error message.")
        return "Error: Image processing service is not configured. Please check the API key."
    try:
        print("Sending image to Gemini Vision API...")
        image = Image.open(io.BytesIO(image_bytes))
        
        # This prompt guides the model to be more helpful for our specific use case.
        prompt = [
            "You are a specialized OCR service for medical documents. ",
            "Analyze this image and extract all text content. ",
            "Prioritize clarity and structure. ",
            "If it appears to be a medical report, lab result, or prescription, ",
            "please identify and label key information such as Patient Name, Diagnosis, ",
            "Medications, Dosages, and important values. If it is not a medical document, ",
            "extract all text as clearly as possible.",
            image
        ]
        
        response = vision_model.generate_content(prompt)
        print("Received response from Gemini.")
        return response.text
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return f"Error: Could not process image. Details: {e}"

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
        # --- NEW: Added image file handling ---
        if extension.lower() in ['.png', '.jpg', '.jpeg']:
            print(f"Processing image file: {filepath}")
            with open(filepath, 'rb') as f:
                image_bytes = f.read()
            text = get_text_from_image(image_bytes)
        
        elif extension == '.pdf':
            with fitz.open(filepath) as doc:
                for page in doc:
                    text += page.get_text()
                    image_list = page.get_images(full=True)
                    for img_index, img in enumerate(image_list):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        # Call the image-to-text function for images inside PDFs
                        text_from_image = get_text_from_image(image_bytes)
                        text += f"\n--- [Image Content] ---\n{text_from_image}\n--- [End Image Content] ---\n"

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

def post_process_translation(text, lang_code):
    if lang_code in ['bn', 'ur', 'el']:
        print(f"Applying enhanced post-processing for language: {lang_code}")
        text = re.sub(r'([^\w\s])', r' \1 ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
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
        translated_text = post_process_translation(translated_text, target_lang)
        
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
            for english_keyword in keywords_in_english:
                departments_for_keyword = symptom_to_department.get(english_keyword, [])
                translated_keyword = medical_glossary[english_keyword].get(target_lang, english_keyword)
                for dept_english_name in departments_for_keyword:
                    translated_dept = department_translations.get(dept_english_name, {}).get(target_lang, dept_english_name)
                    recommendations.append({"keyword": translated_keyword, "department": translated_dept})

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
        
        # process_file now handles images via Gemini
        processed_text = process_file(filepath)
        
        # If Gemini returned an error, pass it to the frontend
        if processed_text.startswith("Error:"):
            os.remove(filepath)
            return jsonify({'translated_text': processed_text, 'keywords': []})

        # Assume the extracted text is in English for keyword analysis.
        # This could be enhanced with language detection in the future.
        source_lang_of_file = 'en'
        keywords_in_english = find_medical_keywords(processed_text, source_lang_of_file)
        translated_text = argostranslate.translate.translate(processed_text, source_lang_of_file, target_lang)
        translated_text = post_process_translation(translated_text, target_lang)
        
        keywords_data = []
        if keywords_in_english:
            for english_keyword in keywords_in_english:
                query = f'"{english_keyword}" medical diagram anatomy'
                search_url = f"https://www.google.com/search?tbm=isch&q={quote(query)}"
                if target_lang in medical_glossary.get(english_keyword, {}):
                    translated_terms = medical_glossary[english_keyword][target_lang]
                    if not isinstance(translated_terms, list): translated_terms = [translated_terms]
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