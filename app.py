import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from gruut import sentences
from google.cloud import translate_v2 as translate

app = Flask(__name__)
CORS(app)

# 1. AUTHENTICATION
# Ensure your Render Secret File is named 'serviceaccount.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/etc/secrets/serviceaccount.json'
translate_client = translate.Client()

# 2. PHONETIC MAPPINGS
MAPS = {
    'hebrew': {
        'consonants': {
            'p': 'פּ', 'b': 'בּ', 't': 'ט', 'd': 'ד', 'k': 'כּ', 'ɡ': 'ג',
            'f': 'פ', 'v': 'ב', 's': 'ס', 'z': 'ז', 'ʃ': 'שׁ', 'ʒ': 'ז',
            'x': 'ח', 'h': 'ה', 'm': 'מ', 'n': 'נ', 'l': 'ל', 'r': 'ר',
            'j': 'י', 'w': 'ו', 'θ': 'ת', 'ð': 'ד', 't͡ʃ': 'צ׳', 'd͡ʒ': 'ג׳',
            'ŋ': 'נ', 'ɹ': 'ר', 'ɾ': 'ר'
        },
        'vowels': {
            'a': '\u05B8', 'æ': '\u05B7', 'e': '\u05B6', 'i': '\u05B4', 
            'o': '\u05B9', 'u': '\u05BB', 'ə': '\u05B0', 'ɪ': '\u05B4', 
            'ʊ': '\u05BB', 'ʌ': '\u05B8', 'ɛ': '\u05B6', 'ɑ': '\u05B8',
            'ɔ': '\u05B8', 'oʊ': '\u05B9', 'ɚ': '\u05B0ר', 'ɝ': '\u05B0ר'
        },
        'sofit': {'כּ': 'ך', 'כ': 'ך', 'מ': 'ם', 'נ': 'ן', 'פּ': 'ף', 'פ': 'ף', 'צ': 'ץ'},
        'target': 'he'
    },
    'arabic': {
        'consonants': {
            'p': 'ب', 'b': 'ب', 't': 'ت', 'd': 'د', 'k': 'ك', 'ɡ': 'ج',
            'f': 'ف', 'v': 'ف', 's': 'س', 'z': 'ز', 'ʃ': 'ش', 'ʒ': 'ج',
            'x': 'خ', 'h': 'ه', 'm': 'م', 'n': 'ن', 'l': 'ل', 'r': 'ر',
            'j': 'ي', 'w': 'و', 'θ': 'ث', 'ð': 'ذ', 't͡ʃ': 'تش', 'd͡ʒ': 'ج',
            'ŋ': 'ن', 'ɹ': 'ر', 'ɾ': 'ر'
        },
        'vowels': {
            'a': '\u064E', 'æ': '\u064E', 'e': '\u0650', 'i': '\u0650', 
            'o': '\u064F', 'u': '\u064F', 'ə': '\u0652', 'ɪ': '\u0650', 
            'ʊ': '\u064F', 'ʌ': '\u064E', 'ɛ': '\u0650', 'ɑ': '\u064E',
            'ɔ': '\u064E', 'oʊ': '\u064F', 'ɚ': '\u064Eر', 'ɝ': '\u064Eر'
        },
        'sofit': {}, # Arabic handles its own joining logic in translation
        'target': 'ar'
    }
}

def get_phonetic_sig(name, mode):
    cfg = MAPS.get(mode, MAPS['hebrew'])
    try:
        ipa_list = []
        for sentence in sentences(name, lang="en-us"):
            for word in sentence:
                if word.phonemes: ipa_list.extend(word.phonemes)
        
        sig = ""
        last_was_con = False
        for p in ipa_list:
            if p in cfg['consonants']:
                sig += cfg['consonants'][p]
                last_was_con = True
            elif p in cfg['vowels']:
                anchor = 'א' if mode == 'hebrew' and not last_was_con else ''
                sig += anchor + cfg['vowels'][p]
                last_was_con = 'ר' in cfg['vowels'][p]
        
        # Apply Sofit for Hebrew
        if mode == 'hebrew':
            chars = list(sig)
            for j in range(len(chars)-1, -1, -1):
                if chars[j] in cfg['sofit']:
                    chars[j] = cfg['sofit'][chars[j]]
                    break
            sig = "".join(chars)
        return sig
    except: return "???"

@app.route('/oracle', methods=['POST'])
def oracle():
    data = request.json
    text = data.get('name', '')
    mode = data.get('mode', 'hebrew')
    
    words = text.split()
    parts = [get_phonetic_sig(w, mode) for w in words]
    full_sig = " ".join(parts)
    
    # Translate using the selected lens
    target = MAPS[mode]['target']
    result = translate_client.translate(full_sig, target_language='en', source_language=target)
    
    return jsonify({
        "signature": full_sig,
        "interpretation": result['translatedText']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))