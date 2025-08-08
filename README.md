### README.md for MediLingua Connect

# 🩺 MediLingua Connect

MediLingua Connect is a real-time multilingual medical translation assistant designed to bridge language gaps in healthcare settings. It facilitates seamless communication between patients and providers by translating spoken or written medical dialogue with a focus on accuracy, low latency, and specialized medical terminology.

-----

### ✨ Features

  * **Real-Time Translation**: Translate text instantly between multiple languages to support natural conversational flow.
  * **Medical Terminology Handling**: Utilizes a built-in medical glossary to accurately translate specific medical terms and patient symptoms.
  * **File Translation**: Translate the content of various file types, including PDF, DOCX, CSV, and TXT.
  * **Speech-to-Text & Text-to-Speech**: Integrates browser APIs for voice input and spoken output, making communication more accessible.
  * **Sign Language Support**: Offers visual aids for medical keywords by linking to sign language videos.
  * **Visual Aids**: Provides image search links for translated medical terms to offer visual context.
  * **SOS Functionality**: Finds and maps nearby hospitals based on the user's location, along with driving directions and estimated travel times using OpenStreetMap and Project OSRM.
  * **Symptom-to-Department Mapping**: Recommends appropriate hospital departments based on the identified medical keywords or symptoms.

-----

### ⚙️ Installation

1.  **Clone the Repository**:

    ```bash
    git clone https://github.com/sriv144/medilingua-connect.git
    cd medilingua-connect
    ```

2.  **Set up Python Environment**:
    The project is preferred to run with **Python 3.11.9**. It is recommended to use a virtual environment.

    ```bash
    # Create and activate a virtual environment
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    First, upgrade pip to avoid potential issues.

    ```bash
    python.exe -m pip install --upgrade pip
    pip install -r requirements.txt
    ```

    The key dependencies include Flask, `argostranslate`, PyMuPDF, python-docx, pandas, and Pillow.

4.  **Install Language Models (Optional but Recommended)**:
    The `app.py` file automatically installs a set of default languages (`en`, `es`, `hi`, `bn`, `ur`, `el`). You can also use the included script to install all available languages.

    ```bash
    python install_all_languages.py
    ```

-----

### ▶️ Usage

1.  **Run the Flask Application**:
    Start the server by running the main application file.

    ```bash
    python app.py
    ```

    The application will be accessible at `http://localhost:5000`.

2.  **Access the User Interface**:
    Open your web browser and navigate to the address above. The single-page application will load, allowing you to:

      * Select source and target languages from the dropdown menus.
      * Type or speak your text for translation.
      * Click the **SOS** button to find nearby hospitals.
      * Upload a file for translation using the paperclip icon.

-----

### 📚 Project Structure

  * `app.py`: The main Flask application that handles all backend logic, including translation, file processing, and API endpoints.
  * `requirements.txt`: Lists the Python libraries required to run the project.
  * `README.md`: This file, providing an overview and instructions for the project.
  * `static/script.js`: The front-end logic written in JavaScript for handling user interactions and API calls.
  * `templates/index.html`: The user interface of the application, built with Tailwind CSS, React, and Leaflet.js for mapping functionalities.
  * `install_all_languages.py`: A utility script to automatically download and install all available language packages for `argostranslate`.
