import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from gruut import sentences
from google.cloud import translate_v2 as translate

app = Flask(__name__)
CORS(app)

# Initialize Translate
# Note: Ensure GOOGLE_APPLICATION_CREDENTIALS is set in your environment
translate_client = translate.Client()

def get_phonetic_hebrew(name):
    try:
        ipa_list = []
        # 'en-us' is the model downloaded in the build command
        for sentence in sentences(name, lang="en-us"):
            for word in sentence:
                if word.phonemes:
                    ipa_list.extend(word.phonemes)
        
        consonants = {
            'p': 'פּ', 'b': 'בּ', 't': 'ט', 'd': 'ד', 'k': 'כּ', 'ɡ': 'ג',
            'f': 'פ', 'v': 'ב', 's': 'ס', 'z': 'ז', 'ʃ': 'שׁ', 'ʒ': 'ז',
            'x': 'ח', 'h': 'ה', 'm': 'מ', 'n': 'נ', 'l': 'ל', 'r': 'ר',
            'j': 'י', 'w': 'ו', 'θ': 'ת', 'ð': 'ד', 't͡ʃ': 'צ׳', 'd͡ʒ': 'ג׳',
            'ŋ': 'נ', 'ɹ': 'ר', 'ɾ': 'ר', 'm': 'מ'
        }

        vowels = {
            'a': '\u05B8', 'æ': '\u05B7', 'e': '\u05B6', 'i': '\u05B4', 
            'o': '\u05B9', 'u': '\u05BB', 'ə': '\u05B0', 'ɪ': '\u05B4', 
            'ʊ': '\u05BB', 'ʌ': '\u05B8', 'ɛ': '\u05B6', 'ɑ': '\u05B8',
            'ɔ': '\u05B8', 'oʊ': '\u05B9', 'ɚ': '\u05B0ר', 'ɝ': '\u05B0ר'
        }

        hebrew_signature = ""
        last_was_consonant = False

        for i, p in enumerate(ipa_list):
            if p in consonants:
                hebrew_signature += consonants[p]
                last_was_consonant = True
            elif p in vowels:
                if not last_was_consonant:
                    hebrew_signature += 'א' + vowels[p]
                else:
                    hebrew_signature += vowels[p]
                last_was_consonant = 'ר' in vowels[p]
            elif len(p) > 1:
                for sub_p in p:
                    if sub_p in consonants:
                        hebrew_signature += consonants[sub_p]
                        last_was_consonant = True
                    elif sub_p in vowels:
                        if not last_was_consonant:
                            hebrew_signature += 'א' + vowels[sub_p]
                        else:
                            hebrew_signature += vowels[sub_p]
                        last_was_consonant = 'ר' in vowels[sub_p]

        sofit_map = {'כּ': 'ך', 'כ': 'ך', 'מ': 'ם', 'נ': 'ן', 'פּ': 'ף', 'פ': 'ף', 'צ': 'ץ'}
        chars = list(hebrew_signature)
        for j in range(len(chars)-1, -1, -1):
            if chars[j] in sofit_map:
                chars[j] = sofit_map[chars[j]]
                break
        return "".join(chars)
    except:
        return "ERROR"

def calculate_gematria(text):
    values = {'א': 1, 'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5, 'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9, 'י': 10, 'כ': 20, 'ל': 30, 'מ': 40, 'נ': 50, 'ס': 60, 'ע': 70, 'פ': 80, 'צ': 90, 'ק': 100, 'ר': 200, 'ש': 300, 'ת': 400, 'ך': 20, 'ם': 40, 'ן': 50, 'ף': 80, 'ץ': 90}
    return sum(values.get(c, 0) for c in text)

@app.route('/oracle', methods=['POST'])
def oracle():
    user_input = request.json.get('name', '')
    words = user_input.split()
    
    hebrew_parts = [get_phonetic_hebrew(w) for w in words]
    full_hebrew = " ".join(hebrew_parts)
    
    # Get Interpretation
    translation = translate_client.translate(full_hebrew, target_language='en', source_language='he')
    
    return jsonify({
        "hebrew": full_hebrew,
        "power": calculate_gematria(full_hebrew),
        "interpretation": translation['translatedText']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)