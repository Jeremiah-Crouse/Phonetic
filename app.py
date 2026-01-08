from flask import Flask, request, jsonify
from flask_cors import CORS
from gruut import sentences
from google.cloud import translate_v2 as translate
import os

app = Flask(__name__)
CORS(app) # Allows your GitHub Pages site to talk to this server

# Initialize Translate (Render will use your Environment Variable)
translate_client = translate.Client()

def get_phonetic_hebrew(name):
    ipa_list = []
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


@app.route('/oracle', methods=['POST'])
def oracle():
    data = request.json
    user_input = data.get('name', '')
    
    words = user_input.split()
    hebrew_words = []
    
    for word in words:
        hebrew_words.append(get_phonetic_hebrew(word))
    
    full_hebrew = " ".join(hebrew_words)
    
    # Translate
    result = translate_client.translate(full_hebrew, target_language='en', source_language='he')
    
    return jsonify({
        "hebrew": full_hebrew,
        "interpretation": result['translatedText'],
        "power": calculate_gematria(full_hebrew)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))