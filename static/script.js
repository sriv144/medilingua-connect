document.addEventListener('DOMContentLoaded', () => {
    const sourceLangSelect = document.getElementById('source-lang');
    const targetLangSelect = document.getElementById('target-lang');
    const inputText = document.getElementById('input-text');
    const outputText = document.getElementById('output-text');
    const translateBtn = document.getElementById('translate-btn');

    // Load languages from backend
    function loadLanguages() {
        fetch('/api/languages')
            .then(response => response.json())
            .then(languages => {
                // Clear existing options
                sourceLangSelect.innerHTML = '';
                targetLangSelect.innerHTML = '';

                languages.forEach(lang => {
                    const option1 = document.createElement('option');
                    option1.value = lang.code;
                    option1.textContent = `${lang.name} (${lang.code})`;
                    sourceLangSelect.appendChild(option1);

                    const option2 = document.createElement('option');
                    option2.value = lang.code;
                    option2.textContent = `${lang.name} (${lang.code})`;
                    targetLangSelect.appendChild(option2);
                });

                // Default source = English if exists, target = another language
                if (languages.find(l => l.code === 'en')) {
                    sourceLangSelect.value = 'en';
                }
                if (languages.length > 1) {
                    targetLangSelect.value = languages.find(l => l.code !== sourceLangSelect.value).code;
                }
            })
            .catch(err => {
                outputText.textContent = `Error loading languages: ${err}`;
                outputText.classList.add('error');
            });
    }

    // Handle translation
    translateBtn.addEventListener('click', () => {
        const sourceLang = sourceLangSelect.value;
        const targetLang = targetLangSelect.value;
        const text = inputText.value.trim();

        outputText.classList.remove('error');
        outputText.textContent = '';

        if (!sourceLang || !targetLang) {
            outputText.textContent = 'Please select both source and target languages.';
            outputText.classList.add('error');
            return;
        }
        if (!text) {
            outputText.textContent = 'Please enter text to translate.';
            outputText.classList.add('error');
            return;
        }

        translateBtn.disabled = true;
        outputText.textContent = 'Translating...';

        fetch('/api/translate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                source_lang: sourceLang,
                target_lang: targetLang,
                text: text
            })
        })
        .then(response => response.json())
        .then(data => {
            translateBtn.disabled = false;
            if (data.error) {
                outputText.textContent = `Error: ${data.error}`;
                outputText.classList.add('error');
            } else {
                outputText.textContent = data.translated_text;
            }
        })
        .catch(err => {
            translateBtn.disabled = false;
            outputText.textContent = `Network error: ${err}`;
            outputText.classList.add('error');
        });
    });

    loadLanguages();
});
